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
import json
from util import *
from v8_connection import *

class V8Backend(object):
  def __init__(self, v8connection):
    self._next_seq = 0
    assert isinstance(v8connection,V8Connection)
    self._connection = v8connection
    self._connection.closed.add_listener(self._on_closed)
    self._connection.attach()

    def drop(*args):
      pass
    self.run_v8_command("evaluate", {"expression": "1+1",
                                     "frame" : 0,
                                     "global" : True,
                                     "disable_break" : True}, drop)
                              

  def _on_closed(self):
    log1("connection closed")
    self._connection = None

  def run_v8_command(self, command, args, cb):
    this_seq = self._next_seq
    self._next_seq += 1
    v8cmd = {
        "seq" : this_seq,
        "type" : "request",
        "command" : command,
        "arguments" : args
        }
    self._connection.run_command_async(v8cmd, cb)

  def _on_close(self):
    print "v8: closed"
    MessageLoop.quit()
