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
import re
import time

class GotoMethodDialog(gtk.Dialog):
  def __init__(self, progdb, current_filename):
    gtk.Dialog.__init__(self)
    self._progdb = progdb
    self._current_filename = current_filename
    self._method_list = None
    self._method_list_request_pending = False

    self.set_title("Goto tag...")
    self.set_size_request(600,400)
    self.add_button("G_o",gtk.RESPONSE_OK)
    self.add_button("Cancel",gtk.RESPONSE_CANCEL)

    model = gtk.ListStore(object)

    treeview = gtk.TreeView(model)
    treeview.get_selection().connect('changed', self._on_treeview_selection_changed)

    text_cell_renderer = gtk.CellRendererText()

    def add_column(title,accessor_cb):
      column = gtk.TreeViewColumn(title, text_cell_renderer)
      column.set_cell_data_func(text_cell_renderer, lambda column, cell, model, iter: cell.set_property('text', accessor_cb(model.get(iter,0)[0])))
      treeview.append_column(column)
      return column
    add_column("Method",lambda obj: obj[1])
    add_column("Type",lambda obj: obj[2])


    def on_destroy(*args):
      self.response(gtk.RESPONSE_CANCEL)
    self.connect('destroy', on_destroy)

    refresh_button = gtk.Button("_Refresh")
    refresh_button.connect('clicked', lambda *args: self.refresh())

    filter_entry = gtk.Entry()
    filter_entry.set_text("")
    filter_entry.connect('key_press_event', self._on_filter_entry_keypress)
    filter_entry.connect('changed', self._on_filter_text_changed)


    # attach everything up
    vbox = self.vbox
    table_vbox = gtk.VBox()
    treeview_scroll_window = gtk.ScrolledWindow()
    treeview_scroll_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    table_options_hbox = gtk.HBox()
    button_hbox = gtk.HBox()

#    self.get_content_area().add(vbox)
    vbox.pack_start(table_vbox,True,True,1)
    table_vbox.pack_start(table_options_hbox,False,False,0)
    table_options_hbox.pack_end(refresh_button,False,False,0)
    table_vbox.pack_start(treeview_scroll_window,True,True,0)
    table_vbox.pack_start(filter_entry,False,True,0)
    treeview_scroll_window.add(treeview)
    vbox.show_all()


    # remember things that need remembering
    self._treeview = treeview
    self._model = model
    self._filter_entry = filter_entry

    filter_entry.grab_focus()


    self.refresh()


  def _on_filter_entry_keypress(self,entry,event):
    keyname = gtk.gdk.keyval_name(event.keyval)

    def redirect():
      prev = self.get_focus()
      self._treeview.grab_focus()
      ret = self._treeview.emit('key_press_event', event)
      if prev:
        prev.grab_focus()
      return True

    if keyname in ("Up", "Down", "Page_Up", "Page_Down"):
      return redirect()
    elif keyname == "space" and event.state & gtk.gdk.CONTROL_MASK:
      return redirect()
    elif keyname == "a" and event.state & gtk.gdk.CONTROL_MASK:
      return redirect()
    elif keyname == 'Return':
      self.response(gtk.RESPONSE_OK)

  def _on_filter_text_changed(self,entry):
    self.refresh()

  def refresh(self):
    # get the method list
    if self._method_list == None:
      if self._method_list_request_pending:
        log1("Method list pending")
        return
      self._method_list_request_pending = True
      w = self._progdb.call.find_tags_in_file(self._current_filename)
      def got_method_list(ml):
        self._method_list_request_pending = False
        if ml == None:
          log1("No file found. Will try again soon")
          MessageLoop.add_delayed_message(self.refresh,250)
        else:
          log1("Got method list")
          self._method_list = ml
          return self.refresh()
      #w.when_done(got_method_list)
      got_method_list(w)
      return

    # update the model based on the filter
    self._treeview.freeze_child_notify()
    self._treeview.set_model(None)

    self._model.clear()

    filt = self._filter_entry.get_text()
    for m in self._method_list:
      if re.search(filt, m[1], re.I):
        row = self._model.append()
        self._model.set(row, 0, m)

    self._treeview.set_model(self._model)
    self._treeview.thaw_child_notify()

    if len(self._model) > 0:
      self._treeview.get_selection().select_path((0,))

  def _on_treeview_selection_changed(self, selection):
    self.set_response_sensitive(gtk.RESPONSE_OK,selection.count_selected_rows() != 0)

  @property
  def selected_line_number(self):
    model,rows = self._treeview.get_selection().get_selected_rows()
    for path in rows:
      iter = model.get_iter(path)
      obj = model.get(iter,0)[0]
      ln = self._progdb.call.get_line_number_for_tag(self._current_filename, obj[0])
      return ln
    return None

if __name__ == "__main__":
#  set_loglevel(3)
  import progdb
  db = RemoteClass(progdb.Database)
  db.call.add_search_path("./tests")
  time.sleep(2) # let it discover tests # todo remove so we can try this without tests...
  dlg = GotoMethodDialog(db, os.path.abspath("./tests/resources/ctags_test1.cpp"))
  resp = dlg.run()
  dlg.hide()
  if resp == gtk.RESPONSE_OK:
    print dlg.selected_line_number
  db.shutdown()
