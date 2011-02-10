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
from ui.thread_tab import *

class ThreadTabTest(UITestCaseSingle):
  def setUp(self):
    UITestCaseSingle.setUp(self,"tests/apps/test_threads")
  def test_thread_count(self):
    tab = self.run_on_ui(lambda mc: mc.find_tab(ThreadTab))
    self.run_on_ui(lambda mc: self.assertEqual(len(tab._ls), 1))
    main_thread = self.run_on_ui(lambda mc: mc.debugger.active_thread)

    self.run_on_ui(lambda mc: self.assertEqual(mc.debugger.active_thread.call_stack[0].location.line_num, 15))
    self.run_on_ui(lambda mc: mc.debugger.active_thread.begin_step_over().wait()) # line 16
    self.run_on_ui(lambda mc: self.assertEqual(mc.debugger.active_thread.call_stack[0].location.line_num, 16))

    # verify that the current thread is yellow
    def step2(mc):
      self.assertEqual(len(tab._ls), 2)
      cur_color = mc.resources.COLOR_CURRENT_LINE
      for i in tab._ls:
        if i[BGCOLOR_COLUMN] == cur_color:
          self.assertEqual(i[ID_COLUMN], main_thread)
        else:
          self.assertNotEqual(i[ID_COLUMN], main_thread)

    self.run_on_ui(step2)

    # switch to thread "2", make sure we switched
