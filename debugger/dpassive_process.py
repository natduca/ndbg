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

from util import DynObject
from util import ProcessUtils
from util import Event
from util import AlreadyFiredEvent
from util import Timer

import subprocess

import os

class DPassiveProcess(object): 
  def __init__(self, p, attach_cb=None, was_launched=False):
    self._debugger = None
    self._backend_info = DynObject()
    if isinstance(p, subprocess.Popen):
      self._backend_info.pid = p.pid
      self._backend_info.subprocess = p
    else:
      self._backend_info.subprocess = None
      self._backend_info.pid = p
    self._gone = False
    self._timer = Timer(150)
    self._timer.tick.add_listener(self._check_alive)
    self._attach = attach_cb
    self._was_launched = was_launched

  @property
  def pid(self):
    return self._backend_info.pid

  @property
  def backend_info(self):
    return self._backend_info

  def attach(self):
    log1("Begin attach to pid %i %s", self.pid, type(self.pid))
    debugger = self._debugger# save because attach_cb may detach the process
    if self._attach:
      self._attach()
    debugger.passive_processes.remove(self)
    log1("Begin attach to pid %i, phase 2", self.pid)
    debugger.begin_attach_to_pid(self.pid, self._was_launched)

  @property
  def gone(self):
    return self._gone

  def kill(self):
    if self._gone:
      return

    ProcessUtils.kill_proc(self.pid)
    if self._debugger:
      self._debugger.passive_processes.remove(self)
    self._gone = True
    if self._debugger:
      self._debugger.passive_processes.remove(self)
    self._timer.enabled = False

  @property
  def was_launched(self):
    return self._was_launched

  def detach(self):
    self._gone = True
    if self._debugger:
      self._debugger.passive_processes.remove(self)
    self._timer.enabled = True

  def _set_frontend_info(self, debugger):
    self._debugger = debugger

  def _check_alive(self):
    if self._gone:
      self._timer.enabled = False
      return

    if self._backend_info.subprocess:
      alive = self._backend_info.subprocess.poll() == None
    else:
      alive = ProcessUtils.is_proc_alive(self.pid)

    if not alive:
      self._gone = True
      self._timer.enabled = False
      if self._debugger:
        self._debugger.passive_processes.remove(self)


  @property
  def target_exe(self):
    try:
      return ProcessUtils.get_pid_name(self.pid)
    except Exception, ex:
      log1("Error getting target exe for %s: %s", self.pid, ex)
      return ""

  @property
  def target_full_cmdline(self):
    try:
      return ProcessUtils.get_pid_full_cmdline_as_array(self.pid)
    except:
      return None

  @property
  def threads(self):
    return []

  @property
  def frontend_id(self):
    return None
