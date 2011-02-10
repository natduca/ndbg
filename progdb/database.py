# Copyright 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from util import *
from collections import deque
import re
import os
import threading
from .tagged_file import *

class Database(object):
  def __init__(self):
    self._search_paths = set() # TODO(nduca) --- persist this?
    self._num_files = 0
    self._all_files_by_basename = {}
    self._all_files_by_filename = {}
    self._ignores = set()
    self._ignores_regexes = set()

    self._num_lookups = 0
    self._total_lookup_duration = 0

    self._worker_threads = []
    self._pending_work_queue = deque()
    self.reset()

  # worker thread system -- shoudl probably get pulled out
  ###########################################################################
  def _begin_reset(self):
    self._pending_work_queue.clear() # get rid of any work pending so the thread stops quicker
    for wt in self._worker_threads:
      wt.stop()
    del self._worker_threads[:]

    self._pending_work_queue.clear() # get rid of any work pending so the thread stops quicker
    self._num_files = 0
    self._all_files_by_basename.clear()
    self._all_files_by_filename.clear()

  def _walker_thread_step(self):
    while True:
      try:
        cmd, args = self._pending_work_queue.popleft()
        cmd(*args)
        return True
      except IndexError:
        return False

  def _finish_reset(self):
    for p in self._search_paths:
      self._pending_work_queue.append((self._explore_path, self._search_paths))

    log2("Restarting worker thread(s)")
    for i in range(1):
      wt = WellBehavedThread("ProgDB Worker", self._walker_thread_step)
      wt.start()
      self._worker_threads.append(wt)

  def reset(self):
    """Resets the memory of the database. Temporary fix until database watches directories for changes."""
    self._begin_reset()
    self._finish_reset()

  def _add_work_front(self, cb,*args): # to front of queue
    self._pending_work_queue.appendleft((cb,args))

  def _add_work(self, cb,*args): # to back of queue
    self._pending_work_queue.append((cb,args))

  def shutdown(self):
    log2("Shutting down Database")
    self._begin_reset()
    log2("Shutdown done")

  # actual database logic
  ###########################################################################

  def add_ignore(self, ign):
    if type(ign) != str:
      raise Exception("ign should be a str")
    log1("Database: Adding ignore %s", ign)
    if len(self._search_paths) == 0:
      # no need to reset if we aren't doign anything yet
      self._ignores.add(ign)
      self._ignores_regexes.add(re.compile(ign))
      return
    else:
      self._begin_reset()
      self._ignores.add(ign)
      self._ignores_regexes.add(re.compile(ign))
      self._finish_reset()

  def add_search_path(self, search_path):
    log1("Database: add_search_path(%s)", search_path)
    path = os.path.realpath(search_path)
    if path in self._search_paths:
      log2("Database: %s is already in search path", path)
      return

    def is_subpath(base, subpath):
      return subpath.startswith(base)

    # if path is a subdir of an existing search path, ignore
    for existing_path in self._search_paths:
      if is_subpath(path, existing_path):
        log2("Database: %s is a subpath of %s, already in the DB's search path", path, existing_path)
        return

    # remove any existing paths that are subpaths of this path; reset if we do
    search_paths_need_changing = False
    new_search_paths = set()
    for existing_path in self._search_paths:
      if is_subpath(existing_path, path):
        log2("Existing path %s is a subpath of new path %s", existing_path, path)
        search_paths_need_changing = True
      else:
        new_search_paths.add(existing_path) # save this path in case we have to clobber search paths

    if search_paths_need_changing:
      log1("Existing search paths changed. Clobbering entire database and resetting...")
      self._begin_reset()
      self._search_paths = new_search_paths
      self._finish_reset()
    else:
      self._search_paths.add(path)
      if os.path.isdir(path):
        self._add_work(self._explore_path, path)
      else:
        log1("Database: Not searching %s, is not dir", path)

  def find_files_matching(self,regex_str):
    log2("Database: Finding files matching %s", regex_str)
    start_time = time.time()
    regex = re.compile(regex_str,flags=re.IGNORECASE)
    res = []
    MAX_RESULTS = 100
    for basename in self._all_files_by_basename:
      if regex.search(basename):
        for tf in self._all_files_by_basename[basename]:
          res.append(tf.filename)
          if len(res) >= 100:
            res.append("<TRUNCATED>")
            break
        if len(res) >= 100:
          break
    duration = time.time() - start_time
    self._total_lookup_duration += duration
    self._num_lookups += 1
    return res

  def find_tags_in_file(self, filename):
    if self._all_files_by_filename.has_key(filename):
      tf = self._all_files_by_filename[filename]

      if tf.get_tags() == None:
        log1("File %s exists, but tags need to be built", filename)
        tf.update()
      tags = tf.get_tags()
      log1("File %s exists. Returning %i tags", filename, len(tags))
      return tags
    else:
      log1("File not found: %s", filename)
      return None

  def get_line_number_for_tag(self, filename, tag_id):
    if self._all_files_by_filename.has_key(filename):
      tf = self._all_files_by_filename[filename]
      tags = tf.get_tags()
      tag = tf.get_tag(tag_id)
      if tag.needs_determining:
        log1("determining line number for %s %s", filename, tag.name)
        tag.determine_line_number(tf.filename)

      if tag.line_number:
        return tag.line_number
      elif tag.line_missing:
        return -1
    else:
      return None

  def get_stats(self):
    if self._num_lookups:
      avg = self._total_lookup_duration / float(self._num_lookups)
    else:
      avg = 0

    return "files: %i, averge lookup: %0.3f ms" % (self._num_files, avg * 1000)

  def get_num_files(self):
    """Gets current number of known files. May change over time since the walker thread is constantly discovering new files."""
    return self._num_files

  def get_status(self):
    if len(self._pending_directories) != 0:
      return "Searching..."
    else:
      return "Idle."

  def _explore_path(self, dir):
    try:
      ents = os.listdir(dir)
      log4("Exploring directory: %s", dir)
    except:
      log1("Error listing directory %s", dir)
      import traceback
      traceback.print_exc()
      ents = []

    # filter ents
    orig_ents = ents
    ents = []
    for ent in orig_ents:
      ignore = False
      for ign in self._ignores_regexes:
        if ign.match(ent):
          ignore = True
          break
      if ignore:
        log4("Ignoring %s", os.path.join(dir,ent))
        continue
      ents.append(ent)

    # make ents absolute
    ents = [os.path.join(dir,ent) for ent in ents]

    newly_found_files = []
    for ent in ents:
      if os.path.isdir(ent):
        self._add_work_front(self._explore_path, ent)
      else:
        newly_found_files.append(ent)
    if len(newly_found_files):
      MessageLoop.add_message(self._save_newly_found_files, newly_found_files)

  def _save_newly_found_files(self, files): # runs on MessageLoop
    log4("Saving %i new files", len(files))
    for filename in files:
      # make sure we haven't discovered a file twice...
      assert self._all_files_by_filename.has_key(filename) == False

      # store file in all_files_by_filename
      tf = TaggedFile(filename)
      self._all_files_by_filename[filename] = tf

      # store file in all_files_by_basename
      basename = os.path.basename(filename)
      if not self._all_files_by_basename.has_key(basename):
        self._all_files_by_basename[basename] = []

      self._all_files_by_basename[basename].append(tf)

      # stats
      self._num_files += 1

