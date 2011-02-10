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
from util.message_loop import *

class TestMessageLoop_NoMessages(unittest.TestCase):
  def test_add_message(self):
    res = []
    MessageLoop.add_message(lambda: res.append(True))
    MessageLoop.run_while(lambda: len(res) == 0)

  def test_add_delayed_mssage(self):
    res = []
    MessageLoop.add_delayed_message(lambda: res.append(True), 200)
    MessageLoop.run_while(lambda: len(res) == 0)

  def test_add_delayed_recurring_message(self):
    res = []
    i = [3]
    def tick():
      i[0] -= 1
      res.append(True)
      return i[0] > 0
    MessageLoop.add_delayed_message(tick, 200)
    MessageLoop.run_until(lambda: len(res) == 2)
