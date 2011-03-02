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
from util.event import *

class Timer(object):
  def __init__(self,interval,cb=None,enabled=True):
    self._enabled = False
    self._interval = interval
    self._timeout_bound = False
    self._tick = Event()
    if cb:
      self._tick.add_listener(cb)
    self.enabled = enabled

  @property
  def tick(self):
    return self._tick

  def _fire(self):
    if self._enabled:
      self._tick.fire()
      return True
    else:
      self._timeout_bound = False
      return False

  def set_enabled(self,val):
    if self.enabled == val:
      return
    self._enabled = val
    if self._enabled == True:
      if self._timeout_bound == False:
        MessageLoop.add_delayed_message(self._fire, self._interval)
        self._timeout_bound = True
      else:
        pass

  @property
  def enabled(self):
    return self._enabled

  @enabled.setter
  def enabled(self, en):
    self.set_enabled(en)


