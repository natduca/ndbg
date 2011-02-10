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
from debugger import *

class BreakpointPersistenceManager(object):
  def __init__(self, mc):
    self._mc = mc
    debugger = self._mc.debugger

    mc.settings.register("CurrentBreakpoints", list, [])

    self._restore_breakpoints_from_settings()
    debugger.breakpoints.changed.add_listener(self._on_breakpoints_changed)

  def _restore_breakpoints_from_settings(self):
    for loc_str in self._mc.settings.CurrentBreakpoints:
      bp = Breakpoint(eval(loc_str, {"Location" : Location}, {}))
      self._mc.debugger.breakpoints.append(bp)

  def _on_breakpoints_changed(self):
    locs = [repr(bp.location) for bp in self._mc.debugger.breakpoints if bp.location.has_repr]
    self._mc.settings.CurrentBreakpoints = locs


