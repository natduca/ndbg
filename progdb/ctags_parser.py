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

import subprocess
import os
import re
from util.logging import *
import tempfile

CTAG_TYPE_CLASS = "c"
CTAG_TYPE_DEFINE = "d"
CTAG_TYPE_FUNCTION = "f"
CTAG_TYPE_NAMESPACE = "n"
CTAG_TYPE_MEMBER = "m"
CTAG_TYPE_TYPEDEF = "t"
CTAG_TYPE_UNKNWON = "?"
CTAG_TYPE_VARIABLE = "v"
CTAG_TYPES = (
  CTAG_TYPE_CLASS,
  CTAG_TYPE_DEFINE,
  CTAG_TYPE_FUNCTION,
  CTAG_TYPE_NAMESPACE,
  CTAG_TYPE_MEMBER,
  CTAG_TYPE_TYPEDEF,
  CTAG_TYPE_UNKNWON,
  CTAG_TYPE_VARIABLE
  )

class CTag(object):
  def __init__(self,raw_line):
    recs = raw_line.split("\t")
    assert len(recs) >= 3
    self.name = recs[0]
    m1 = re.match("\/\^(.+)\$\/\;\"", recs[2])
    m2 = re.match("\/\^(.+)\$\/", recs[2])
    if (not m1) and (not m2):
      m = re.match("(\d+)\;\"", recs[2])      
      if not m:
        m = re.match("(\d+)", recs[2])
        if not m:
          raise Exception("Malformed ctags search expression: '%s'" % recs[2])
        else:
          self._line_number = int(m.group(1))
          self._line_missing = False
          self._ex_cmd = None
      else:
        self._line_number = int(m.group(1))
        self._line_missing = False
        self._ex_cmd = None
    elif m1:
      self._ex_cmd = re.escape(m1.group(1))
      self._line_number = -1 # if -1, might exist or might need determining
      self._line_missing = False
    elif m2:
      self._ex_cmd = re.escape(m2.group(1))
      self._line_number = -1 # if -1, might exist or might need determining
      self._line_missing = False
    else:
      assert False
    if len(recs) >= 4:
      if recs[3] in CTAG_TYPES:
        self.type = recs[3]
      else:
        log0("Warning: unfamiliar type found: %s for line %s", recs[3], raw_line)
        self.type = CTAG_TYPE_UNKNWON
    else:
      self.type = CTAG_TYPE_UNKNWON

  @property
  def line_missing(self):
    return self._line_missing

  @property
  def line_number(self):
    return self._line_number

  @property
  def needs_determining(self):
    return self._ex_cmd != None and self._line_number == -1 and self._line_missing == False

  def determine_line_number(self, filename):
    if self._ex_cmd == None:
      raise Exception("Cannot determine line number unless we have a ex_cmd")
    self._line_missing = False
    self._line_number = -1
    try:
      f = open(filename,'r')
    except IOError:
      return
    line_no = 0
    for l in f.readlines():
      line_no += 1
      if re.match(self._ex_cmd, l):
        self._line_number = line_no
        self._line_missing = False
        break
    f.close()

def parse_ctags_from_source(filename):
  tagfile = tempfile.NamedTemporaryFile(delete=False)
  tagfile.close()

  args = ["ctags", "--declarations", "-o", tagfile.name, filename]
  proc = subprocess.Popen(args, stdout=None, stderr=None, stdin=None)
  proc.wait()

  lines = open(tagfile.name, 'r').readlines()
  os.unlink(tagfile.name)
  res = parse_ctags_from_ctags_output(lines)

  if proc.poll() == None:
    proc.kill()
  return res

def parse_ctags_from_ctags_output(lines):
  res = []
  for l in  lines:
    ct = CTag(l.strip())
    res.append(ct)
  return res
