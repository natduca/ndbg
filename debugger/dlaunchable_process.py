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
from util import DynObject
from util import ProcessUtils
from util import Event
import os

class DLaunchableProcess(object): 
  def __init__(self, cmdline, launch_cb, ignore_launch_cb, detach_cb):
    self._debugger = None
    self._backend_info = DynObject()
    self._backend_info.pid = None
    self._backend_info.cmdline = cmdline
    self._launch = launch_cb
    self._ignore_launch = ignore_launch_cb
    self._detach = detach_cb

  @property
  def pid(self):
    return None

  def launch(self):
    self._debugger.launchable_processes.remove(self)
    return self._launch()

  def ignore_launch(self):
    self._debugger.launchable_processes.remove(self)
    return self._ignore_launch()

  def detach(self):
    self._debugger.launchable_processes.remove(self)
    return self._detach()

  def _set_frontend_info(self, debugger):
    self._debugger = debugger

  @property
  def backend_info(self):
    return self._backend_info

  def kill(self):
    raise Exception("Not implemented")

  @property
  def target_exe(self):
    return self._backend_info.cmdline[0]

  @property
  def target_full_cmdline(self):
    return self._backend_info.cmdline

  @property
  def threads(self):
    return []

  @property
  def frontend_id(self):
    return None
