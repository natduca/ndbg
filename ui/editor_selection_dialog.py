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

class EditorSelectionDialog(gtk.Dialog):
  def __init__(self):
    gtk.Dialog.__init__(self)
    self.set_title("Select editor...")

    self._editor = None
    def pick(e):
      self._editor = e

    b0 = gtk.RadioButton(None, "GTK")
    b0.connect('clicked', lambda *a: pick("SourceViewEditor"))

    b1 = gtk.RadioButton(b0, "GVim")
    b1.connect('clicked', lambda *a: pick("GVimEditor"))


    b2 = gtk.RadioButton(b0, "Emacs")
    b2.connect('clicked', lambda *a: pick("EmacsEditor"))

    self.vbox.pack_start(gtk.Label("Please select the text editor you want to use:     "))
    self.vbox.pack_start(gtk.HSeparator())
    self.vbox.pack_start(b0)
    self.vbox.pack_start(b1)
    self.vbox.pack_start(b2)
    self.add_button("Select", gtk.RESPONSE_OK)
    self.set_default_response(gtk.RESPONSE_OK)
    self.show_all()

    b0.emit('clicked')
    assert self._editor != None

  def run(self):
    resp = gtk.Dialog.run(self)
    self.hide()
    self.destroy()
    return resp

  @property
  def editor(self):
    return self._editor

if __name__ == "__main__":
  dlg = EditorSelectionDialog()
  res = dlg.run()
  if res == gtk.RESPONSE_OK:
    print dlg.editor
  else:
    print "canceled"
