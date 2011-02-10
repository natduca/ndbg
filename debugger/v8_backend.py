import socket
from util import *
from cStringIO import StringIO

class AsyncV8IO(object):
  def __init__(self, s):
    self._next_seq = 0
    self._io = AsyncIO()

    self._io.read.add_listener(self._on_read)
    self._io.close.add_listener(self._on_close)
    self._io.open(s)

    self._found_header = False
    self._cur_header = ""
    self._cur_body = ""

  def v8_request(self, command, args):
    this_seq = self._next_seq
    self._next_seq += 1
    self.general_request({
        "seq" : this_seq,
        "type" : "request",
        "command" : command,
        "arguments" : args
        })

  def general_request(self, args):
    text = pson.dumps(args)
    header = ""
    header += "Tool:DevToolsService\r\n"
    header += "Content-Length:%i\r\n" % (len(text))
    header += "\r\n"
    print "send[%s]" % (header + text)
    self._io.write(header + text)

  def _on_read(self, data):
    print "read %s" % data
    if not self._found_header:
      self._cur_header += data
      idx = self._cur_header.find("\r\n\r\n")
      if idx:
        print "header found"
        self._found_header = True
        body = self._cur_header[idx+4:]
        self._cur_header = self._cur_header[:idx]
        lines = self._cur_header.split("\r\n")
        if lines[-1] == '':
          del lines[-1]
        arys = [[y.strip() for y in x.split(':')] for x in lines]
        d = dict([x[0] for x in arys], [x[1] for x in arys])
        print d
        if not d.has_key("Content-Length"):
          self._io.close()
          raise Exception("Malformed header")
        self._content_length_goal  = int(d["Content-Length"])
        self._on_read(body)
    else:
      self._cur_body += data
      if len(self._cur_body) >= self._content_length_goal:
        remainder = self._cur_body[self._content_length_goal:]
        self._cur_body = self._cur_body[:self._content_length_goal]
        # body recvd
        print "response: [%s]" % self._cur_body
        if len(remainder):
          self._on_read(remainder)

  def _on_close(self):
    self._io = None

class V8Backend(object):
  def __init__(self, host, port):
    s = socket.socket()
    s.connect((host, port))
    self._do_handshake(s)
    self._io = AsyncV8IO(s)
    self._io.general_request({"command" : "ping"})
    self._io.general_request({"command" : "ping"})

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
