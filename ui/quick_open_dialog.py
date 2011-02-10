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
import subprocess
import cStringIO as StringIO
import re
import time

from butter_bar import *


class QuickOpenDialog(gtk.Dialog):
  def __init__(self, settings, progdb):
    gtk.Dialog.__init__(self)
    settings.register("QuickOpenDialog_FilterText", str, "")
    self._settings = settings
    self._progdb = progdb
    self.set_title("Quick open...")
    self.set_size_request(1000,400)
    self.add_button("_Open",gtk.RESPONSE_OK)
    self.add_button("Cancel",gtk.RESPONSE_CANCEL)

    model = gtk.ListStore(object)

    treeview = gtk.TreeView(model)
    treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
    treeview.get_selection().connect('changed', self._on_treeview_selection_changed)

    text_cell_renderer = gtk.CellRendererText()

    def add_column(title,accessor_cb):
      column = gtk.TreeViewColumn(title, text_cell_renderer)
      column.set_cell_data_func(text_cell_renderer, lambda column, cell, model, iter: cell.set_property('text', accessor_cb(model.get(iter,0)[0])))
      treeview.append_column(column)
      return column
    add_column("File",lambda obj: os.path.basename(obj))
    add_column("Path",lambda obj: os.path.dirname(obj))

    def on_destroy(*args):
      self.response(gtk.RESPONSE_CANCEL)
    self.connect('destroy', on_destroy)

    truncated_bar = ButterBar()
    refresh_button = gtk.Button("_Refresh")
    refresh_button.connect('clicked', lambda *args: self.refresh())

    reset_button = gtk.Button("Rese_t Database")
    reset_button.connect('clicked', lambda *args: self._reset_database())


    stats_label = gtk.Label()
    MessageLoop.add_delayed_message(self._update_stats,250, stats_label)

    filter_entry = gtk.Entry()
    filter_entry.set_text(self._settings.QuickOpenDialog_FilterText)
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
    table_options_hbox.pack_start(reset_button,False,False,0)
    table_options_hbox.pack_start(stats_label,False,False,10)
    table_options_hbox.pack_end(refresh_button,False,False,0)
    table_vbox.pack_start(treeview_scroll_window,True,True,0)
    table_vbox.pack_start(truncated_bar,False,True,0)
    table_vbox.pack_start(filter_entry,False,True,0)
    treeview_scroll_window.add(treeview)
    vbox.show_all()

    truncated_bar.hide()

    # remember things that need remembering
    self._treeview = treeview
    self._model = model
    self._truncated_bar = truncated_bar

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

    if keyname in ("Up", "Down", "Page_Up", "Page_Down", "Left", "Right"):
      return redirect()
    elif keyname == "space" and event.state & gtk.gdk.CONTROL_MASK:
      return redirect()
    elif keyname == "a" and event.state & gtk.gdk.CONTROL_MASK:
      return redirect()
    elif keyname == 'Return':
      self.response(gtk.RESPONSE_OK)

  def _on_filter_text_changed(self,entry):
    text = entry.get_text()
    try:
      re.compile(text)
      self._settings.QuickOpenDialog_FilterText = text
      self.refresh()
    except Exception, ex:
      log0("Regexp error: %s" % str(ex)) # TODO(nduca) put up a warning that this isn't a valid regex


  def _update_stats(self,stats_label):
    w = self._progdb.call_async_waitable.get_stats()
    w.when_done(lambda v: stats_label.set_text(v))
    return self.get_property('visible')

  def _reset_database(self):
    self._progdb.call.reset()
    self.refresh()

  def refresh(self):
    # TODO(nduca) save the selection

    # update the model based on result
    def on_result(files):
      start_time = time.time()
      self._treeview.freeze_child_notify()
      self._treeview.set_model(None)

      self._model.clear()
      if len(files) and files[-1] == "<TRUNCATED>":
        truncated = True
        del files[-1]
      else:
        truncated = False

      for f in files:
        row = self._model.append()
        self._model.set(row, 0, f)

      self._treeview.set_model(self._model)
      self._treeview.thaw_child_notify()

      if truncated:
        self._truncated_bar.text = "Search was truncated at %i items" % len(files)
        self._truncated_bar.show()
      else:
        self._truncated_bar.hide()

      elapsed = time.time() - start_time
      log1("Model update time: %0.3fms" % (elapsed * 1000))

      if len(self._model) > 0:
        self._treeview.get_selection().select_path((0,))

    if self._settings.QuickOpenDialog_FilterText != "":
      ft = str(self._settings.QuickOpenDialog_FilterText)
      log2("QuickOpenDialog: Calling progdb %s", ft)
      w = self._progdb.call_async_waitable.find_files_matching(ft)
      w.when_done(on_result)

#      res = self._progdb.call.find_files_matching(ft)
#      on_result(res)
    else:
      self._model.clear()


  def _on_treeview_selection_changed(self, selection):
    self.set_response_sensitive(gtk.RESPONSE_OK,selection.count_selected_rows() != 0)

  @property
  def selected_files(self):
    model,rows = self._treeview.get_selection().get_selected_rows()

    files = []
    for path in rows:
      iter = model.get_iter(path)
      obj = model.get(iter,0)[0]
      files.append(obj)
    return files

if __name__ == "__main__":
  set_loglevel(2)
  import progdb
  db = RemoteClass(progdb.Database)
  db.call.add_search_path("./tests")
  dlg = QuickOpenDialog(new_settings(),db)
  resp = dlg.run()
  dlg.hide()
  if resp == gtk.RESPONSE_OK:
    print dlg.selected_files
  db.shutdown()
