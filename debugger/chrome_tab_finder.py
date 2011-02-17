from util import *
import json

class ChromeTabFinder(object):
  def __init__(self, host, port):
    self._next_seq = 0
    self._timer = Timer(250)
    self._timer.tick.add_listener(self._tick)

    self._host = host
    self._port = port

    self._session = None
    self._get_tab_list_pending = False

    self._tick()

  def _tick(self):
    if not self._session:
      self._try_connect()
    elif not self._get_tab_list_pending:
      self._begin_get_tab_list()

  def _try_connect(self):
    try:
      s = socket.socket()
      s.connect((self._host, self._port))
      ChromeTabFinder.do_handshake(s)
      self._session = AsyncHTTPSession(s)
    except:
      self._session = None
      log2("Could not connect to chrome on %s:%s", self._host, self._port)

    if self._session:
      self._session.closed.add_listener(self._on_session_closed)


  def _on_session_closed(self):
    assert self._session
    self._session = None

  @property
  def chrome_found(self):
    return self._session != None

  @staticmethod
  def do_handshake(s):
    i = "ChromeDevToolsHandshake"
    handshake = "ChromeDevToolsHandshake\r\n"
    remaining = handshake
    while len(remaining):
      sent = s.send(handshake)
      remaining = remaining[sent:]
    handshake_ack = s.recv(len(handshake))
    if handshake_ack != handshake:
      raise Exception('handshake failed')
    else:
      log1("handshake succeeded")

  def _begin_get_tab_list(self):
    self._get_tab_list_pending = True
    self._session.request({"Tool":"DevToolsService"}, json.dumps({"command" : "list_tabs"}), self._finish_get_tab_list)

  def _finish_get_tab_list(self, headers, content):
    self._get_tab_list_pending = False
    resp = json.loads(content)
    print "content=%s"%content
#    print resp

  def _on_close(self):
    log1("chrome connection was closed. chrome processes won't be available.")
    self._session = None


if __name__ == "__main__":
  set_loglevel(2)

  def init(*args):
    try:
      be = ChromeTabFinder(*args)
    except:
      import traceback; traceback.print_exc();
      MessageLoop.quit()


  # for chrome, launch with chrome --remote-shell-port
  import sys
  MessageLoop.add_message(init, "localhost", int(sys.argv[1]))
#  MessageLoop.add_message(init, "localhost", 5858)
  MessageLoop.run_no_gtk(lambda: False)
  print "main done"
