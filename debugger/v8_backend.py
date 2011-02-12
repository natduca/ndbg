from util import *

class V8Backend(object):
  def v8_request(self, command, args):
    this_seq = self._next_seq
    self._next_seq += 1
    self.general_request({
        "seq" : this_seq,
        "type" : "request",
        "command" : command,
        "arguments" : args
        })
    text = pson.dumps(args)
    self.general_request("V8Debugger", cmd)

  def general_request(self, tool, args, cb = None):
    if not args:
      args = {}
    def pass_cb(h,resp):
      print "%s\n%s\n\n" % (h, resp)
      if cb:
        cb(resp)
    self._session.request({"Tool":tool}, pson.dumps(args), pass_cb)

  def __init__(self, host, port):
    self._next_seq = 0

    s = socket.socket()
    s.connect((host, port))
    self._do_handshake(s)

    self._session = AsyncHTTPSession(s)
    self.general_request("DevToolsService", {"command": "ping"})
    self.general_request("DevToolsService", {"command": "tabs"})

  def _do_handshake(self,s):
    i = "ChromeDevToolsHandshake"
    print len(i)
    handshake = "ChromeDevToolsHandshake\r\n"
    remaining = handshake
    while len(remaining):
      sent = s.send(handshake)
      remaining = remaining[sent:]
    handshake_ack = s.recv(len(handshake))
    if handshake_ack != handshake:
      raise Exception('handshake failed')

  def _do_init(self, host, port):
    pass

  def _on_close(self):
    print "v8: closed"
    MessageLoop.quit()


if __name__ == "__main__":
  set_loglevel(2)
  def init(*args):
    try:
      be = V8Backend(*args)
    except:
      import traceback; traceback.print_exc();
      MessageLoop.quit()


  # for chrome, launch with chrome --remote-shell-port
  import sys
  MessageLoop.add_message(init, "localhost", int(sys.argv[1]))
#  MessageLoop.add_message(init, "localhost", 5858)
  MessageLoop.run_no_gtk(lambda: False)
  print "main done"
