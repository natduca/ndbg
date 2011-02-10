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

import time

class MainControlTests1(UITestCaseSingle):
  def setUp(self):
    UITestCaseSingle.setUp(self,"tests/apps/test1")

  def test_step_over(self):
    loc1 = self.run_on_ui(lambda mc: mc.debugger.active_thread.call_stack[0].location)
    self.assertEqual(loc1.line_num, 38)

    self.run_on_ui(lambda mc: mc.debugger.active_thread.begin_step_over().wait())
    loc2 = self.run_on_ui(lambda mc: mc.debugger.active_thread.call_stack[0].location)
    self.assertEqual(loc2.line_num, 39)

  def test_step_into_and_out(self):
    loc1 = self.run_on_ui(lambda mc: mc.debugger.active_thread.call_stack[0].location)
    self.assertEqual(loc1.line_num, 38)

    self.run_on_ui(lambda mc: mc.debugger.active_thread.begin_step_into().wait())
    loc2 = self.run_on_ui(lambda mc: mc.debugger.active_thread.call_stack[0].location)
    self.assertEqual(loc2.line_num, 34)

    self.run_on_ui(lambda mc: mc.debugger.active_thread.begin_step_out().wait())
    loc3 = self.run_on_ui(lambda mc: mc.debugger.active_thread.call_stack[0].location)
    self.assertEqual(loc3.line_num, 38)

class MainControlTests(UITestCaseBase):
  def test_launch(self):
    self.run_on_ui(lambda mc: mc._launch_process("tests/apps/test1"))
    time.sleep(1)
    self.assertNoUnhandledExceptions()
    self.run_on_ui(lambda mc: self.assertTrue(len(mc.debugger.processes) != 0))

  def test_attach(self):
    import subprocess
    proc = subprocess.Popen(["tests/apps/test_multiproc"])
    self.assertTrue(proc != None)

    self.run_on_ui(lambda mc: self.assertEqual(len(mc.debugger.processes), 0))
    self.run_on_ui(lambda mc: mc._attach_to_pids([proc.pid]))
    time.sleep(1)
    self.assertNoUnhandledExceptions()
    self.run_on_ui(lambda mc: self.assertEqual(mc.debugger.status, STATUS_BREAK))
    self.run_on_ui(lambda mc: self.assertEqual(len(mc.debugger.processes), 1))

    self.run_on_ui(lambda mc: mc.debugger.processes.first.kill())
    self.assertTrue(proc.poll() != None)

    self.assertNoUnhandledExceptions()
