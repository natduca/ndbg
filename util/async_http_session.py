from __future__ import absolute_import
import socket
from collections import *
from cStringIO import StringIO

from util import *



class AsyncHTTPSession(object):
  def __init__(self, s):
    self._closed = Event()
    self._io = AsyncIO()

    self._io.read.add_listener(self._on_read)
    self._io.close.add_listener(self._on_close)
    self._io.open(s)

    self._found_header = False
    self._cur_header = ""
    self._cur_body = ""
    self._cur_headers = None

    self._pending_request_cbs = deque()

  def request(self, headers, text, cb):
    header = "\r\n".join(["%s:%s" % (x, headers[x]) for x in headers])
    header += "\r\nContent-Length:%i\r\n" % (len(text))
    header += "\r\n"
#    print "send[%s]" % (header + text)
    self._pending_request_cbs.append(cb)
    self._io.write(header + text)

  def _on_read(self, data):
    if not self._found_header:
      self._cur_header += data
      idx = self._cur_header.find("\r\n\r\n")
      if idx:
#        print "header found"
        self._found_header = True
        body = self._cur_header[idx+4:]
        headers = self._cur_header[:idx]
        self._cur_header = ''
        lines = headers.split("\r\n")
        if lines[-1] == '':
          del lines[-1]
        arys = [[y.strip() for y in x.split(':')] for x in lines]
        d = dict(arys)
        self._cur_headers = d
        if not d.has_key("Content-Length"):
          log1("Malformed header")
          self._found_header = False
          self._cur_headers = ""
          if self._io:
            self._io.close()
          return
        self._content_length_goal  = int(d["Content-Length"])
        self._on_read(body)
    else:
      self._cur_body += data
      if len(self._cur_body) >= self._content_length_goal:
        remainder = self._cur_body[self._content_length_goal:]
        body = self._cur_body[:self._content_length_goal]
        self._cur_body = ''

        d = self._cur_headers
        self._cur_headers = None

        self._found_header = False

        # body recvd
        self._on_response(d, body)

        # more?
        if len(remainder):
          self._on_read(remainder)

  def _on_response(self, headers, body):
    cb = self._pending_request_cbs.popleft()
    cb(headers, body)

  def _on_close(self):
    log1("closed");
    self._io = None
    self._closed.fire()

  @property
  def closed(self):
    return self._closed
