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

class Filter(object):
  def __init__(self,text):
    recs = text.split(" ")
    self._regexes = []
    for rec in recs:
      self._regexes.append(re.compile(rec))
  def search(self,text):
    for regex in self._regexes:
      if not regex.search(text):
        return False
    return True
class AlwaysFailFilter(object):
  def search(self,text):
    return False

class AttachToProcessDialog(gtk.Dialog):
  def __init__(self, settings,hidden_pids=[]):
    gtk.Dialog.__init__(self)
    self._settings = settings
    self._settings.register("AttachToProcessDialog_ShowAllProcesses", bool, False)
    self._settings.register("AttachToProcessDialog_FilterText", str, "")
    self.set_title("Attach to proces...")
    self.set_size_request(800,650)
    self.add_button("_Attach",gtk.RESPONSE_OK)
    self.add_button("Cancel",gtk.RESPONSE_CANCEL)

    self._hidden_pids = hidden_pids
    model = gtk.ListStore(object)
    filtered_model = model.filter_new()
    try:
      self._filter = Filter(self._settings.AttachToProcessDialog_FilterText)
    except:
      print "Warning: AttachToProcessDialog_FilterText is not a valid regexp."
      self._settings.set_temporarily("AttachToProcessDialog_FilterText","")
      self._filter = Filter("")

    def is_visible(model, it):
      obj = model.get(it, 0)[0]
      if obj == None:
        return True
      if self._filter.search(obj.args):
        return True
      else:
        return False
    filtered_model.set_visible_func(is_visible)

    treeview = gtk.TreeView(filtered_model)
    treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
    treeview.get_selection().connect('changed', self._on_treeview_selection_changed)

    text_cell_renderer = gtk.CellRendererText()

    def add_column(title,accessor_cb):
      column = gtk.TreeViewColumn(title, text_cell_renderer)
      column.set_cell_data_func(text_cell_renderer, lambda column, cell, model, iter: cell.set_property('text', accessor_cb(model.get(iter,0)[0])))
      treeview.append_column(column)
      return column
    add_column("PID",lambda obj: obj.pid)
    add_column("User",lambda obj: obj.username)
    add_column("Command",lambda obj: obj.args)

    def on_destroy(*args):
      self.response(gtk.RESPONSE_CANCEL)
    self.connect('destroy', on_destroy)

    refresh_button = gtk.Button("_Refresh")
    refresh_button.connect('clicked', lambda *args: self.refresh())

    show_all_users_checkbox = gtk.CheckButton("Show all _users")
    show_all_users_checkbox.set_active(self._settings.AttachToProcessDialog_ShowAllProcesses)
    def on_toggled(*args):
      self._settings.AttachToProcessDialog_ShowAllProcesses = show_all_users_checkbox.get_active()
      self.refresh()
    show_all_users_checkbox.connect('toggled',on_toggled)

    filter_entry = gtk.Entry()
    filter_entry.set_text(self._settings.AttachToProcessDialog_FilterText)
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
    table_options_hbox.pack_start(show_all_users_checkbox,False,False,0)
    table_options_hbox.pack_end(refresh_button,False,False,0)
    table_vbox.pack_start(treeview_scroll_window,True,True,0)
    table_vbox.pack_start(filter_entry,False,True,0)
    treeview_scroll_window.add(treeview)
    vbox.show_all()

    # remember things that need remembering
    self._treeview = treeview
    self._filtered_model = filtered_model
    self._model = model

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
    text = entry.get_text()
    try:
      self._filter = Filter(text)
      self._settings.AttachToProcessDialog_FilterText = text
    except Exception, ex:
      log0("Regexp error: %s", str(ex)) # TODO(nduca) put up a warning that this isn't a valid regex
      self._filter = AlwaysFailFilter()
    self._filtered_model.refilter()


  def refresh(self):
    # save the selection
    # update the model
    show_all_users = self._settings.AttachToProcessDialog_ShowAllProcesses
    procs = ProcessUtils.get_process_list(show_all_users)
    self._model.clear()
    for p in procs:
      if p.pid in self._hidden_pids:
        continue
      row = self._model.append()
      self._model.set(row, 0, p)

    # TODO --- restore previous selection, if possible
    if len(self._filtered_model) > 0:
      self._treeview.get_selection().select_path((0,))

  def _on_treeview_selection_changed(self, selection):
    self.set_response_sensitive(gtk.RESPONSE_OK,selection.count_selected_rows() != 0)

  @property
  def selected_pids(self):
    model,rows = self._treeview.get_selection().get_selected_rows()
    pids = []
    for path in rows:
      iter = model.get_iter(path)
      obj = model.get(iter,0)[0]
      pids.append(obj.pid)
    return pids

if __name__ == "__main__":
  dlg = AttachToProcessDialog()
  resp = dlg.run()
  if resp == gtk.RESPONSE_OK:
    print dlg.selected_pids
