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

import os
from util import *
from .ctags_parser import *

class TaggedFile(object):
  def __init__(self, filename):
    self.filename = filename
    self._ctags = None

  def update(self):
    if os.path.exists(self.filename) == False:
      log0("%s has gone missing.", self.filename)
      return

    self._ctags = parse_ctags_from_source(self.filename)

  def get_tag(self, id):
    assert(self._ctags)
    return self._ctags[id]

  def get_tags(self):
    if self._ctags == None:
      return None
    else:
      res = []
      for i in range(len(self._ctags)):
        tag = self._ctags[i]
        res.append((i, tag.name, tag.type))
      return res
