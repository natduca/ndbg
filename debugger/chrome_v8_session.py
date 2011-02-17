import json
from util import *
from v8_backend import V8Session

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

class ChromeV8Session(V8Session):
  def __init__(self, host, port, tab_id):
    V8Session.__init__(self)
    self._next_seq = 0
    self._tab_id = tab_id

    s = socket.socket()
    s.connect((host, port))
    ChromeTabFinder.do_handshake(s)
    self._session = AsyncHTTPSession(s)
    self._attach_to_v8()

  def attach(self):
    def step1():
      self._session.request({"Tool":"V8Debugger",
                             "Destination" :
                               },
                            json.dumps({"command" : "attach"}), step2)

    step2_complete = BoxedObject(None)
    def step2(self,headers,content):
      log("attach done")
      assert headers["result"] == RESULT_CODE_OK
      step2_complete.set(True)

    step1()
    MessageLoop.run_until(lambda: step2_complete.get())

  def _on_close(self):
    print "v8: closed"
    MessageLoop.quit()


if __name__ == "__main__":
  set_loglevel(2)
  def init(*args):
    try:
      session = ChromeV8Session(*args)
      import v8_backend
      v8_backend.V8Backend(session)
    except:
      import traceback; traceback.print_exc();
      MessageLoop.quit()


  # for chrome, launch with chrome --remote-shell-port
  import sys
  MessageLoop.add_message(init, "localhost", int(sys.argv[1]), int(sys.argv[2]))
#  MessageLoop.add_message(init, "localhost", 5858)
  MessageLoop.run_no_gtk(lambda: False)
  print "main done"
