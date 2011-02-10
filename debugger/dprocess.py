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
import os

class DProcess(object):
  def __init__(self, backend, backend_id):
    self._debugger = None # will be none until _set_frontend_info called by debuger._on_backend_process_added
    self._frontend_id = None # will be none until _set_frontend_info called by debuger._on_backend_process_added
    self._backend = backend
    self._backend_id = backend_id
    self._threads = BindingList()
    self._last_active_thread = None
    self._target_executable_changed = Event()
    self._was_launched = False

    self._backend_info = None
    self._pty = None

    # retrieve process backend_info when we next stop, processees get created in run mode


  frontend_id = property(lambda self: self._frontend_id)
  backend_id = property(lambda self: self._backend_id)
  threads = property(lambda self: self._threads)
  pty = property(lambda self: self._pty)

  """Backend_Info contains backend-specific information about the process"""
  backend_info = property(lambda self: self._backend_info)

  @property
  def target_executable_changed(self):
    """Fired when the target executable changes without the pid
    changing, e.g. via execv.  Listener should be of the form:
      cb(dprocess)
    """
    return self._target_executable_changed


  def set_last_active_thread(self,thr):
    self._last_active_thread = thr
  last_active_thread = property(lambda self: self._last_active_thread, set_last_active_thread)

  @property
  def was_launched(self):
    """If true, the process was launched by ndbg. If false, it was attached to."""
    return self._was_launched

  # called by the backend
  def _set_backend_info(self, backend_info, was_launched):
    old_info = self._backend_info
    self._was_launched = was_launched
    self._backend_info = backend_info
    if old_info and old_info.target_exe != backend_info.target_exe:
      self._target_executable_changed.fire(self)
    self._update_pty_name()
  def _on_exiting(self):
    self._backend_info = None
    self._backend_id = None

  def _on_exited(self):
    assert(len(self._threads) == 0)


  def _update_pty_name(self):
    if self._pty != None:
      self._pty.name = str(self)

  def _set_pty(self, pty):
    self._pty = pty
    self._update_pty_name()

  # called by the frontend
  def _set_frontend_info(self, debugger, frontend_id):
    self._debugger = debugger
    self._frontend_id = frontend_id

  # public crap
  @property
  def target_cwd(self):
    assert self._backend_info
    return self._backend_info.target_cwd

  @property
  def target_exe(self):
    assert self._backend_info
    return self._backend_info.target_exe

  @property
  def target_full_cmdline(self):
    assert self._backend_info
    if self._backend_info.full_cmdline:
      return self._backend_info.full_cmdline
    else:
      try:
        return ProcessUtils.get_pid_full_cmdline_as_array(self._backend_info.pid)
      except:
        return ["<process dead>"]

  @property
  def compilation_directory(self):
    return self._backend_info.compilation_directory

  @property
  def status(self):
    all_break = True
    for t in self.threads:
      all_break &= t.status == STATUS_BREAK
    if all_break:
      return STATUS_BREAK
    else:
      return STATUS_RUNNING

  # activation helper
  def make_active(self):
    if self._debugger == None:
      raise DebuggerxException("Cannot make active without controlling debugger.")
    if self.last_active_thread:
      t = self.last_active_thread
    elif len(self.threads):
      t = self.threads[-1]
    else:
      t = None
    if t:
      self._debugger.active_thread = t

  # control type stuffs..
  def kill(self):
    assert self._debugger.status == STATUS_BREAK
    self._backend.kill_process(self)

  def detach(self):
    log2("Detach process")
    assert self._debugger.status == STATUS_BREAK
    self._backend.detach_process(self)

  def __str__(self):
    if self._frontend_id and self._backend_info:
      return "Process #%i  %s:%i" % (self._frontend_id, os.path.basename(self.target_exe), self.backend_info.pid)
    elif self._backend_info:
      return "Process %s:%i" % (os.path.basename(self.target_exe), self.backend_info.pid)
    else:
      return "Process be_id=%s" % self.backend_id

