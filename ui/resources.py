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
import os.path
import pango
import weakref
import tempfile
from util import *

class Resource(object):
  def __init__(self, name):
    self._name = name
  @property
  def name(self):
    return self._name

class KeyboardActionResource(Resource):
  def __init__(self, name, keyname, modifiers):
    Resource.__init__(self, name)
    self.keyname = keyname
    self.modifiers = modifiers

class MenuResource(Resource):
  def __init__(self, name, text):
    Resource.__init__(self, name)
    self.text = text

class MenuItemResource(Resource):
  def __init__(self, name, text, keyname, modifiers):
    Resource.__init__(self, name)
    self.text = text
    self.keyname = keyname
    self.modifiers = modifiers

class TabPageResource(Resource):
  def __init__(self, name, panel_id, title):
    Resource.__init__(self, name)
    self.panel_id = panel_id
    self.title = title

class Resources(object):
  def __init__(self, settings, base_dir):
#    gtk.rc_parse(os.path.join(base, "rc/main.gtkrc"))

    self._settings = settings
    self.base_dir = base_dir

    # breakpoint marks
    ###########################################################################
    marks = [
      "current_line",
      "current_line_and_break",
      "current_line_and_break_disabled",
      "on_callstack",
      "on_callstack_and_break",
      "on_callstack_and_break_disabled",
      "all_break",    # represents breakpoints that are set correctly on all processes
      "disabled_break",    # represents breakpoints that are set correctly on all processes
      "error_break",    # general error pixmap
      "some_break",    # represents a breakpoint that was applied correctly in one process but not others
      "error"
      ]
    self.mark_resources = {}
    next_id = 0
    for mname in marks:
      res = DynObject()
      res.integer_id = next_id
      next_id += 1
      res.name = mname
      res.el_name = mname.replace("_", "-")
      res.filename = os.path.abspath(os.path.join(base_dir,'images/%s.png' % mname))
      if not os.path.exists(res.filename):
        raise Exception("Missing file: %s" % res.filename)
      res.pixmap = gtk.gdk.pixbuf_new_from_file(res.filename)
      res.pixmap_small_tmpfile = tempfile.NamedTemporaryFile()
      res.filename_small = res.pixmap_small_tmpfile.name
      res.pixmap_small = gtk.gdk.pixbuf_new_from_file_at_size(res.filename, 12, 12)
      res.pixmap_small.save(res.filename_small, 'png')

      self.mark_resources[res.filename] = res
      setattr(self, "mark_%s" % mname, res)

    ###########################################################################

    self.COLOR_CURRENT_LINE="yellow"
    self.COLOR_ACTIVE_FRAME="#b4e4b4"

    # General error pixmap
    self.PIXMAP_ERROR = gtk.gdk.pixbuf_new_from_file(os.path.join(base_dir, 'images/error.png'))

    self.SMALL_FONT_SIZE = 8
    self.CODE_FONT_SIZE = 8
    self._skip_list = []

    self._resources = {}

    is_emacs = settings.Editor == "EmacsEditor"
    is_not_emacs = settings.Editor != "EmacsEditor"
    is_gvim = settings.Editor == "GVimEditor"

    # the following code uses the argsel function
    # this function, in util/functional.py
    #p

    initial_resources = [
      argsel(settings.Editor,
             MenuResource("main_menu.file", "_File"),
             EmacsEditor = MenuResource("main_menu.file", "File")),
      MenuItemResource("main_menu.file.exit", "E_xit", None, 0),
      MenuResource("main_menu.tabs", "T_abs"),
      MenuResource("main_menu.tools", "_Tools"),
      argsel(settings.Editor,
             MenuResource("main_menu.debug", "_Debug"),
             EmacsEditor = MenuResource("main_menu.debug", "Deb_ug")),

      MenuItemResource("tabs.editor", "Editor", 'K', gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK),
      MenuItemResource("tabs.call_stack", "Call stack", 'C', gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK),
      MenuItemResource("tabs.output", "Output", 'O', gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK),
      MenuItemResource("tabs.breakpoints", "Breakpoints", 'B', gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK),
      MenuItemResource("tabs.threads", "Threads", 'H', gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK),
      MenuItemResource("tabs.processes", "Processes", 'P', gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK),
      MenuItemResource("tabs.interactive", "GDB Interaction", 'I', gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK | gtk.gdk.CONTROL_MASK),
      MenuItemResource("tabs.python", "Python", 'Y', gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK | gtk.gdk.CONTROL_MASK),

      TabPageResource("tabpage.call_stack", "panel1", "Call stack"),
      TabPageResource("tabpage.output", "panel1", "Output"),
      TabPageResource("tabpage.breakpoints", "panel2", "Breakpoints"),
      TabPageResource("tabpage.threads", "panel2", "Threads"),
      TabPageResource("tabpage.processes", "panel1", "Processes"),
      TabPageResource("tabpage.interactive", "panel2", "Interactive"),
      TabPageResource("tabpage.python", "panel2", "Python"),


      MenuItemResource('debug.break', "Brea_k", "Break", gtk.gdk.CONTROL_MASK),
      MenuItemResource('debug.step_over', "_Step over", 'F10', 0),
      MenuItemResource('debug.step_into', "Step i_nto", 'F11', 0),
      MenuItemResource('debug.step_out', "Step _out", 'F11', gtk.gdk.SHIFT_MASK),
      MenuItemResource('debug.continue', "Continue", 'F5', 0),
      MenuItemResource('debug.launch_process', "_Launch proces...", None, 0),
      MenuItemResource('debug.attach_to_process', "_Attach to proces...", 'P', gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK | gtk.gdk.SHIFT_MASK),
      MenuItemResource('debug.end_debugging', "_End debugging", 'F5', gtk.gdk.SHIFT_MASK),
      MenuItemResource('debug.run_primary_executable', "Run", "F5", 0),
      MenuItemResource('debug.run_primary_executable_suspended', "_Run (suspended)...", 'F10', 0),

      MenuItemResource('tools.options', "_Options...", None, 0),

      MenuItemResource('editor.toggle_breakpoint', "Toggle _breakpoint", 'F9', 0),
      MenuItemResource('editor.quick_open', "_Quick open...","O",gtk.gdk.SHIFT_MASK | gtk.gdk.MOD1_MASK),
      MenuItemResource('editor.goto_method', "Go to _method or tag...", 'M', gtk.gdk.MOD1_MASK),

      MenuItemResource('breakpoints.new_breakpoint', "New _breakpoint", 'B', gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK),

      KeyboardActionResource('source_view_editor.focus_tab_1', "1", gtk.gdk.CONTROL_MASK),
      KeyboardActionResource('source_view_editor.focus_tab_2', "2", gtk.gdk.CONTROL_MASK),
      KeyboardActionResource('source_view_editor.focus_tab_3', "3", gtk.gdk.CONTROL_MASK),
      KeyboardActionResource('source_view_editor.focus_tab_4', "4", gtk.gdk.CONTROL_MASK),
      KeyboardActionResource('source_view_editor.focus_tab_5', "5", gtk.gdk.CONTROL_MASK),
      KeyboardActionResource('source_view_editor.focus_tab_6', "6", gtk.gdk.CONTROL_MASK),
      KeyboardActionResource('source_view_editor.focus_tab_7', "7", gtk.gdk.CONTROL_MASK),
      KeyboardActionResource('source_view_editor.focus_tab_8', "8", gtk.gdk.CONTROL_MASK),
      KeyboardActionResource('source_view_editor.focus_tab_9', "9", gtk.gdk.CONTROL_MASK),

      ]

    for r in initial_resources:
      if self._resources.has_key(r.name):
        log0("A resource named %s already exists" % r.name)
        raise Exception("Resource name conflict on %s" % r.name)
      self._resources[r.name] = r

  def get_resource_of_type(self,t,name):
    try:
      r = self._resources[name]
    except KeyError:
      raise KeyError("No resource named %s" % name)

    if not isinstance(r, t):
      reason = "Resource type mismatch on %s. Expected %s, got %s" % (name, t, type(r))
      raise Exception(reason)
    return r

  def add_fontsize_skip(self,w):
    r = weakref.ref(w)
    self._skip_list.append(r)

  def apply_small_fontsize(self, w):
    self.apply_fontsize(w,self.SMALL_FONT_SIZE)

  def apply_fontsize(self, w, sz):
    skip = set()
    for r_ in self._skip_list:
      r = r_()
      if r:
        skip.add(r)

    f_ = w.get_style().font_desc.copy()
    f_.set_size(sz*pango.SCALE)
    self._apply_font_recursive(skip,w,f_)

  def _apply_font_recursive(self, skip, w, f_):
    if w in skip:
      return
    w.modify_font(f_)
    if isinstance(w,gtk.Notebook):
      for i in range(w.get_n_pages()):
        page = w.get_nth_page(i)
        label = w.get_tab_label(page)
        self._apply_font_recursive(skip, label, f_)
        self._apply_font_recursive(skip, page, f_)
      w.set_property('tab-border', 0)
      w.set_property('show-border', False)


    elif isinstance(w,gtk.TreeView):
      for c in w.get_columns():
        if not c.get_widget():
          l = gtk.Label(c.get_title())
          l.show()
          c.set_widget(l)
        self._apply_font_recursive(skip, c.get_widget(),f_)
        for cr in c.get_cell_renderers():
          if isinstance(cr, gtk.CellRendererText):
            cr.font_desc = f_
    elif isinstance(w,gtk.Container):
      for c in w.get_children():
        self._apply_font_recursive(skip, c, f_)

    elif isinstance(w,gtk.Button):
      self.set_property('inner-border', 0)
