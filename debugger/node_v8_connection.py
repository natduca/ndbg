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

class NodeV8Connection(V8Connection):
  def __init__(self, host, port):
    V8Connection.__init__(self)
    self._host = host
    self._port = port
    self._closed = Event()
    self._session = None

  def attach(self):
    s = socket.socket()
    s.connect((self._host, self._port))
    self._session = AsyncHTTPSession(s)
    self._session.closed.add_listener(self._on_close)

    got_handshake = BoxedObject(False)
    def on_handshake(headers, content):
      assert headers["Type"] == "connect"
      assert headers["Protocol-Version"] == "1"
      got_handshake.set(True)
    self._session.request(None,None,on_handshake)
    log1("Waiting for V8 handshake")
    MessageLoop.run_until(lambda: got_handshake.get())
    log1("Attached to V8.")

  def run_command_async(self, args, cb = None):
    def on_done(headers,content):
      print "command done: [%s]" % (content)
      obj = json.loads(content)
      if cb:
        cb(obj)
    self._session.request({}, json.dumps(args), on_done)

  def _on_close(self):
    log1("node-v8: closed")
    self._closed.fire()

  @property
  def closed(self):
    return self._closed

  def detach(self):
    self._session.close()


if __name__ == "__main__":
  set_loglevel(2)
  def init(*args):
    try:
      conn = NodeV8Connection(*args)
      import v8_backend
      v8_backend.V8Backend(conn)
    except:
      import traceback; traceback.print_exc();
      MessageLoop.quit()

  # for chrome, launch with chrome --remote-shell-port
  import sys
  MessageLoop.add_message(init, sys.argv[1], int(sys.argv[2]))
  MessageLoop.run_no_gtk(lambda: False)
  print "main done"
