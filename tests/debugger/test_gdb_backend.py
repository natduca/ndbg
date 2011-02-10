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
import unittest

import debugger
from debugger.gdb_backend import *

# attach
# breakpoints
# call stack parsing
# failure to launch
# program stopped unexpectedly
# threads created/deleted
# multiple processes

class GdbTestBasics(unittest.TestCase):
  def tearDown(self):
    pass

  def test_launch_suspended(self):
    gdb = GdbBackend()
    proc = gdb.begin_launch_suspended("tests/apps/test1").wait()
    self.assertEqual(gdb.status, GDB_STATUS_BREAK)
    self.assertTrue(len(gdb.threads) > 0)
    self.assertTrue(len(gdb.processes) > 0)

    thr = list(gdb.threads)[0]
    proc.kill()
    gdb.shutdown()

  def test_launch_suspended_with_no_executable(self):
    gdb = GdbBackend()
    wait = gdb.begin_launch_suspended("tests/apps/this_doesn_t_exist")
    self.assertRaises(debugger.DebuggerException, lambda: wait.wait())
    gdb.shutdown()

  def test_launch_multiplee(self):
    if GdbBackend.supports_multiple_processes() == False:
      return # we know this will fail so don't do anything...
    gdb = GdbBackend()
    proc1 = gdb.begin_launch_suspended("tests/apps/test_multiproc").wait()
    self.assertEqual(gdb.status, GDB_STATUS_BREAK)
    self.assertEqual(len(gdb.threads), 1)
    self.assertEqual(len(gdb.processes), 1)
    proc2 = gdb.begin_launch_suspended("tests/apps/test_multiproc").wait()
    self.assertEqual(gdb.status, GDB_STATUS_BREAK)
    self.assertEqual(len(gdb.threads), 2)
    self.assertEqual(len(gdb.processes), 2)
    # kill proc1
    proc2.kill()
    self.assertEqual(gdb.status, GDB_STATUS_BREAK)
    self.assertEqual(len(gdb.threads), 1)
    self.assertEqual(len(gdb.processes), 1)
    proc1.kill()
    self.assertEqual(gdb.status, GDB_STATUS_BREAK)
    self.assertEqual(len(gdb.threads), 0)
    self.assertEqual(len(gdb.processes), 0)

  def test_shutdown_no_launch(self):
    gdb = GdbBackend()
    gdb.begin_launch_suspended("tests/apps/test1").wait()
    while len(gdb.processes):
      gdb.kill_process(gdb.processes.first)
    gdb.shutdown()

  def test_shutdown_while_stopped(self):
    gdb = GdbBackend()
    gdb.begin_launch_suspended("tests/apps/test1").wait()
    gdb.shutdown(force=True)

  def test_shutdown_while_running(self):
    gdb = GdbBackend()
    gdb.begin_launch_suspended("tests/apps/test1").wait()
    gdb.begin_resume(gdb.threads.first).wait()
    gdb.shutdown(force=True)

  def test_shutdown_twice_while_stopped(self):
    gdb = GdbBackend()
    gdb.begin_launch_suspended("tests/apps/test1").wait()
    gdb.shutdown(force=True)
    gdb.shutdown(force=True)

  def test_attach(self):
    gdb = GdbBackend()
    import subprocess
    proc = subprocess.Popen(["tests/apps/test_multiproc"])
    self.assertTrue(proc != None)

    p = gdb.begin_attach_to_pid(proc.pid).wait()
    self.assertEqual(gdb.status, GDB_STATUS_BREAK)
    self.assertEqual(len(gdb.processes), 1)

    gdb.kill_process(gdb.processes.first)
    time.sleep(0.1)
    self.assertTrue(proc.poll() != None)
    gdb.shutdown(force=True)

  def test_attach_nonexistent(self):
    gdb = GdbBackend()
    self.assertRaises(debugger.DebuggerException,lambda: gdb.begin_attach_to_pid(999999).wait())
    gdb.shutdown(force=True)


class GdbTestSingleApp(unittest.TestCase):
  def setUp(self, launch_str):
    gdb = GdbBackend()
    gdb.begin_launch_suspended(launch_str).wait()
    self._gdb = gdb

  @property
  def gdb(self):
    return self._gdb

  def tearDown(self):
    self._gdb.shutdown(force=True)


class GdbTest1(GdbTestSingleApp):
  def setUp(self):
    GdbTestSingleApp.setUp(self,"tests/apps/test1")
  def test_resume_and_interrupt(self):
    thr = self.gdb.threads.first
    self.gdb.begin_resume(thr).wait()
    self.assertEqual(self.gdb.status,GDB_STATUS_RUNNING)
    self.gdb.begin_interrupt().wait()
    self.assertEqual(self.gdb.status,GDB_STATUS_BREAK)

  def test_call_stack(self):
    thr = self.gdb.threads.first
    cs = self.gdb.get_call_stack(thr)
    self.assertTrue(len(cs) != 0)
    # sanity check the call stack?
    # we want to verify the various frame parsers... so stop it in a few different ways...

  def test_step(self):
    thr = self.gdb.threads.first
    self.gdb.begin_step_over(thr).wait()
    self.assertEqual(self.gdb.status,GDB_STATUS_BREAK)

  def test_call_stack_after_step_over(self):
    thr = self.gdb.threads.first
    self.gdb.begin_step_over(thr).wait()
    self.assertEqual(self.gdb.status,GDB_STATUS_BREAK)
    cs = self.gdb.get_call_stack(thr)
    self.assertTrue(len(cs) != 0)

  def test_compile_path(self):
    cdir = self.gdb.processes.first.compilation_directory
    self.assertTrue(cdir != None)
    real_cdir = "./tests/apps/"
    self.assertTrue(os.path.samefile(cdir,real_cdir))


class GdbTest3(GdbTestSingleApp):
  def setUp(self):
    GdbTestSingleApp.setUp(self,"tests/apps/test3")


class GdbTestTemplate(GdbTestSingleApp):
  def setUp(self):
    GdbTestSingleApp.setUp(self,"tests/apps/test_template")

  def test_template(self):
    loc = Location(filename="test_template.cc", line_num=6)
    bp = self.gdb.new_breakpoint(loc, lambda: None)
    self.assertTrue(bp.id != None)
    self.assertTrue(len(bp.location_list) == 2)
    self.gdb.delete_breakpoint(bp.id)

  def test_run_to_exit(self):
    w = self.gdb.begin_resume(self.gdb.threads.first).wait()
    MessageLoop.run_while(lambda: self.gdb.status == GDB_STATUS_RUNNING)
    self.assertEqual(len(self.gdb.processes),0)


