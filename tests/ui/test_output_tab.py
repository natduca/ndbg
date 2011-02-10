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
from debugger import *
from ui.output_tab import *

class TestOutputTab(UITestCaseBase):
  def test_output_ls_on_launch(self):
    otab = self.run_on_ui(lambda mc: mc.find_tab(OutputTab))
    proc1 = self.run_on_ui(lambda mc: mc.debugger.begin_launch_suspended("tests/apps/test1").wait())
    self.run_on_ui(lambda mc: self.assertEqual(len(otab._ls), 1))

    proc2 = self.run_on_ui(lambda mc: mc.debugger.begin_launch_suspended("tests/apps/test2").wait())
    self.run_on_ui(lambda mc: self.assertEqual(len(otab._ls), 2))

