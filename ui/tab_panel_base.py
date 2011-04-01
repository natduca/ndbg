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

from util import *
from overlay import *
import ui

class TabPanel(gtk.Notebook):
  def __init__(self, mw, id):
    gtk.Notebook.__init__(self)
    self._id = id
    self._mw = mw
    self.set_tab_pos(gtk.POS_BOTTOM)
    self.set_group_id(0x31415)
    self.connect("page-added", self._on_page_added)
    self.connect("page-removed", lambda *args: self.update_visibility())
    self.connect("create-window", self._on_create_window)
    self.set_name("TabPanel")
    self.set_property('tab-border', 0)
    self.set_property('show-border', False)

  @property
  def id(self):
    return self._id

  def _on_create_window(self,src_notebook, page, x, y):
    print "CreateWindow at %i,%i" % (x, y)
    w = gtk.Window()
    p = TabPanel(self._mw)
    psr = list(page.get_size_request())
    if psr[0] <= 0:
      psr[0] = 300
    if psr[1] <= 0:
      psr[1] = 200
    w.resize(psr[0],psr[1])
    w.move(x-5,y-5)
    w.add(p)
    w.show_all()

    i = src_notebook.get_page_index(page)
    l = src_notebook.get_tab_label(page)
    src_notebook.remove_page(i)
    p.append_page(page,l)
    p.set_tab_reorderable(page,True)
    p.set_tab_detachable(page,True)



  def _on_page_added(self, nb, page, pageNum, *args):
    # page's overlay needs to know that it changed panels
    overlay = self._mw._tab_owner_overlays[page]
    overlay.on_tab_panel_changed(page, self)
    self.update_visibility()

  def update_visibility(self):
    # are all our children hidden?
    one_visible = False
    for i in range(0,self.get_n_pages()):
      if self.get_nth_page(i).get_property('visible'):
        one_visible = True
    if one_visible:
      self.show()
    else:
      self.hide()
  def get_page_index(self,tab):
    for i in range(0,self.get_n_pages()):
      if self.get_nth_page(i) == tab:
        return i
    return -1

  def add_tab(self,tab,title,owner_overlay):
    if tab.get_parent():
      raise Exception("tab is already attached to something")

    self._mw._tab_owner_overlays[tab] = owner_overlay

    l = gtk.Label(title)
    self.append_page(tab,l)
    self.set_tab_reorderable(tab,True)
    self.set_tab_detachable(tab,True)
    self.update_visibility()

  def remove_tab(self,tab):
    if tab.get_parent() != this:
      raise Exception("Not my child")
    for i in range(0,self.get_n_pages()):
      if self.get_page(i) == tab:
        tab.remove_page(i)
        break
    del self._mw._tab_owner_overlays[tab]
    self.update_visibility()

def _is_child_of(w,parent):
  cur = w
  while cur:
    if cur == parent:
      return True
    cur = cur.get_property('parent')
  return False
