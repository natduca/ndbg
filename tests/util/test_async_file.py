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
from tempfile import *

from util import *

import socket
import subprocess

class TestAsyncFile(unittest.TestCase):
  def test_file_ending_wo_nl(self):
    self.do_test([
      "Line1\n",
      "Line2\n",
      "\n",
      "Line4\n",
      "Last"])

  def test_file_ending_with_nl(self):
    self.do_test([
      "Line1\n",
      "Line2\n",
      "\n",
      "Line4\n",
      "Last\n"])

  def test_nearly_empty_file(self):
    self.do_test([
      "\n"])

  def do_test(self, in_lines):
    tf = NamedTemporaryFile(delete=False)
    for l in in_lines:
      tf.write("%s" % l)
    tf.close()

    f = AsyncFile(open(tf.name,'r'))

    rcvd = []
    def on_line(l,expected):
      self.assertEquals(l,expected)
      rcvd.append(l)
    did_get_ltce = BoxedObject(False)
    def on_line_that_cant_exist(l):
      self.assertEquals(l,None)
      did_get_ltce.set(True)
      assert(f.is_closed)

    # read each of the lines
    for l in in_lines:
      f.readline(on_line, l)
    f.readline(on_line_that_cant_exist) 

    MessageLoop.run_until(lambda: f.is_closed and did_get_ltce.get())

    self.assertEquals(len(in_lines), len(rcvd))

    os.unlink(tf.name)

  def test_empty_file(self):
    self.do_test([])

