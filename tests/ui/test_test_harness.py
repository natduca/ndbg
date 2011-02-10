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

import time
from debugger import *
from util import MessageLoop

class TestUITestCaseBase(UITestCaseBase):
  def test_run_returns_value(self):
    ret = self.run_on_ui(lambda mc: 31415+1)
    self.assertEqual(ret, 31415+1)

  def test_run_callback_that_never_returns(self):
    def wait_forever(mc):
      MessageLoop.run_until(lambda: False)
      assert("Should never reach here.") # because MessageLoop will raise QuitException
    self.assertRaises(UITimeoutException, lambda: self.run_on_ui(wait_forever,timeout=1))

  def test_callback_that_causes_subsequent_exception(self):
    def enqueue_exception(mc):
      def raise_exception():
        raise Exception("This is an intentional exception")
      MessageLoop.add_message(raise_exception)
    self.run_on_ui(enqueue_exception)
    def do_nothing(mc):
      pass
    self.assertRaises(UIThreadException, lambda: self.run_on_ui(do_nothing))

  def test_exception_on_malformed_cb(self):
    def malformed_cb(): # should have mc as a signature
      pass
    self.assertRaises(UIThreadException, lambda: self.run_on_ui(malformed_cb))

  def test_assertion_ok_on_uithread(self):
    self.run_on_ui(lambda mc: self.assertTrue(True))

  def test_assertion_fail_on_uithread(self):
    def do_assert_fail():
      self.run_on_ui(lambda mc: self.assertTrue(False))
    self.assertRaises(UIThreadException, do_assert_fail)

  def test_run_returns_exception(self):
    def raise_ex_on_ui(mc):
      raise Exception("Foo")
    self.assertRaises(Exception, lambda:  self.run_on_ui(raise_ex_on_ui))

class TestUITestCaseSingle(UITestCaseSingle):
  def setUp(self):
    UITestCaseSingle.setUp(self, "tests/apps/test1")

  def test_launched(self):
    self.run_on_ui(lambda mc: self.assertEqual(len(mc.debugger.processes), 1))
    self.assertTrue(self.run_on_ui(lambda mc: mc.debugger.active_thread) != None)
