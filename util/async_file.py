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
from __future__ import absolute_import
import socket
from collections import *
from cStringIO import StringIO

from util import *

class AsyncFile(object):
  def __init__(self, f, mode = None):
    if isinstance(f, str):
      if mode != None:
        f = file(f, mode)
      else:
        raise Exception("invalid mode")
    self._io = AsyncIO(f)
    self._io.read.add_listener(self._on_read)
    self._io.closed.add_listener(self._on_close)

    self._cur_buffer = ""

    self._pending_cbs = deque()
    self._fake_on_read_pending = False

    self._closed = Event()
    self._closing = False
    self._io.open() # keep this last, it will trigger callbacks...


  def write(self, data, cb = None, *args):
    if not self._io:
      raise Exception("Closed")
    if len(args):
      self._io.write(data, lambda: cb(*args))
    else:
      self._io.write(data, cb)

  def readline(self, cb, *args):
    if not self._io:
      MessageLoop.add_message(cb, None, *args)
      return

    if len(args):
      self._pending_cbs.append(lambda l: cb(l, *args))
    else:
      self._pending_cbs.append(cb)

    if not self._fake_on_read_pending:
      self._fake_on_read_pending = True
      def fake_on_read():
        self._on_read(None)
        self._fake_on_read_pending = False # set this here in case the on-read caues a readline
      MessageLoop.add_message(fake_on_read)
    else:
      pass
  def _on_read(self, data):
    if data:
      self._cur_buffer += data
    while len(self._pending_cbs):
      idx = self._cur_buffer.find("\n")
      if idx == -1:
        break
      idx += 1
      line = self._cur_buffer[:idx]
      self._cur_buffer = self._cur_buffer[idx:]

      cb = self._pending_cbs.popleft()
      cb(line)

    if self._closing:
      if len(self._cur_buffer):
        assert self._cur_buffer.find("\n") == -1
        if len(self._pending_cbs):
          cb = self._pending_cbs.popleft()
          cb(self._cur_buffer)
          self._cur_buffer = ''
      self._io = None
      self._closing = False
      self._closed.fire() # truly closed
      while len(self._pending_cbs):
        cb = self._pending_cbs.popleft()
        cb(None)
    else:
      pass

  def _on_close(self):
    self._closing = True
    self._on_read(None)

  @property
  def closed():
    return self._closed

  @property
  def is_closed(self):
    return self._io == None

