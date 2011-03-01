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
from util import *

class AsyncReader(object):
  def __init__(self, on_readline_cb, on_close_cb, f, mode = None):
    self._f = AsyncFile(f, mode)
    self._on_readline = on_readline_cb
    self._f.closed.add_listener(on_close_cb)
    self._f.readline(self._got_line)

  def _got_line(self,l):
    if l:
      self._on_readline(l)
    if not self._f.is_closed:
      self._f.readline(self._got_line)
