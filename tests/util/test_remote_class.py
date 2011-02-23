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
import time

from util import *

class A():
  def __init__(self):
    self.val = 7

  def set(self, v):
    self.val = v

  def get(self):
    return self.val

  def exception(self):
    raise Exception("This is an expected exception")

  def sleep_then_get(self):
    time.sleep(0.5)
    return self.vall

class TestRemoteClient(unittest.TestCase):
  def test_basic(self):
    a = RemoteClient(A)
    a.shutdown()

  def test_call_async(self):
    a = RemoteClient(A)
    a.call_async('set', 3)
    a.shutdown()

  def test_call_async_waitable(self):
    a = RemoteClient(A)
    w = a.call_async_waitable('get')
    v = w.wait()
    self.assertEqual(v, 7)
    a.shutdown()

  def test_set_then_get(self):
    a = RemoteClient(A)
    w = a.call_async('set', 314)
    w = a.call_async_waitable('get')
    v = w.wait()
    self.assertEqual(v, 314)
    a.shutdown()

  def test_call_async_exception_waitable(self):
    a = RemoteClient(A)
    w = a.call_async_waitable('exception')
    self.assertRaises(Exception, lambda: w.wait())
    a.shutdown()

class TestRemoteClass(unittest.TestCase):
  def test_basic(self):
    a = RemoteClass(A)
    a.call_async.set(3)
    self.assertEqual(a.call.get(), 3)
    a.call_async.set(3)
    a.call_async.set(4)
    a.call_async.set(5)
    v = a.call_async_waitable.get().wait()
    self.assertEqual(v, 5)
    self.assertRaises(Exception, lambda: a.call.exception())
    self.assertRaises(Exception, lambda: a.call_async_waitable.exception().wait())
    a.shutdown()

  def test_leave_running(self):
    a = RemoteClass(A)
    a.call_async.set(3)

