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

from debugger import *
from tab_interface import *

ICON_COLUMN=0
ID_COLUMN=1
LOCATION_COLUMN=2

class BreakpointTab(gtk.VBox):
  def __init__(self,mc):
    TabInterface.validate_implementation(self)
    gtk.VBox.__init__(self)
    self._id = None
    self._mc = mc
    self._ls = gtk.ListStore(gtk.gdk.Pixbuf,object,str)

    tv = gtk.TreeView(self._ls)
    self._tv = tv

    pixbufCell = gtk.CellRendererPixbuf()
    pixbufCell.set_property("mode", gtk.CELL_RENDERER_MODE_INERT)
    pixbufColumn = gtk.TreeViewColumn("", pixbufCell, pixbuf=ICON_COLUMN)
    pixbufColumn.unset_flags(gtk.CAN_FOCUS)
    tv.append_column(pixbufColumn)

#    plainCell = gtk.CellRendererText()
#    tv.append_column(gtk.TreeViewColumn("ID", plainCell, text=ID_COLUMN))

    locCell = gtk.CellRendererText()
    locCell.set_property("editable",True)
    tv.append_column(gtk.TreeViewColumn("Function", locCell, text=LOCATION_COLUMN))



    locCell.connect('edited', self._on_breakpoint_location_edit)

    tvs = tv.get_selection()
    tvs.set_mode(gtk.SELECTION_SINGLE)

    tv.connect("button-press-event", self._on_button_press)
    tv.connect("key_press_event", self._on_key_press)

    popup = gtk.Menu()
    popup.show()
    self._popup_new = add_to_menu(popup, "_New breakpoint", self._on_new_breakpoint)
    self._popup_delete = add_to_menu(popup, "_Delete breakpoint", self._on_delete_breakpoint_under_mouse,None)
    self._popup = popup


    m = self._mc.when_debugging_overlay.add_debug_menu_item('breakpoints.new_breakpoint', self._on_new_breakpoint)

    sw = gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add(tv)
    self.pack_start(sw,True,True,0)
    self.show_all()

    mc.debugger.breakpoints.changed.add_listener(self._on_breakpoints_changed)


  @property
  def id(self):
    return self._id
  @id.setter
  def id(self,id):
    self._id = id

  def get_selected(self):
    tvs = self._tv.get_selection()
    m, s = tvs.get_selected()
    if s != None:
      return m.get_value(s,ID_COLUMN)
    return None

  def _on_new_breakpoint(self,*args):
    dlg = gtk.Dialog("New breakpoint",
                     None,
                     gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                     (gtk.STOCK_OK,gtk.RESPONSE_OK,
                      gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
    hbox = gtk.HBox()
    label = gtk.Label("Location:")
    entry = gtk.Entry()
    entry.set_size_request(400,-1)
    entry.set_activates_default(True)
    hbox.pack_start(label,False,False,4)
    hbox.pack_start(entry,True,True,0)
    hbox.show_all()
    dlg.get_content_area().pack_start(hbox,False,False,0)
    dlg.set_default_response(gtk.RESPONSE_OK)
    resp = dlg.run()
    dlg.hide()

    if resp == gtk.RESPONSE_OK and entry.get_text() != "":
      self.new_breakpoint(entry.get_text())

  def new_breakpoint(self,text):
    l = Location(text=text)
    b = Breakpoint(l)
    self._mc.debugger.breakpoints.append(b)
    return b

  def _on_delete_breakpoint_under_mouse(self,*args):
    pos = self._tv.get_pointer()
    if self._popup_path:
      iter = self._ls.get_iter(self._popup_path)
      b = self._ls.get(iter,ID_COLUMN)
      assert(b)
      self._mc.debugger.breakpoints.remove(b[0])


  def _on_breakpoint_location_edit(self,cell,path,newtext):
    iter = self._ls.get_iter(path)
    b = self._ls.get_value(iter,ID_COLUMN)
    b.location = Location(text=newtext)

  def _on_button_press(self,tv,evt):
    if evt.button == 1 and evt.type == gtk.gdk._2BUTTON_PRESS:
      b = self.get_selected()
      if b and b.some_valid:
        # TODO(nduca): pick the location to focus based on the active process
        self._mc.focus_location(b.actual_location_list[0])
        return True

    elif evt.button == 3:
      pathinfo = self._tv.get_path_at_pos(int(evt.x), int(evt.y))
      self._tv.grab_focus()
      if pathinfo:
        path,col,cellx,celly = pathinfo
        self._popup_path = path
        self._tv.set_cursor(path,col, 0)
        self._popup_delete.set_sensitive(True)
      else:
        self._popup_path = None
        self._popup_delete.set_sensitive(False)

      self._popup.popup(None, None, None, evt.button, evt.time)
      return True

  def _on_key_press(self,tv,evt):
    keyname = gtk.gdk.keyval_name(evt.keyval)
    if keyname == "Return":
      b = self.get_selected()
      if b and b.some_valid:
        # TODO(nduca): pick the location to focus based on the active process
        self._mc.focus_location(b.actual_location_list[0])
        return True
    elif keyname == "Delete":
      b = self.get_selected()
      if b:
        self._mc.debugger.breakpoints.remove(b)

  def _on_breakpoints_changed(self):
    self._breakpoints = self._mc.debugger.breakpoints
    self._update_liststore()

  def _update_liststore(self):
    self._ls.clear()
    r = self._mc.resources
    for b in self._mc.debugger.breakpoints:
      row = self._ls.append()
      if b.all_valid:
        self._ls.set(row,ICON_COLUMN,r.mark_all_break.pixmap)
        self._ls.set(row,ID_COLUMN,b)
        self._ls.set(row,LOCATION_COLUMN, str(b.location))
      elif b.some_valid:
        self._ls.set(row,ICON_COLUMN,r.mark_some_break.pixmap)
        self._ls.set(row,ID_COLUMN,b)
        self._ls.set(row,LOCATION_COLUMN, str(b.location))
      else:
        self._ls.set(row,ICON_COLUMN,r.mark_error_break.pixmap)
        self._ls.set(row,ID_COLUMN,b)
        self._ls.set(row,LOCATION_COLUMN, str(b.location))
