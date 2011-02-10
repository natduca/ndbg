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

_breakpoint_id_counter = 1

class Breakpoint(object):
  def __init__(self,location):
    global _breakpoint_id_counter
    self._id = _breakpoint_id_counter
    _breakpoint_id_counter += 1

    # set up reasonable values
    self._on_hit = Event()
    self._debugger = None
    self._location = location # might be null
    self._enabled = True # whether the breakpoint is enabled
    self._backend_breakpoints = {} # the backends on which this breakpoint is currently established
    self._actual_location_list = None # the location where the debugger actually placed the bkpt
    self._error = ""

    self._update()

  @property
  def id(self):
    """ID of the breakpoint."""
    return self._id

  @property
  def location(self):
    """Sets the location of the breakpoint. Note, this is the requested location, not the actual location."""
    return self._location
  @location.setter
  def location(self,location):
    """Sets the location of the breakpoint."""
    self._location = location
    self._enabled = True # turn the breakpoint "on" if it was off....
    if self._debugger:
      self._debugger._on_breakpoint_needs_update(self)


  @property
  def enabled(self):
    """Enabled state of the breakpoint"""
    return self._enabled
  @enabled.setter
  def enabled(self,en):
    self._enabled = en
    if self.valid and self._enabled:
      for backend in self._backend_breakpoints:
        bp = self._backend_breakpoints[backend]
        backend.enable_breakpoint(self,bp.id)
    elif self.valid and not self._enabled:
      for backend in self._backend_breakpoints:
        bp = self._backend_breakpoints[backend]
        backend.disable_breakpoint(self,bp.id)

  @property
  def all_valid(self):
    """Whether the breakpoint is valid. If invalid, check error for why."""
    valid = True
    for backend in self._backend_breakpoints:
      bp = self._backend_breakpoints[backend]
      valid &= bp.valid
    return valid

  @property
  def some_valid(self):
    """Whether the breakpoint is valid. If invalid, check error for why."""
    some_valid = False
    for backend in self._backend_breakpoints:
      bp = self._backend_breakpoints[backend]
      some_valid |= bp.valid
    return some_valid

  @property
  def error(self):
    """Get any errors creating the breakpoint"""
    errors = set()
    for backend in self._backend_breakpoints:
      bp = self._backend_breakpoints[backend]
      if bp.valid==False:
        errors.add(bp.error)
    return "\n".join(list(errors))

  """Actual location list"""
  @property
  def actual_location_list(self):
    locs = set()
    for backend in self._backend_breakpoints:
      bp = self._backend_breakpoints[backend]
      if bp.valid == False:
        continue
      for l in bp.location_list:
        locs.add(l)
    return list(locs)

  @property
  def on_hit(self):
    """Hit util.Event fired when the debugger stops on this breakpoint."""
    return self._on_hit

  # Innards
  def _get_debugger(self):
    return self._debugger
  def _set_debugger(self,val):
    if self._debugger and val:
      raise Exception("Can't set debugger. Already bound to one! You probably added this breakpoint already.")
    self._delete_cur_breakpoint_if_needed()
    self._debugger = val
    self._update()

  def _delete_cur_breakpoint_if_needed(self):
    for backend in self._backend_breakpoints:
      bp = self._backend_breakpoints[backend]
      if bp.valid:
        backend.delete_breakpoint(bp.id)
      self._valid = False
    self._backend_breakpoints.clear()

  def _update(self):
    # early out if we're not attached
    if not self._debugger:
      return

    # delete old breakpoint
    self._delete_cur_breakpoint_if_needed()

    # issue break command
    location = self._location
    for backend in self._debugger._backends:
      try:
        resp = backend.new_breakpoint(location, lambda: self._debugger._on_backend_breakpoint_hit(backend,self))
        bp = DynObject()
        bp.id = resp.id
        bp.valid = True
        bp.location_list = resp.location_list
        if self._enabled == False: # they get created 'enabled'
          backend.disable_breakpoint(self,bp.id)
        self._backend_breakpoints[backend] = bp

      except DebuggerException,e:
        log1("Error creating breakpoint %s on %s: %s", location, backend, e.message)
        bp = DynObject()
        bp.valid = False
        bp.error = e.message
        self._backend_breakpoints[backend] = bp

    # let debugger know of change
    if self._debugger:
      self._debugger._on_breakpoint_changed(self)
