#!/usr/bin/env python2.6
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
import unittest

class TestDebuggerBreakpoints_Test2(unittest.TestCase):
  def setUp(self):
    self._debugger = Debugger()
    self._debugger.begin_launch_suspended("tests/apps/test2").wait()

  def test_create_invalid_breakpoint(self):
    b1 = Breakpoint(Location(text="no_way_this_function_exists"))
    self._debugger.breakpoints.append(b1)
    self.assertEqual(b1.all_valid,False)
    self.assertEqual(b1.some_valid,False)
    self.assertTrue(b1.error != None)
    self.assertEqual(type(b1.error), str)

    b2 = Breakpoint(Location(text="missing_file.c:23"))
    self._debugger.breakpoints.append(b2)
    self.assertEqual(b2.all_valid,False)
    self.assertEqual(b2.some_valid,False)


  def test_breakpoint_on_hit(self):
    thr = self._debugger.threads.first

    b1 = Breakpoint(Location(text="c"))
    self._debugger.breakpoints.append(b1)
    self.assertTrue(b1.all_valid)

    b2 = Breakpoint(Location(text="test2.c:21")) # d
    self._debugger.breakpoints.append(b2)
    self.assertTrue(b2.all_valid)

    # tracing system...
    hit_trace = []
    def trace_and_resume(tv):
      log1("t_a_r %s", tv)
      hit_trace.append(tv)
      self.assertEqual(self._debugger.active_thread, thr)
      thr.begin_resume()

    # bind the breakpoint hit events and run the program
    # we expect the call sequence to be c() d()
    # since d calls c, we expect b1 b2 b1
    b1.on_hit.add_listener(lambda: trace_and_resume("b1"))
    b2.on_hit.add_listener(lambda: trace_and_resume("b2"))
    thr.begin_resume()

    # wait until we have collected 3 events
    MessageLoop.run_until(lambda: len(hit_trace) == 3)

    trace_sr = " ".join(hit_trace)
    self.assertEqual(trace_sr, "b2 b1 b2")

  def tearDown(self):
    self._debugger.shutdown()


class TestDebuggerBreakpoints(unittest.TestCase):
  def setUp(self):
    self._debugger = Debugger(use_multiple_gdb_backends_override=True) # force multiple backends

  def test_breakpoints_applied_after_launch(self):
    b1 = Breakpoint(Location(text="19"))
    self._debugger.breakpoints.append(b1)
    self.assertTrue(b1.all_valid)
    self.assertEqual(len(b1.actual_location_list), 0)

    proc1 = self._debugger.begin_launch_suspended("tests/apps/test1").wait()
    if b1.all_valid == False:
      print b1.error
    self.assertTrue(b1.all_valid)
    self.assertEqual(len(b1.actual_location_list), 1)

    proc2 = self._debugger.begin_launch_suspended("tests/apps/test1").wait()
    self.assertEqual(len(self._debugger._backends),2)

    self.assertTrue(b1.all_valid)
    self.assertEqual(len(b1.actual_location_list), 1)
    self.assertEqual(len(b1._backend_breakpoints), 2)

    proc2.kill()
    self.assertTrue(b1.all_valid)
    self.assertEqual(len(b1.actual_location_list), 1)
    self.assertEqual(len(b1._backend_breakpoints), 1)

  def tearDown(self):
    self._debugger.shutdown()
