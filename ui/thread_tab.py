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

from tab_interface import *
from debugger import *

ICON_COLUMN=0
ID_COLUMN=1
TID_COLUMN=2
PROC_COLUMN=3
WHERE_COLUMN=4
BGCOLOR_COLUMN=5

class ThreadTab(gtk.VBox):
  def __init__(self,mc):
    TabInterface.validate_implementation(self)
    gtk.VBox.__init__(self)
    self._id = None
    self._mc = mc
    self._ls = gtk.ListStore(gtk.gdk.Pixbuf,object,str,str,str,str)

    tv = gtk.TreeView(self._ls)
    self._tv = tv

    pixbufCell = gtk.CellRendererPixbuf()
    pixbufCell.set_property("mode", gtk.CELL_RENDERER_MODE_INERT)
    pixbufColumn = gtk.TreeViewColumn("", pixbufCell, pixbuf=ICON_COLUMN)
    pixbufColumn.unset_flags(gtk.CAN_FOCUS)
    tv.append_column(pixbufColumn)

    plainCell = gtk.CellRendererText()
    tv.append_column(gtk.TreeViewColumn("TID", plainCell, text=TID_COLUMN, background=BGCOLOR_COLUMN))
    tv.append_column(gtk.TreeViewColumn("Process", plainCell, text=PROC_COLUMN, background=BGCOLOR_COLUMN))
    tv.append_column(gtk.TreeViewColumn("Current Location", plainCell, text=WHERE_COLUMN, background=BGCOLOR_COLUMN))

    tvs = tv.get_selection()
    tvs.set_mode(gtk.SELECTION_SINGLE)

    tv.connect("button-press-event", self.on_button_press)
    tv.connect("row-activated", self._on_row_activated)

    sw = gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add(tv)
    self.pack_start(sw,True,True,0)
    self.show_all()

    mc.debugger.threads.changed.add_listener(self._on_threads_changed)
    mc.debugger.active_frame_changed.add_listener(self._on_active_frame_changed)

  @property
  def id(self):
    return self._id
  @id.setter
  def id(self,id):
    self._id = id

  def special_grab_focus(self):
    self._tv.grab_focus()
    def set_cursor(model,path,iter):
      if model.get_value(iter,ID_COLUMN) == self._mc.debugger.active_thread:
        self._tv.set_cursor(path)
    self._ls.foreach(set_cursor)

  def get_selected(self):
    tvs = self._tv.get_selection()
    m, s = tvs.get_selected()
    if s != None:
      return m.get_value(s,ID_COLUMN)
    return None

  def _on_row_activated(self,tv,path,view_column):
    iter = self._ls.get_iter(path)
    t = self._ls.get(iter,ID_COLUMN)[0]
    if t:
      self._mc.debugger.active_thread = t

  def on_button_press(self,tv,evt):
    if evt.button == 3:
      self._popup.popup(None, None, None, evt.button, evt.time)
      return True

  def _on_threads_changed(self):
    self._update_liststore()
    self._update_colors_and_status()

  def _on_active_frame_changed(self):
    self._update_colors_and_status()

  def _update_liststore(self):
    self._ls.clear()
    for t in self._mc.debugger.threads:
      row = self._ls.append()
      self._ls.set(row,ICON_COLUMN,None) # todo make new pixmap for stopped vs running thread
      self._ls.set(row,ID_COLUMN,t)
      self._ls.set(row,TID_COLUMN, str(t.frontend_id))
      self._ls.set(row,PROC_COLUMN, str(t.process))

  def _update_colors_and_status(self):
    show_where = self._mc.debugger.status == STATUS_BREAK
    for row in liststore_get_children(self._ls):
      t = self._ls.get(row,ID_COLUMN)[0]
      if t == self._mc.debugger.active_thread:
        self._ls.set(row,BGCOLOR_COLUMN, self._mc.resources.COLOR_CURRENT_LINE)
      else:
        self._ls.set(row,BGCOLOR_COLUMN, "white")

      if show_where:
        self._ls.set(row,WHERE_COLUMN, str(t.active_frame))
      else:
        self._ls.set(row,WHERE_COLUMN, "")

