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

class DThread(object):
  def __init__(self, backend, backend_id, process):
    self._backend = backend
    self._frontend_id = None
    self._backend_id = backend_id
    self._process = process

    self._status = STATUS_RUNNING

    self._active_frame = None # frame zero of call stack; this is an optimization to avoid fetching full call stack all the time
    self._call_stack = None
    self._active_frame_number = 0
    self._changed = Event() # something changed wrt this thread

  frontend_id = property(lambda self: self._frontend_id)
  backend_id = property(lambda self: self._backend_id)
  process = property(lambda self: self._process)

  # called by the frontend when it takes control of the thread....
  def _set_frontend_info(self, frontend_id):
    self._frontend_id = frontend_id

  # Status
  def _set_status(self, status):
    """does not fire a changed event"""
    log2("Set thread %s status to running", self)
    self._status = status
    self._reset_state()
  def _fire_changed(self):
    self._changed.fire()
  status = property(lambda self: self._status)

  """Catch all event for somethign changing on this thread --- frame, etc"""
  changed = property(lambda self: self._changed)

  # Flow control
  def begin_resume(self):
    if self._process._debugger == None:
      raise DebuggerException("Can't control thread directly until it is bound to a Debugger.")
    return self._process._debugger._on_begin_resume(self)

  def begin_step_over(self):
    if self._process._debugger == None:
      raise DebuggerException("Can't control thread directly until it is bound to a Debugger.")
    return self._process._debugger._on_begin_step_over(self)

  def begin_step_into(self):
    if self._process._debugger == None:
      raise DebuggerException("Can't control thread directly until it is bound to a Debugger.")
    return self._process._debugger._on_begin_step_into(self)

  def begin_step_out(self):
    if self._process._debugger == None:
      raise DebuggerException("Can't control thread directly until it is bound to a Debugger.")
    return self._process._debugger._on_begin_step_out(self)

  # call stack
  def _reset_state(self):
    self._active_frame_number = 0
    self._call_stack = None
    self._active_frame = None

  @property
  def call_stack(self):
    if self._call_stack == None:
      self._active_frame = None # make active_frame use call stack now
      self._call_stack = self._backend.get_call_stack(self)
    return self._call_stack

  @property
  def active_frame(self):
    if self._call_stack:
      return self.call_stack[0]

    if self._active_frame == None:
      self._active_frame = self._backend.get_frame(self,self._active_frame_number)
    return self._active_frame

  # active frame
  def set_active_frame_number(self, f):
    if type(f) != int:
      raise DebuggerException("Not an int")
    self._active_frame_number = f
    self._active_frame = None
    self._changed.fire()
  active_frame_number = property(lambda self: self._active_frame_number, set_active_frame_number)

  # str
  def __str__(self):
    if self.frontend_id:
      return "Thread fe_id=%s be_id=%s: %s" % (self.frontend_id, self.backend_id, self.status)
    else:
      return "Thread unbound be_id=%s: %s" % (self.backend_id, self.status)
