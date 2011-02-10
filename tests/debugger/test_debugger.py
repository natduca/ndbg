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
from debugger import *
from tests import *
import unittest
import time

class DebuggerTests(unittest.TestCase):
  def setUp(self):
    self.debugger = Debugger()

  def tearDown(self):
    self.debugger.shutdown()

  def test_debugger_launch_nonexistent(self):
    debugger = self.debugger
    raised = True
    self.assertRaises(DebuggerException, lambda: debugger.begin_launch_suspended("does_not_exist").wait())

  def test_debugger_launch_and_kill(self):
    debugger = self.debugger
    proc = debugger.begin_launch_suspended("tests/apps/test1").wait()
    proc.kill()
    self.assertEqual(debugger.status,STATUS_BREAK)

  def test_debugger_launch_and_run_to_completion(self):
    debugger = self.debugger
    proc = debugger.begin_launch_suspended("tests/apps/test_template").wait()
    list(debugger.threads)[0].begin_resume().wait()
    debugger.wait_for_status_break()
    self.assertEqual(debugger.status,STATUS_BREAK)

  def test_debugger_launch_and_interrupt(self):
    debugger = self.debugger
    proc = debugger.begin_launch_suspended("tests/apps/test1").wait()
    list(proc.threads)[0].begin_resume().wait()
    debugger.begin_interrupt().wait()
    proc.kill()

  def test_debugger_launch_twice(self):
    debugger = self.debugger
    proc = debugger.begin_launch_suspended("tests/apps/test1").wait()
    self.assertEqual(debugger.status, STATUS_BREAK)
    proc.kill()
    self.assertEqual(debugger.status, STATUS_BREAK)
    self.assertEqual(len(debugger.processes),0)
    self.assertEqual(len(debugger.threads),0)

    proc = debugger.begin_launch_suspended("tests/apps/test1").wait()
    self.assertEqual(debugger.status, STATUS_BREAK)
    proc.kill()
    self.assertEqual(debugger.status, STATUS_BREAK)
    self.assertEqual(len(debugger.threads),0)
    self.assertEqual(len(debugger.processes),0)

  def test_debugger_launch_multiple(self):
    debugger = self.debugger

    self.assertEqual(debugger.status, STATUS_BREAK)
    proc1 = debugger.begin_launch_suspended("tests/apps/test_multiproc").wait()
    self.assertEqual(debugger.status, STATUS_BREAK)
    self.assertEqual(len(debugger.threads), 1)
    self.assertEqual(len(debugger.processes), 1)
    proc2 = debugger.begin_launch_suspended("tests/apps/test_multiproc").wait()
    self.assertEqual(debugger.status, STATUS_BREAK)
    self.assertEqual(len(debugger.threads), 2)
    self.assertEqual(len(debugger.processes), 2)
    # kill proc1
    proc2.kill()
    self.assertEqual(debugger.status, STATUS_BREAK)
    self.assertEqual(len(debugger.threads), 1)
    self.assertEqual(len(debugger.processes), 1)
    proc1.kill()
    self.assertEqual(debugger.status, STATUS_BREAK)
    self.assertEqual(len(debugger.threads), 0)
    self.assertEqual(len(debugger.processes), 0)

  def test_attach(self):
    debugger = self.debugger
    import subprocess
    proc = subprocess.Popen(["tests/apps/test_multiproc"])
    self.assertTrue(proc != None)

    debugger.begin_attach_to_pid(proc.pid).wait()
    self.assertEqual(debugger.status, STATUS_BREAK)
    self.assertEqual(len(debugger.processes), 1)

    debugger.processes.first.kill()
    time.sleep(0.1)
    self.assertTrue(proc.poll() != None)

  def test_all_backends_stop(self):
    debugger = self.debugger
    proc1 = debugger.begin_launch_suspended("tests/apps/test2").wait()
    proc2 = debugger.begin_launch_suspended("tests/apps/test_multiproc").wait()

    b = Breakpoint(Location(text="test2.c:4"))
    hit = []
    def on_hit():
      self.assertEqual(debugger.status, STATUS_BREAK)# if this fails, then we raised the hit event too soon
      hit.append(1)
    b.on_hit.add_listener(on_hit)
    debugger.breakpoints.append(b)
    self.assertTrue(b.some_valid)

    debugger.threads.first.begin_resume()

    MessageLoop.run_until(lambda: len(hit) == 1)
    log1("Hit breakpoint, waiting on status_break")
    MessageLoop.run_until(lambda: debugger.status == STATUS_BREAK)

    self.assertEqual(debugger.status, STATUS_BREAK)

  def run_until_hit(self,loc):
    debugger = self.debugger
    b = Breakpoint(loc)
    hit = []
    def on_hit():
      self.assertEqual(debugger.status, STATUS_BREAK)# if this fails, then we raised the hit event too soon
      hit.append(1)
    b.on_hit.add_listener(on_hit)
    debugger.breakpoints.append(b)
    if not b.some_valid:
      raise Exception("Could not create breakpoint anywhere: %s" % b.error)

    debugger.active_thread.begin_resume()


    MessageLoop.run_until(lambda: len(hit) == 1)
    debugger.breakpoints.remove(b)

  def test_all_backends_resume_on_step(self):
    debugger = self.debugger
    proc1 = debugger.begin_launch_suspended("tests/apps/test2").wait()
    proc2 = debugger.begin_launch_suspended("tests/apps/test_multiproc").wait()

    self.run_until_hit(Location(text="test2.c:4"))
    trace1 = []
    trace2 = []
    proc1._backend.status_changed.add_listener(lambda be: trace1.append("%s" % be.status))
    proc2._backend.status_changed.add_listener(lambda be: trace2.append("%s" % be.status))


    proc1.threads[0].begin_step_over().wait()

    expected_trace = ["GDB_STATUS_RUNNING","GDB_STATUS_BREAK"]
    self.assertEqual(trace1, expected_trace)
    self.assertEqual(trace2, expected_trace)

  def test_breakpoint_hit_sets_active_thread_correctly(self):
    debugger = self.debugger
    proc1 = debugger.begin_launch_suspended("tests/apps/test2").wait()
    proc2 = debugger.begin_launch_suspended("tests/apps/test_multiproc").wait()

    self.run_until_hit(Location(text="test2.c:4"))

    self.assertEqual(debugger.active_thread, proc1.threads[0])

  def test_debugger_has_multiple_ptys(self):
    debugger = self.debugger
    proc1 = debugger.begin_launch_suspended("tests/apps/test2").wait()
    proc2 = debugger.begin_launch_suspended("tests/apps/test_multiproc").wait()
    self.assertEqual(len(debugger.ptys), 2)
    self.assertTrue(proc1.pty in debugger.ptys)
    self.assertTrue(proc2.pty in debugger.ptys)

  def test_begin_interpreter_exec_async(self):
    debugger = self.debugger
    proc1 = debugger.begin_launch_suspended("tests/apps/test2").wait()
    proc2 = debugger.begin_launch_suspended("tests/apps/test_multiproc").wait()

    # test innards
    tmp = debugger._immediate_exprs.fuzzy_get("f")
    self.assertTrue(tmp[0] != None)

    # test raw execution
    debugger.begin_interpreter_exec("*where",lambda val: 0, squash_exceptions=False)

    # test unfiltered
    res = CallbackDrivenWaitable()
    debugger.begin_interpreter_exec("print 7", lambda val: res.set_done(val),squash_exceptions=False)
    self.assertEqual(res.wait(), "$1 = 7\n")

    # test commands should work
    debugger.begin_interpreter_exec("i th",lambda val: 0, squash_exceptions=False)
    should_work = [
      "info procs",
      "info threads",
      "proc",
      "thread",
      "thread 1",
      "frame",
      "frame 0",
      "up",
      "up 3",
      "down",
      "down 7",
      "info breakpoints",
      ]
    for expr in should_work:
      debugger.begin_interpreter_exec(expr,lambda val: None, squash_exceptions=False)

    # test commands that should raise
    should_raise = [
      "thread 100"
      "frame 400"
      "proc 73"
      ]
    for expr in should_raise:
      self.assertRaises(Exception, lambda val: debugger.begin_interpreter_exec(expr,lambda: None, squash_exceptions=False))

