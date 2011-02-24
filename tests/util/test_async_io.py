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

class TestAsyncIO(unittest.TestCase):
  def test_socket(self):
    s = socket.socket()
    s.connect(('google.com', 80))
    x = AsyncIO(s)
    data_recvd = BoxedObject(False)
    x_closed = BoxedObject(False)
    def do_request():
      x.write("GET / HTTP/1.0\r\n\r\n")
    def on_recv(data):
      data_recvd.set(True)
    def on_close():
      x_closed.set(True)

    x.read.add_listener(on_recv)
    x.closed.add_listener(on_close)
    x.open()
    do_request()
    MessageLoop.run_until(lambda: x_closed.get())
    self.assertTrue(data_recvd.get())

  def test_file(self):
    f = NamedTemporaryFile(delete=False)
    f.write("HelloWorld\n")
    f.close()

    x = AsyncIO(open(f.name,'r'))
    rcvd_data = BoxedObject("")
    did_close = BoxedObject(False)
    def on_recv(b):
      rcvd_data.set(rcvd_data.get() + b)
    def on_close():
      did_close.set(True)
    x.read.add_listener(on_recv)
    x.closed.add_listener(on_close)
    x.open()
    MessageLoop.run_until(lambda: x.is_closed)
    self.assertTrue(did_close.get())
    self.assertEquals(rcvd_data.get(), "HelloWorld\n")

    os.unlink(f.name)
