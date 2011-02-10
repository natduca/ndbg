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

class MainOptionsDialog(gtk.Dialog):
  def __init__(self, settings):
    self._destroyed = False
    gtk.Dialog.__init__(self)
    self.set_title("Options")
    self.set_size_request(500,300)

    primary_executable_box = gtk.HBox()
    primary_executable_box.pack_start(gtk.Label("Main executable: "),False,False)
    self._primary_executable = gtk.Entry()
    self._primary_executable.set_activates_default(True)
    primary_executable_box.pack_start(self._primary_executable, True, True)
    self._cached_primary_executable = None

    debug_mode_frame = gtk.Frame("When running the main executable....")
    debug_mode_frame_box = gtk.VBox()
    def set_debug_mode(m):
      settings.RunPrimaryExecutableMode = m
    b0 = gtk.RadioButton(None, "Attach the debugger immediately")
    b0.connect('clicked', lambda *a: set_debug_mode("active"))

    b1 = gtk.RadioButton(b0, "Passively debug the process")
    b1.connect('clicked', lambda *a: set_debug_mode("passive"))

    if settings.RunPrimaryExecutableMode == "active":
      b0.emit('clicked')
    else:
      b1.emit('clicked')

    self.vbox.pack_start(primary_executable_box,False,False,4)
    self.vbox.pack_start(debug_mode_frame,False,False,4)
    debug_mode_frame.add(debug_mode_frame_box)
    debug_mode_frame_box.pack_start(b0,False,False)
    debug_mode_frame_box.pack_start(b1,False,False)

    self.add_button("Cancel", gtk.RESPONSE_CANCEL)
    self.add_button("OK", gtk.RESPONSE_OK)
    self.set_default_response(gtk.RESPONSE_OK)
    self.connect("delete_event", lambda *args: self.response(gtk.RESPONSE_CANCEL))

    self.show_all()

  @property
  def primary_executable(self):
    if self._cached_primary_executable:
      return self._cached_primary_executable
    else:
      import shlex
      cmdline = shlex.split(self._primary_executable.get_text())
      return cmdline

  @primary_executable.setter
  def primary_executable(self, cmdline):
    self._primary_executable.set_text(ProcessUtils.shlex_join(cmdline))
    self._primary_executable.set_position(-1)

  def run(self):
    resp = gtk.Dialog.run(self)
    self.hide()
    self._cached_primary_executable = self.primary_executable
    self._destroyed = True
    self.destroy()
    return resp

if __name__ == "__main__":
  settings = new_settings()
  settings.register("RunPrimaryExecutableMode", str, "active")
  dlg = MainOptionsDialog(settings)
  res = dlg.run()
  if res == gtk.RESPONSE_OK:
    print "ok"
  else:
    print "canceled"
