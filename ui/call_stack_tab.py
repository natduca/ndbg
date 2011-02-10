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
import pygtk
pygtk.require('2.0')
import gtk
import gobject

import os.path
import debugger
from tab_interface import *
ICON_COLUMN=0
FRAME_NUM_COLUMN=1
FUNCTION_COLUMN=2
BGCOLOR_COLUMN=3

class CallStackTab(gtk.VBox):
  def __init__(self,mc):
    TabInterface.validate_implementation(self)
    gtk.VBox.__init__(self)
    self._id = None
    self._mc = mc
    self._ls = gtk.ListStore(gtk.gdk.Pixbuf, int,str,str)

    tv = gtk.TreeView(self._ls)
    self._tv = tv

    cell = gtk.CellRendererText()
    pixbufCell = gtk.CellRendererPixbuf()
    tv.append_column(gtk.TreeViewColumn("", pixbufCell, pixbuf=ICON_COLUMN))
    tv.append_column(gtk.TreeViewColumn("Frame", cell, text=FRAME_NUM_COLUMN, background=BGCOLOR_COLUMN))
    tv.append_column(gtk.TreeViewColumn("Function", cell, text=FUNCTION_COLUMN, background=BGCOLOR_COLUMN))

    tvs = tv.get_selection()
    tvs.set_mode(gtk.SELECTION_SINGLE)

    tv.connect("button-press-event", self.on_button_press)
    tv.connect("row-activated", self._on_row_activated)


    sw = gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add(tv)
    self.pack_start(sw,True,True,0)
    self.show_all()

    mc.debugger.active_frame_changed.add_listener(self.on_active_frame_changed)

  @property
  def id(self):
    return self._id
  @id.setter
  def id(self,id):
    self._id = id

  def special_grab_focus(self):
    self._tv.grab_focus()
    fn = self._mc.debugger.active_thread.active_frame_number
    path = (fn, )
    self._tv.set_cursor(path)

  def get_selected_frame_numer(self):
    tvs = self._tv.get_selection()
    m, s = tvs.get_selected()
    if s != None:
      return m.get_value(s,FRAME_NUM_COLUMN)
    return None

  def on_button_press(self,tv,evt):
    if evt.button == 1 and evt.type == gtk.gdk._2BUTTON_PRESS:
      fn = self.get_selected_frame_numer()
      if fn == None:
        self._mc.debugger.active_thread.set_active_frame_number(fn)
        self._mc.focus_editor()

  def _on_row_activated(self,tv,path,view_column):
    iter = self._ls.get_iter(path)
    fn = self._ls.get_value(iter,FRAME_NUM_COLUMN)
    if fn != None:
      self._mc.debugger.active_thread.set_active_frame_number(fn)
      self._mc.focus_editor()

  def on_active_frame_changed(self):
    self._ls.clear()

    # early out if needed
    if not self._mc.debugger.active_thread:
      return

    # update table
    cs = self._mc.debugger.active_thread.call_stack
    for frame in cs:
      row = self._ls.append()
      self._ls.set(row,FRAME_NUM_COLUMN,frame.frame_number)
      self._ls.set(row,FUNCTION_COLUMN, str(frame.location))

    # update coloring...
    activeFrameNum = self._mc.debugger.active_thread.active_frame_number
    for frameNum in range(0,self._ls.iter_n_children(None)):
      row = self._ls.iter_nth_child(None, frameNum)
      if frameNum == 0:
        self._ls.set(row, ICON_COLUMN, self._mc.resources.mark_current_line.pixmap)
        self._ls.set(row, BGCOLOR_COLUMN, self._mc.resources.COLOR_CURRENT_LINE)
      elif frameNum == activeFrameNum:
        self._ls.set(row, ICON_COLUMN, self._mc.resources.mark_on_callstack.pixmap)
        self._ls.set(row, BGCOLOR_COLUMN, self._mc.resources.COLOR_ACTIVE_FRAME)
      else:
        self._ls.set(row, ICON_COLUMN, None)
        self._ls.set(row, BGCOLOR_COLUMN, "white")




