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
from util.logging import *
from util.exponential_backoff import *
import threading
import traceback

class WellBehavedThread():
  def __init__(self, name, cb):
    """
    cb should return True if work was performed, False if no work was found.
    """
    if not cb:
      raise Exception("Cb must be non null")
    self._name = name
    self._cb = cb
    self._thread = None
    self._run = False

  def __del__(self):
    if self._thread:
      self.stop()

  @property
  def name(self):
    return self._name

  @property
  def should_run(self):
    """Returns whether the thread should be running. Will go to false
    before the actual thread stops."""
    return self._run

  def is_runinng(self):
    """Returns whether the thread is running."""
    return self._thread != None

  def start(self):
    if self._thread:
      raise Exception("Already running")
    self._run = True
    self._thread = threading.Thread(target=self._thread_main)
    self._thread.setName(self._name)
    self._thread.start()
    log2("%s thread running", self._name)

  def _thread_main(self):
    exp = ExponentialBackoff()
    while self._run:
      try:
        ret = self._cb()
        if ret:
          exp.reset()
        else:
          exp.sleep()
      except:
        print "On %s thread:" % self._name
        traceback.print_exc()


  def stop(self):
    log2("%s thread stopping", self._name)
    self._run = False
    self._thread.join()
    log2("%s thread stopped", self._name)
    self._thread = None
