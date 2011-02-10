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
import os.path
import exceptions
from util import *
from . import *
import progdb
import traceback

class FileHandle(object):
  def __init__(self):
    self._absolute_name = None
    self._aliases = []

  def make_location(self, line_num):
    if self._absolute_name == None:
      raise Exception("Cannot make a location for current file handle.")
    return Location(text = "%s:%i" % (self._aliases[0], line_num))

  @property
  def exists(self):
    return self._absolute_name != None

  @property
  def absolute_name(self):
    if self._absolute_name == None:
      raise Exception("Not resolveed.")
    return self._absolute_name

  @property
  def basename(self):
    if self._absolute_name == None:
      raise Exception("Not resolveed.")
    return os.path.basename(self._absolute_name)

  @property
  def aliases(self):
    return self._aliases

  def __hash__(self):
    if self._absolute_name == None:
      raise Exception("Cannot hash unresolved file.")
    return self._absolute_name.__hash__()

  def __eq__(self,that):
    if self._absolute_name == None:
      raise Exception("Cannot hash unresolved file.")
    if that._absolute_name == None:
      raise Exception("Cannot hash unresolved file.")
    return self._absolute_name == that._absolute_name

  def __str__(self):
    if self._absolute_name:
      return "%s aka %s" % (self._absolute_name, ", ".join(self._aliases))
    else:
      assert(len(self._aliases) == 1)
      return "Unresolved %s" % (self._aliases[0])

  def __repr__(self):
    return self.__str__()

class FileManager(object):
  def __init__(self,settings,debugger):
    self._settings = settings
    self._settings.register("FileManager_ProgDB_Ignores", list,
                            ["^\.", # hidden folders
                             "^.+\.o$", # object files
                             "^#.+#$", # emacs crud
                             "^.+~$", # emacs crud
                             ]
                            )

    self._debugger = debugger
    self._debugger.processes.item_added.add_listener(self._on_processes_added)

    self._file_search_path = set()
    self._files_by_absolute_name = {} # todo, keep these by weak reference?
    self._files_by_alias = {} # todo, keep these by weak reference?

    self._progdb = RemoteClass(progdb.Database)
    for ign in self._settings.FileManager_ProgDB_Ignores:
      try:
        re.compile(ign)
        self._progdb.call_async.add_ignore( ign )
      except:
        log0("While compiling FileManager_ProgDB_Ignore %s:", ign)
        traceback.print_exc()

  @property
  def progdb(self):
    return self._progdb

  def shutdown(self):
    self._progdb.shutdown()


  def _on_processes_added(self,proc):
    dirs = []
    if proc.compilation_directory and os.path.exists(proc.compilation_directory):
      dirs.append(proc.compilation_directory)
#    elif os.path.exists(proc.target_exe):
#      dirs.append(os.path.dirname(proc.target_exe))

    dirs.append(proc.target_cwd)

    for d in dirs:
      self._progdb.call_async.add_search_path(d)
    for d in dirs:
      self._file_search_path.add(d)

  @property
  def search_paths(self):
    return list(self._file_search_path)

  def add_search_path(self,path):
    path = os.path.realpath(path)
    self._file_search_path.add(path)
    self._progdb.call_async.add_search_path(path)
    # todo, do we get rid of existing file handles?

  def find_file(self,requested_filename):
    # check files by absolute
    if self._files_by_absolute_name.has_key(requested_filename):
      return self._files_by_absolute_name[requested_filename]

    # check aliases
    if self._files_by_alias.has_key(requested_filename):
      return self._files_by_alias[requested_filename]

    # ok we need to find the file
    for b in self._file_search_path:
      candiate_resolved = os.path.join(b, requested_filename)
      try:
        f = open(candiate_resolved,"r")
        log1("FileManager: %s->%s", requested_filename, candiate_resolved)
        f.close()
        # make it absolute...
        candiate_resolved = os.path.realpath(candiate_resolved)

        if self._files_by_absolute_name.has_key(candiate_resolved):
          # return current handle with new alias
          result = self._files_by_absolute_name[candiate_resolved]
          result._aliases.append(requested_filename)
          assert self._files_by_alias.has_key(requested_filename) == False
          self._files_by_alias[requested_filename] = result
        else:
          # return new handle
          result = FileHandle()
          result._absolute_name = os.path.realpath(candiate_resolved)
          result._aliases.append(requested_filename)
          self._files_by_absolute_name[result.absolute_name] = result
          assert not self._files_by_alias.has_key(requested_filename)
          self._files_by_alias[requested_filename] = result

        return result
      except exceptions.IOError:
        log2("FileManager: tried %s", candiate_resolved)
        pass
    log2("FileManager: %s **NO MATCH**", requested_filename)
    result = FileHandle()
    result._aliases.append(requested_filename)
    self._files_by_alias[requested_filename] = result
    return result
