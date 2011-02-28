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
from . import *
try:
  import gtk
except:
  gtk = None

if gtk:
  class StatusDialog(gtk.Dialog):
    def __init__(self, title="Status"):
      gtk.Dialog.__init__(self)
      self._should_ignore_delete = True
      self.set_title(title)
      self.set_response_sensitive(gtk.RESPONSE_CANCEL,False)
      self.set_size_request(450,300)
      self._label = gtk.Label("dasdfsadfasdfasd")
      self._label.set_line_wrap(True)
      self.get_content_area().add(self._label)
      self.get_content_area().show_all()
      self.set_modal(True)

  #    self.connect("response", self._on_response)
      self.connect("close", self._on_close)
      self.connect("delete_event", self._on_delete)

      self.show()


    def _on_close(self, *args):
      return self._should_ignore_delete
    def _on_delete(self, *args):
      return self._should_ignore_delete

    def destroy_please(self):
      self._should_ignore_delete = False
      StatusDialog.destroy(self)

    @property
    def status(self):
      return self._label.get_text()

    @status.setter
    def status(self, value):
      return self._label.set_text(value)

