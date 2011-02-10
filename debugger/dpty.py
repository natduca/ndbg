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
from . import *
from util import *

class DPty(object):
  def __init__(self,master_fd,slave_fd):
    self._name = None
    self._name_changed = Event()
    
    self._master_fd = master_fd
    self._slave_fd = slave_fd
    
  def set_name(self,name):
    self._name = name
    self._name_changed.fire(self)
  name = property(lambda self: self._name, set_name)
  name_changed = property(lambda self: self._name_changed)

  @property
  def slave_fd(self):
    return self._slave_fd

  @property
  def master_fd(self):
    return self._master_fd
