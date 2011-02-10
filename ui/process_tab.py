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

from debugger import *
from tab_interface import *

ICON_COLUMN=0
ID_COLUMN=1
FE_ID_COLUMN=2
PID_COLUMN=3
NAME_COLUMN=4
STATUS_COLUMN=5
ARGS_COLUMN=6
BGCOLOR_COLUMN=7

class ProcessTab(gtk.VBox):
  def __init__(self,mc):
    TabInterface.validate_implementation(self)
    gtk.VBox.__init__(self)
    self._id = None
    self._mc = mc
    self._ls = gtk.ListStore(gtk.gdk.Pixbuf,object,str,str,str,str,str,str)

    tv = gtk.TreeView(self._ls)
    self._tv = tv

    pixbufCell = gtk.CellRendererPixbuf()
    pixbufCell.set_property("mode", gtk.CELL_RENDERER_MODE_INERT)
    pixbufColumn = gtk.TreeViewColumn("", pixbufCell, pixbuf=ICON_COLUMN)
    pixbufColumn.unset_flags(gtk.CAN_FOCUS)
    tv.append_column(pixbufColumn)

    plainCell = gtk.CellRendererText()
    tv.append_column(gtk.TreeViewColumn("ID", plainCell, text=FE_ID_COLUMN, background=BGCOLOR_COLUMN))
    tv.append_column(gtk.TreeViewColumn("PID", plainCell, text=PID_COLUMN, background=BGCOLOR_COLUMN))
    tv.append_column(gtk.TreeViewColumn("Name", plainCell, text=NAME_COLUMN, background=BGCOLOR_COLUMN))
    tv.append_column(gtk.TreeViewColumn("Status", plainCell, text=STATUS_COLUMN, background=BGCOLOR_COLUMN))
    tv.append_column(gtk.TreeViewColumn("Arguments", plainCell, text=ARGS_COLUMN, background=BGCOLOR_COLUMN))

    tvs = tv.get_selection()
    tvs.set_mode(gtk.SELECTION_SINGLE)

    tv.connect("row-activated", self._on_row_activated)
    tv.connect("button-press-event", self._on_button_press)

    sw = gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    sw.add(tv)
    self.pack_start(sw,True,True,0)
    self.show_all()

    popup = gtk.Menu()
    popup.show()
    self._popup_kill = add_to_menu(popup, "_Kill", self._on_kill)
    self._popup = popup

    mc.debugger.processes.item_added.add_listener(self._on_process_added)
    mc.debugger.processes.item_deleted.add_listener(self._on_process_deleted)
    mc.debugger.passive_processes.changed.add_listener(self._on_passive_processes_changed)
    mc.debugger.active_frame_changed.add_listener(self._on_active_frame_changed)

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

  def _on_kill(self,*args):
    if self._popup_path:
      iter = self._ls.get_iter(self._popup_path)
      proc = self._ls.get(iter,ID_COLUMN)[0]

      was_running = self._mc.debugger.status == STATUS_RUNNING
      if was_running:
        status_dlg.status = "Stopping other processes..."
        self._mc.debugger.begin_interrupt().wait()
      proc.kill()
      if was_running:
        assert self._mc.debugger.status == STATUS_BREAK
        self._mc.debugger.active_thread.begin_resume()


  def _on_row_activated(self,tv,path,view_column):
    iter = self._ls.get_iter(path)
    p = self._ls.get(iter,ID_COLUMN)[0]
    if p:
      if isinstance(p, DPassiveProcess):
        p.attach()
      else:
        p.make_active()
        return True

  def _on_button_press(self,tv,evt):
    if evt.button == 3:
      pathinfo = self._tv.get_path_at_pos(int(evt.x), int(evt.y))
      self._tv.grab_focus()
      if pathinfo:
        path,col,cellx,celly = pathinfo
        self._popup_path = path
        self._tv.set_cursor(path,col, 0)
        self._popup_kill.set_sensitive(True)
      else:
        self._popup_path = None
        self._popup_kill.set_sensitive(False)

      self._popup.popup(None, None, None, evt.button, evt.time)

  def _on_process_added(self,proc):
    proc.target_executable_changed.add_listener(self._on_process_executable_changed)
    self._update_liststore()
    self._update_colors_and_status()

  def _on_process_executable_changed(self,proc):
    self._update_liststore()
    self._update_colors_and_status()

  def _on_process_deleted(self,proc):
    proc.target_executable_changed.remove_listener(self._on_process_executable_changed)
    self._update_liststore()
    self._update_colors_and_status()

  def _on_passive_processes_changed(self):
    self._update_liststore()
    self._update_colors_and_status()

  def _on_active_frame_changed(self):
    self._update_colors_and_status()

  def _update_liststore(self):
    self._ls.clear()
    for p in self._mc.debugger.processes:
      row = self._ls.append()
      self._ls.set(row,ICON_COLUMN,None) # todo make new pixmap for stopped vs running thread
      self._ls.set(row,ID_COLUMN,p)
      if p.backend_info:
        self._ls.set(row,PID_COLUMN, str(p.backend_info.pid))
      else:
        self._ls.set(row,PID_COLUMN, "<no pid>")
      bn = os.path.basename(p.target_exe)
      self._ls.set(row,NAME_COLUMN, bn)

    for p in self._mc.debugger.passive_processes:
      row = self._ls.append()
      self._ls.set(row,ICON_COLUMN,None) # todo make new pixmap for stopped vs running thread
      self._ls.set(row,ID_COLUMN,p)
      self._ls.set(row,PID_COLUMN,p.backend_info.pid)
      bn = os.path.basename(p.target_exe)
      self._ls.set(row,NAME_COLUMN, bn)
      

  def _compute_status(self,proc):
    if isinstance(proc, DPassiveProcess):
      return "<Availble for debugging...>"
    return proc.status

  def _update_colors_and_status(self):
    show_where = self._mc.debugger.status == STATUS_BREAK
    for row in liststore_get_children(self._ls):
      p = self._ls.get(row,ID_COLUMN)[0]

      if p.frontend_id:
        self._ls.set(row,FE_ID_COLUMN, p.frontend_id)
      else:
        self._ls.set(row,FE_ID_COLUMN, p.frontend_id)
        
      if isinstance(p, DPassiveProcess):
        self._ls.set(row,BGCOLOR_COLUMN, "#D0D0FF")
      elif self._mc.debugger.active_thread in p.threads:
        self._ls.set(row,BGCOLOR_COLUMN, self._mc.resources.COLOR_CURRENT_LINE)
      else:
        self._ls.set(row,BGCOLOR_COLUMN, "white")

      pstat = self._compute_status(p)
        
      self._ls.set(row,STATUS_COLUMN, str(pstat))

      try:
        cmdline = " ".join(p.target_full_cmdline[1:])
      except:
        cmdline = "<unknown>"
      self._ls.set(row,ARGS_COLUMN, cmdline)
