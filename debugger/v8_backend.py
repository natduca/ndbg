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

RESULT_CODE_OK = 0
RESULT_ILLEGAL_TAB_STATE = 1
RESULT_UNKNOWN_TAB = 2
RESULT_DEBUGGER_ERROR = 3
RESULT_UNKNOWN_COMMAND = 4

def _result_code_to_string(code) {
  map = {
    0 : "RESULT_CODE_OK",
    1 : "RESULT_ILLEGAL_TAB_STATE",
    2 : "RESULT_UNKNOWN_TAB",
    3 : "RESULT_DEBUGGER_ERROR",
    4 : "RESULT_UNKNOWN_COMMAND"
    }
  return map[code]
}

class V8Session(object):
  def __init__(self):
    iv = InterfaceValidator(self)
    iv.expect_method("attach(self)")
    iv.expect_method("detach(self)")
    iv.expect_method("run_command_async(self, args, cb)")
    iv.expect_get_property("closed")

class V8Backend(object):
  def __init__(self, v8session):
    self._next_seq = 0
    assert isinstance(v8session,V8session)
    self._session = v8session
    self._session.attach()
    self._session.closed.add_listener(self._on_closed)

  def _on_closed(self):
    log("session closed")
    self._session = None

  def request(self, command, args, cb):
    this_seq = self._next_seq
    self._next_seq += 1
    v8cmd = {
        "seq" : this_seq,
        "type" : "request",
        "command" : command,
        "arguments" : args
        }
    self._session.run_command_async(v8cmd, cb)

  def _on_close(self):
    print "v8: closed"
    MessageLoop.quit()


if __name__ == "__main__":
  set_loglevel(2)
  def init(*args):
    try:
      be = ChromeV8Backend(*args)
    except:
      import traceback; traceback.print_exc();
      MessageLoop.quit()


  # for chrome, launch with chrome --remote-shell-port
  import sys
  MessageLoop.add_message(init, "localhost", int(sys.argv[1]), int(sys.argv[2]))
#  MessageLoop.add_message(init, "localhost", 5858)
  MessageLoop.run_no_gtk(lambda: False)
  print "main done"
