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
from tests.ui import *
from ui.process_tab import *

class ProcessTabMultipleProcesses(UITestCaseMultiple):
  def setUp(self):
    UITestCaseMultiple.setUp(self, launch=["tests/apps/test_multiproc", "tests/apps/test_multiproc"])

  def test_process_liststore(self): # test disabled until I can fix gdb_backend's use of "kill inferior"
    self.assertTrue(self.proc1 != None)
    self.assertTrue(self.proc2 != None)

    ptab = self.run_on_ui(lambda mc: mc.find_tab(ProcessTab))

    def step1(mc):
      self.assertTrue(mc.debugger.active_thread != None)
      pass
      self.assertEqual(len(ptab._ls),2)
      current_found = False
      for row in ptab._ls:
        if row[BGCOLOR_COLUMN] == mc.resources.COLOR_CURRENT_LINE:
          current_found = True
      self.assertTrue(current_found)

    self.run_on_ui(step1)


