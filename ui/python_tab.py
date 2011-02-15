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
import codeop
import sys
import traceback
from tab_interface import *
from nconsole import *
from util import *

class PythonTab(NConsole):
  def __init__(self, mc):
    NConsole.__init__(self, mc)
    TabInterface.validate_implementation(self)
    self._id = None

    self.line_entered.add_listener(self._on_line_entered)

    self._pending_text = ""

    self._locals = { "__name__" : "__console__",
                     "__doc__" : None,
                     'mc' : mc,
                     'debugger' : mc.debugger,
                     'editor' : mc.editor,
                     'filemanager' : mc.filemanager,
                     'set_loglevel' : set_loglevel
                     }

    self._old_displayhook = sys.displayhook
    sys.displayhook = self._on_display

    self.ps1 = ">>> "
    self.ps2 = "... "
    self.output(self.ps1)

  def destroy(self):
    sys.displayhook = self._old_displayhook
    NConsole.destroy(self)

  def _on_display(self, line):
    self.output(repr(line))

  def _on_line_entered(self, line):
    self._pending_text += line
    self._pending_text += "\n"
    try:
      print "trying %s" % self._pending_text
      code = codeop.compile_command(self._pending_text)
      if code:
        self._pending_text = ""
        try:
          exec code in self._locals
        except SystemExit:
          MessageLoop.quit()
        except:
          fmt = traceback.format_exc()
          self.output(fmt)
        else:
          self.output("\n")
        self.output(self.ps1)
      else:
        print "no value"
        self.output(self.ps2)
    except SyntaxError, ex:
      self.output(str(ex))
      self._pending_text = ""
      self.output(self.ps1)

  @property
  def id(self):
    return self._id
  @id.setter
  def id(self,id):
    self._id = id
