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
import gtk
import debugger
from util import *
from quick_open_dialog import *
from goto_method_dialog import *

import os
class NoCurrentLocationException(Exception):
  pass


class LineMarkState(object):
  def __init__(self):
    self.current_line = False # where the program counter is
    self.on_callstack = False # line is on the callstack, but not current
    self.active_frame = False # line is not the current_line, but is the active frame
    self.breakpoint = False   # line has a breakpoint set
    self.breakpoint_state = ""   # state of breakpoint (all,some,none,disabled)

  def get_mark_resource(self, r):
    if self.current_line:
      if self.breakpoint:
        if self.breakpoint_state == 'disabled':
          m = r.mark_current_line_and_break
        else:
          m = r.mark_current_line_and_break_disabled
      else:
        m = r.mark_current_line
    elif self.on_callstack:
      if self.breakpoint:
        if self.breakpoint_state == 'disabled':
          m = r.mark_on_callstack_and_break_disabled
        else:
          m = r.mark_on_callstack_and_break
      else:
        m = r.mark_on_callstack
    elif self.breakpoint:
      if self.breakpoint_state == 'all':
        m = r.mark_all_break
      elif self.breakpoint_state == 'some':
        m = r.mark_some_break
      elif self.breakpoint_state == 'none':
        m = r.mark_error_break
      elif self.breakpoint_state == 'disabled':
        m = r.mark_disabled_break
      else:
        raise Exception("Unrecognized breakpoint state")
    else:
      m = None
    return m

  def __str__(self):
    return "current_line=%s on_callstack=%s active_frame=%s breakpoint=%s breakpoint_state=%s" % (self.current_line,self.on_callstack,self.active_frame,self.breakpoint,self.breakpoint_state)
  def __eq__(self,that):
    res = True
    res &= self.current_line == that.current_line
    res &= self.on_callstack == that.on_callstack
    res &= self.active_frame == that.active_frame
    res &= self.breakpoint == that.breakpoint
    res &= self.breakpoint_state == that.breakpoint_state
    return res
  def __ne__(self,that):
    return not self.__eq__(that)

class EditorBase(object):
  def __init__(self,mc):
    self._mc = mc

    # check that the subclass implements the things we need...
    iv = InterfaceValidator(self)
    iv.expect_get_property("widget") # gtk.Widget

    # should have signature (self,file_handle,create_tab)->EditorTabBase
    # If the file couldn't be found, file_handle.exists == False
    iv.expect_method("focus_file(self, file_handle, line_no=-1)") # -> None
    iv.expect_method("get_current_location(self)") # -> None, or raises NoCurrentLocationException
    iv.expect_method("set_line_mark_states(self, file_handle, added, changed, removed)") # -> None

    # innards
    self._overlay = self._mc.new_overlay("Editor overlay") # overlay specific to editor functionality

    # additions to the debug overlay --- which is only visible in breakpoint mode, iirw
    self._mc.always_overlay.add_debug_menu_item('editor.toggle_breakpoint', self._on_toggle_breakpoint)

    # file-open modifier
    self._overlay.add_file_menu_item('editor.quick_open', self._on_quick_open_file);
    self._overlay.add_file_menu_item('editor.goto_method', lambda x,y: self._on_goto_method())

    # monitor current and active frames, breakpoint list
    self._update_marks_scheduled = False
    self._line_marks_by_loc = {} # file_handle -> dictionary(lineno -> LineMarkState)
    mc.debugger.active_frame_changed.add_listener(self._on_active_frame_changed)
    mc.debugger.breakpoints.changed.add_listener(self._on_breakpoints_changed)

  def destroy(self):
    self.mc.debugger.active_frame_changed.remove_listener(self._on_active_frame_changed)
    self.mc.debugger.breakpoints.changed.remove_listener(self._on_breakpoints_changed)

  # public properties
  @property
  def mc(self):
    return self._mc

  @property
  def overlay(self):
    return self._overlay


  # stuff called by maincontrol
  def show(self):
    self.widget.show()
  def hide(self):
    self.widget.hide()
  def enable(self):
    self.widget.set_sensitive(True)
  def disable(self):
    self.widget.set_sensitive(False)
  def focus_location(self,loc):
    if loc.has_file_location:
      fh = self.mc.filemanager.find_file(loc.filename)
      log2("Focusing loc=%s with fh=%s", loc, fh)
      self.focus_file(fh, loc.line_num) # may not exist! that is up to the child to handle
    else:
      print "Haven't implemented disassembly viewing yet"

  # called by subclasses to toggle a breakpoint, should they so-desire
  def toggle_breakpoint(self,loc):
    # look for breakpoints by actual location, first
    log2("Toggling breakpoint at %s", loc)
    b = [x for x in self._mc.debugger.breakpoints if loc in x.actual_location_list]
    if len(b) != 0:
      log2("Found existing breakpoint %s by actual location, removing...", b[0])
      self._mc.debugger.breakpoints.remove(b[0])
      return

    # now, look for breakpoints by requested location
    b = [x for x in self._mc.debugger.breakpoints if x.location == loc]
    if len(b) != 0:
      log2("Found existing breakpoint %s by requested location, removing...", b[0])
      self._mc.debugger.breakpoints.remove(b[0])
      return

    # nothign found, create one
    b = debugger.Breakpoint(loc)
    log2("Creating new breakpoint %s for %s...", b, loc)
    self._mc.debugger.breakpoints.append(b)
    log2("Breakpoint creation done")


  # actual events that trigger mark changes
  def _on_active_frame_changed(self):
    # focus the active location
    if self._mc.debugger.active_thread: # we probably just went from running to break...
      log2("Active frame changed. Active thread is %s", self._mc.debugger.active_thread);
      fn = self._mc.debugger.active_thread.active_frame_number
      cs = self._mc.debugger.active_thread.call_stack
      self.focus_location(cs[fn].location)

    # update marks
    self._schedule_update_marks()


  def _on_breakpoints_changed(self):
    self._schedule_update_marks()

  def _schedule_update_marks(self):
    """
    This function allows multiple update marks to be coalesced
    together, hopefully reducing the number of times we hit the editor backend.
    """
    if self._update_marks_scheduled:
      return
    self._update_marks_scheduled = True
    def do_update_marks():
      self._update_marks_scheduled = False
      self._update_marks()
    MessageLoop.add_message(do_update_marks)

  def _dump_marks(self, d):
    if len(d):
      log0("<current marks>")
    for k in d:
      v = d[k]
      log0(" %s: %i marks" % (k, len(v)))
      for l in v:
        log0("  %3i: %s" % (l, v[l]))
    if len(d):
      log0("</current marks>")


  def _update_marks(self):
    # make a new marks table
    new_line_marks_by_loc = {}

    # helper function to create a mark in the nw_marks_table or return a dummy mark if needeed
    def getmark(loc):
      if loc.has_file_location == False:
        return LineMarkState() # empty one, let it get gc'd
      fh =  self.mc.filemanager.find_file(loc.filename)
      if not fh.exists: # we don't have this tab in the UI, ignore it
        return LineMarkState() # empty one, let it get gc'd
      if not new_line_marks_by_loc.has_key(fh):
        new_line_marks_by_loc[fh] = {}
      if not new_line_marks_by_loc[fh].has_key(loc.line_num):
        new_line_marks_by_loc[fh][loc.line_num] = LineMarkState()
      return new_line_marks_by_loc[fh][loc.line_num]

    # go through breakpoints and add them table
    if len(self._mc.debugger.processes):
      for b in self._mc.debugger.breakpoints:
        if b.all_valid:
          for loc in b.actual_location_list:
            m = getmark(loc)
            m.breakpoint = True
            m.breakpoint_state = 'all'
        elif b.some_valid:
          for loc in b.actual_location_list:
            m = getmark(loc)
            m.breakpoint = True
            m.breakpoint_state = 'some'
        else:
          for loc in b.actual_location_list:
            m = getmark(loc)
            m.breakpoint = True
            m.breakpoint_state = 'none'
    else:
      for b in self._mc.debugger.breakpoints:
        m = getmark(b.location)
        m.breakpoint = True
        m.breakpoint_state = 'all'

    # add current and active frames to the table
    if self._mc.debugger.active_thread: # we probably just went from running to break...
      afn = self._mc.debugger.active_thread.active_frame_number
      cs = self._mc.debugger.active_thread.call_stack
      getmark(cs[0].location).current_line = True
      if afn != 0:
        getmark(cs[afn].location).active_frame = True
      for f in cs[1:]:
        getmark(f.location).on_callstack = True

    # compute changes between self._line_marks_by_loc and new_line_marks_by_loc
    # firing tab.set_line_mark_state for:
    # - newly-unmarked lines [in the old table, not in the new table]
    # - newly-marked lines, or for un
    # - any lines that have changed in value
#    log1("update_marks():")
#    if get_loglevel() >= 2:
#      self._dump_marks(self._line_marks_by_loc)

    all_keys = set(new_line_marks_by_loc.keys()).union(self._line_marks_by_loc.keys())
    for fh in all_keys:
      if new_line_marks_by_loc.has_key(fh):
        new_line_dict = new_line_marks_by_loc[fh]
      else:
        new_line_dict = {} # this file marks, now it doesn't

      if self._line_marks_by_loc.has_key(fh) == False:
        old_line_dict = {}
      else:
        old_line_dict = self._line_marks_by_loc[fh]

      delta = diff(old_line_dict.keys(), new_line_dict.keys())

      # unmark lines that were removed
      removed_lines = []
      for line_num in delta.removed:
#        log1("  %s:%i unmarked", fh.basename, line_num)
        removed_lines.append(line_num)

      # set line mark state for tabs that have changed
      changed_lines = {}
      for line_num in delta.unchanged:
        mark = new_line_dict[line_num]
        if mark != old_line_dict[line_num]:
#          log1("  %s:%i changed to %s", fh.basename, line_num, mark)
          changed_lines[line_num] = mark

      # just set added marks
      added_lines = {}
      for line_num in delta.added:
        mark = new_line_dict[line_num]
#        log1("  %s:%i added as %s", fh.basename, line_num, mark)
        added_lines[line_num] = mark

      # tell the tab about it
      self.set_line_mark_states(fh, added_lines, changed_lines, removed_lines)

    # we're done
    self._line_marks_by_loc = new_line_marks_by_loc

  # other innards
  def _on_quick_open_file(self,*unused):
    dlg = QuickOpenDialog(self._mc.settings, self._mc.filemanager.progdb)
    res = dlg.run()
    dlg.hide()
    if res == gtk.RESPONSE_OK:
      for fn in dlg.selected_files:
        fh = self._mc.filemanager.find_file(fn)
        if fh.exists:
          self.focus_file(fh)
          self._do_grab_focus()

  def open_file(self,requested_filename):
    fh = self.mc.filemanager.find_file(requested_filename)
    if fh.exists:
      self.focus_file(fh)
      self._do_grab_focus()

  def _do_grab_focus(self):
    if hasattr(self,'grab_focus'):
      self.grab_focus()

  def _on_goto_method(self):
    try:
      loc = self.get_current_location()
    except NoCurrentLocationException:
      return

    assert(loc.has_file_location)
    fh = self.mc.filemanager.find_file(loc.filename)
    assert(fh.exists)

    dlg = GotoMethodDialog(self._mc.filemanager.progdb, fh.absolute_name)
    res = dlg.run()
    if res == gtk.RESPONSE_OK:
      ln = dlg.selected_line_number
      dlg.destroy()
      self.focus_file(fh, ln)
      self._do_grab_focus()

  # f9 toggle breakpoint impl
  def _on_toggle_breakpoint(self,*args):
    try:
      loc = self.get_current_location()
    except NoCurrentLocationException:
      pass
    else:
      self.toggle_breakpoint(loc)
