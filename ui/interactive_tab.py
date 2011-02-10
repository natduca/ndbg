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
import pygtk
pygtk.require('2.0')
import gtk
import gobject

from debugger import *
from tab_interface import *
from nconsole import *

class InteractiveTab(NConsole):
  def __init__(self,mc):
    TabInterface.validate_implementation(self)
    NConsole.__init__(self, mc)
    self._id = None

    self._last_expr = ""
    self.ps1 = "(ndbg) "
    self.line_entered.add_listener(self._on_line_entered)
    self.output(self.ps1)

  def eval(self, expr):
    def on_result(resp):
      res = str(resp) # fixme

      if not res.endswith("\n"):
        self.output(res + "\n")
      else:
        self.output(res)
      self.output(self.ps1)

    try:
      self.mc.debugger.begin_interpreter_exec(expr,on_result)
    except Exception:
      res = traceback.format_exc()
      self.output(res)

  def _on_line_entered(self, line):
    print line
    if line == "":
      txt = self._last_expr
    else:
      txt = line
    self.eval(txt)
    self._last_expr = txt
    return True

  @property
  def id(self):
    return self._id
  @id.setter
  def id(self,id):
    self._id = id
