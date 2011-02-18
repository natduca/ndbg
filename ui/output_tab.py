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
import vte
import os
import os.path

from tab_interface import *
from debugger import *

class OutputTab(gtk.VBox):
  def __init__(self,mc):
    TabInterface.validate_implementation(self)
    gtk.VBox.__init__(self)
    self._id = None
    self._mc = mc

    self._mc.settings.register("OutputTab_ScrollbackLines", int, 1000)

    # ls
    self._ls = PListStore(Text = str, Pty = object, Term = object)

    # cbox
    cbox = gtk.ComboBox(self._ls)
    cell = gtk.CellRendererText()
    cbox.pack_start(cell, True);
    cbox.add_attribute(cell, 'text', self._ls.Text)
    self._cbox = cbox
    self.pack_start(cbox,False,False,0)
    cbox.connect('changed', self._on_active_pty_changed)

    # term box
    term_box = gtk.VBox() # gtk.ScrolledWindow()
#    term_box.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self._term_box = term_box

    self.pack_start(term_box,True,True,0)

    self.show_all()

    # connect up to debugger...
    mc.debugger.ptys.item_added.add_listener(self._on_pty_added)
    mc.debugger.ptys.item_deleted.add_listener(self._on_pty_deleted)
    mc.debugger.active_frame_changed.add_listener(self._on_active_frame_changed)

    # active pty
    self._active_pty = None

    # add any ptys that were alive when we were created
    for i in range(len(mc.debugger.ptys)):
      pty = mc.debugger.ptys[i]
      self._on_pty_added(i,pty)
    if len(self._ls) and self._cbox.get_active() == -1:
      self._cbox.set_active(0)

  # tabbase interface
  @property
  def id(self):
    return self._id
  @id.setter
  def id(self,id):
    self._id = id

  def on_rerun(self): # called by MC when the program is re-run
    self._ls.clear()

  # terminal creation
  def _on_pty_added(self,idx,pty):
    r = self._ls.append()
    r.Text = pty.name
    r.Pty = pty
    r.Term = vte.Terminal()
    r.Term.set_property('scrollback-lines', self._mc.settings.OutputTab_ScrollbackLines)

#    r.Term.set_size(80, 8)
    r.Term.set_pty(pty.master_fd)
    desc = r.Term.get_font().copy()
    desc.set_size(self._mc.resources.SMALL_FONT_SIZE*pango.SCALE)
    r.Term.set_font(desc)
    pty.name_changed.add_listener(self._on_pty_renamed)
    if len(self._ls) and self._cbox.get_active() == -1:
      self._cbox.set_active(0)

  def _on_pty_renamed(self,pty):
    r = self._ls.find(lambda x: x.Pty == pty)
    r.Text = pty.name

  def _on_pty_deleted(self,idx,pty):
#    if self._active_pty == pty:
#      if len(self._ls) and self._cbox.get_active() == -1:
#        self._cbox.set_active(0)
#      else:
#        self._cbox.set_active(-1)
    r = self._ls.find(lambda x: x.Pty == pty)
    r.Text = pty.name + " <defunct>"
    pty.name_changed.remove_listener(self._on_pty_renamed)
#    r = self._ls.find(lambda r: r.Pty == pty)
#    self._ls.remove(r)

  # ignore for now...
  def _on_active_frame_changed(self):
    pass

  # active changed
  def _on_active_pty_changed(self, x):
    if self._cbox.get_active_iter() == None:
      self._set_active_pty(None)
    else:
      row = self._ls[self._cbox.get_active_iter()]
      self._set_active_pty(row.Pty)

  # active pty
  def _set_active_pty(self,pty):
    # find item in the ls
    if self._active_pty != None:
      self._term_box.remove(self._term_box.get_children()[0])

    self._active_pty = pty

    # make the new pty active
    if self._active_pty:
      r = self._ls.find(lambda r: r.Pty == pty)
      self._term_box.add(r.Term)
      self.show_all()

  # not sure what this shit does
  def _update_combobox(self):
    pass
#    md_combo = gtk.combo_box_new_text()
#    for i in range(1,_MAX_DEPTH+1):
#      md_combo.append_text("%s" % i)
#    md_combo.append_text("No limit");
#    md_combo.set_active(_MAX_DEPTH) # "no limit"

