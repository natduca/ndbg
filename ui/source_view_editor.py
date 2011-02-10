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


# This class is the GtkSourceView implementation of EditorBase
# Hence, it is called SourceViewEditor
import gtk
import gobject
import os.path

import debugger
from util import *
from editor_base import *
from source_view_tab import SourceViewTab

class SourceViewFileNotFoundTab(gtk.VBox):
  def __init__(self,file_handle):
    EditorTabInterface.validate_implementation(self)
    gtk.VBox.__init__(self,file)
    l = gtk.Label("File not found: %s" % file)
    self._file_handle = file_handle
    self.pack_start(l,True,True,0)
    self.show_all()

  @property
  def file_handle(self):
    return self._file_handle


class SourceViewEditor(EditorBase):
  def __init__(self,mc):
    EditorBase.__init__(self, mc)
    self._notebook = gtk.Notebook()
    self._notebook.set_tab_pos(gtk.POS_TOP)
    self._notebook.set_size_request(1000,400)
    self._tabs_with_files_that_exist = {}

    # control 1 thru 9 modifiers
    self.overlay.add_keyboard_action('source_view_editor.focus_tab_1', lambda: self._focus_nth_tab(0))
    self.overlay.add_keyboard_action('source_view_editor.focus_tab_2', lambda: self._focus_nth_tab(1))
    self.overlay.add_keyboard_action('source_view_editor.focus_tab_3', lambda: self._focus_nth_tab(2))
    self.overlay.add_keyboard_action('source_view_editor.focus_tab_4', lambda: self._focus_nth_tab(3))
    self.overlay.add_keyboard_action('source_view_editor.focus_tab_5', lambda: self._focus_nth_tab(4))
    self.overlay.add_keyboard_action('source_view_editor.focus_tab_6', lambda: self._focus_nth_tab(5))
    self.overlay.add_keyboard_action('source_view_editor.focus_tab_7', lambda: self._focus_nth_tab(6))
    self.overlay.add_keyboard_action('source_view_editor.focus_tab_8', lambda: self._focus_nth_tab(7))
    self.overlay.add_keyboard_action('source_view_editor.focus_tab_9', lambda: self._focus_nth_tab(self._notebook.get_n_pages() - 1))

    self._notebook.connect('page-added', self._on_page_added)
    self._notebook.connect('page-removed', self._on_page_removed)

  @property
  def widget(self):
    return self._notebook


  # EditorBase methods
  ############################################################################
  def focus_file(self, file_handle, line_no = -1):
    if file_handle.exists:
      if not self._tabs_with_files_that_exist.has_key(file_handle.absolute_name):
        v = SourceViewTab(self, file_handle)
        bn = file_handle.basename
        v.show_all()
        self._notebook.append_page(v,gtk.Label(bn))

      if not self._tabs_with_files_that_exist.has_key(file_handle.absolute_name):
        # only happens on shutdown...
        return
      v = self._tabs_with_files_that_exist[file_handle.absolute_name]
      assert v
      self._focus_tab(v)
      if line_no != -1:
        v.focus_line(line_no)
    else:
      # TODO show the file not found tab...
      pass

  def get_current_location(self):
    tab_num = self._notebook.get_current_page()
    tab = self._notebook.get_nth_page(tab_num)
    fh = tab.file_handle
    line_num = tab.get_current_line()
    return fh.make_location(line_num)

  def set_line_mark_states(self, file_handle, added, changed, removed):
    if not file_handle.exists:
      return
    if self._tabs_with_files_that_exist.has_key(file_handle.absolute_name):
      self._tabs_with_files_that_exist[file_handle.absolute_name].set_line_mark_states(added, changed, removed)


  # implementation
  ###########################################################################
  def grab_focus(self):
    if self._notebook.get_n_pages():
      n = self._notebook.get_current_page()
      self._notebook.get_nth_page(n).grab_focus()

  def _on_page_added(self, nb, child, page_num):
    fh = child.file_handle
    if fh.exists:
      self._tabs_with_files_that_exist[fh.absolute_name] = child

  def _on_page_removed(self, nb, child, page_num):
    fh = child.file_handle
    if fh.exists:
      assert self._tabs_with_files_that_exist.has_key(fh.absolute_name)
      del self._tabs_with_files_that_exist[fh.absolute_name]

  def _focus_nth_tab(self,num):
    print "Focusing %i" % num
    if num >= self._notebook.get_n_pages():
      return
    self._notebook.set_current_page(num)
    self._notebook.get_nth_page(num).grab_focus()

  def _focus_tab(self,tab):
    for i in range(self._notebook.get_n_pages()):
      page = self._notebook.get_nth_page(i)
      if page == tab:
        self._notebook.set_current_page(i)
        return
    raise Exception("Tab not found: %s")
