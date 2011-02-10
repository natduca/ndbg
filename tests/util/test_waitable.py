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
from util import *

class WaitableTestCase(unittest.TestCase):
  def test_poll_waitable(self):
    trace = []
    res = []
    w0 = PollUntilTrueWaitable(lambda: len(res) == 1)
    w0.when_done(lambda v: trace.append("w0 done"))
    MessageLoop.add_message(lambda: res.append(True))
    w0.wait()
    self.assertEqual(trace,["w0 done"])

  def test_poll_waitable_that_raises(self):
    def fail():
      raise Exception("boom")
    w0 = PollUntilTrueWaitable(fail)
    w0.when_done(lambda v: self.assertFalse()) # ensure we never call the callbacks
    self.assertRaises(Exception,lambda: w0.wait())
    self.assertTrue(w0.is_done)
    self.assertRaises(Exception,w0.get_return_value)

  def test_callback_driven_waitable(self):
    w = CallbackDrivenWaitable()
    MessageLoop.add_message(lambda: w.set_done(31415))
    res = []
    w.when_done(lambda v: res.append(v))
    w.wait()
    assert(res[0] == 31415)


  def test_callback_driven_waitable(self):
    w = CallbackDrivenWaitable()
    MessageLoop.add_message(lambda: w.set_done(31415))
    res = BoxedObject()
    w.when_done(lambda v: res.set(v))
    ret = w.wait()
    self.assertEqual(ret, 31415)
    self.assertTrue(w.is_done)
    self.assertEqual(res.get(), 31415)


  def test_callback_driven_waitable_that_aborts(self):
    w = CallbackDrivenWaitable()
    w.set_check_for_abort_cb(lambda: True)
    w.when_done(lambda v: self.assertTrue(False)) # should never run when_done
    self.assertRaises(Exception, lambda: w.wait())
    self.assertTrue(w.is_done)
    self.assertRaises(Exception, lambda: w.get_return_value())

  def test_counter_waitable_inc(self):
    when_done_res = BoxedObject(None)
    w = CounterWaitable(0,1)
    MessageLoop.add_message(lambda: w.set_return_value(1234))
    MessageLoop.add_message(lambda: w.inc())
    w.when_done(lambda v: when_done_res.set(v))
    ret = w.wait()
    self.assertEqual(ret, 1234)
    self.assertEqual(w.get_return_value(), 1234)
    self.assertEqual(when_done_res.get(), 1234)

  def test_counter_waitable_dec(self):
    when_done_res = BoxedObject(None)
    w = CounterWaitable(1,0)
    MessageLoop.add_message(lambda: w.set_return_value(1234))
    MessageLoop.add_message(lambda: w.dec())
    w.when_done(lambda v: when_done_res.set(v))
    ret = w.wait()
    self.assertEqual(ret, 1234)
    self.assertEqual(w.get_return_value(), 1234)
    self.assertEqual(when_done_res.get(), 1234)


  def test_counter_waitable_inc_that_aborts(self):
    w = CounterWaitable(0,1)
    MessageLoop.add_message(lambda: w.abort())
    w.when_done(lambda v: self.assertTrue(False)) # should never hit
    self.assertRaises(Exception, lambda: w.wait())
    self.assertRaises(Exception, lambda: w.get_return_value())
    self.assertTrue(w.is_done)

