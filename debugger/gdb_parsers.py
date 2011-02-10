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
import code
import thread
import threading

import time
import re
import shlex
import subprocess

from util import *
from stack_frame import *
from location import *

def parse_loose_dict(lines):
  d = {}
  for l in lines:
    x=re.match("^(.+) += '(.+)'$",l)
    if x:
      d[x.group(1)] = x.group(2)
      continue

    x=re.match("^(\S+) (\S+)$",l)
    if x:
      d[x.group(1)] = x.group(2)
      continue
    raise Exception("Could not parse response line ["+ l +"]")
  class LooseObj:
    pass
  o = LooseObj()
  for k in d.keys():
    setattr(o,k,d[k])
  return o


def parse_location(resp):
  id = None
  filename = None
  line_num = None
  prog_ctr = None
  if hasattr(resp,"addr"):
    prog_ctr = resp.addr
  if hasattr(resp,"file"):
    filename = resp.file
    line_num = resp.line
  if hasattr(resp,"func"):
    if resp.func != "??":
      id = resp.func
  return Location(id=id,filename=filename,line_num=line_num,prog_ctr=prog_ctr)

def parse_stack_frame(frame):
  return StackFrame(frame.level,parse_location(frame))


class GdbMiInnerResponse(object):
  def __init__(self):
    pass
  def __str__(self):
    keys = [x for x in  self.__dict__ if not x.startswith("_")]
    def tostr(x):
      if type(x) == list:
        return "[%s]" % (",".join([str(y) for y in x]))
      else:
        return str(x);
    vals = ["%s=%s" % (x,tostr(getattr(self,x))) for x in keys]
    return "{%s}" % ",".join(vals)

def _parse_bare_string(v):
    m= re.match('\d+$',v)
    if m:
      value = int(v)
    else:
      m = re.match('0x[0-9a-fA-F]+$',v)
      if m:
        value  = int(v,16)
      else:
        v = v.replace("\\\"","\"")
        value = v
    return value

def _parse_single_item(rest,key_required=True):
  qi = rest.find('=')
  if qi == -1:
    if key_required:
      raise Exception("zomg no key found, rest=%s" % rest)
    key = ""
  else:
    key = rest[:qi]
    rest = rest[qi+1:]
  key = key.replace("-","_") # replace dashes with underscores
  
#  print "key=%s,rest=%s" % (key,rest)
  value = None
  if rest[0] == '"':
    rest = rest[1:]
    qi = rest.find('"')
    while rest[qi-1] == "\\": #its escaped, find another
      qi = rest.find('"',qi+1)
    v = rest[:qi]
    value = _parse_bare_string(v)
    rest = rest[qi+1:]
  elif rest[0] == '{':
    rest = rest[1:]
    value = GdbMiInnerResponse()
    while True:
      if rest[0] == '}':
        rest = rest[1:]
        break
      elif rest[0] == ',':
        rest = rest[1:]
        continue
      else:
        (subkey,subvalue,subrest) = _parse_single_item(rest)
        setattr(value,subkey,subvalue)
        rest = subrest
  elif rest[0] == '[':
    rest = rest[1:]
    value = []
    while True:
      if rest[0] == ']':
        rest = rest[1:]
        break
      elif rest[0] == ',':
        rest = rest[1:]
        continue
      elif rest[0] == '{':
        rest="anon=%s" % rest
        (subkey,subvalue,subrest) = _parse_single_item(rest,key_required=False)
        value.append(subvalue)
        rest = subrest
      else:
        (subkey,subvalue,subrest) = _parse_single_item(rest,key_required=False)
        value.append(subvalue)
        rest = subrest
  else:
    raise Exception("barf: %s", rest)
  return (key,value,rest)


class GdbMiResponse(GdbMiInnerResponse):
  def __init__(self,code,l):
    GdbMiInnerResponse.__init__(self)
    self.code = code
    if l:
      rest = l
    else:
      rest = ""
    while len(rest) > 0:
      #    print "PR rest=%s" % rest
      (key,value,rest) = _parse_single_item(rest)
      #    print "got key=%s,value=%s,rest=%s" % (key,value,rest)
      setattr(self,key,value)
      if len(rest) == 0:
        break
      elif rest[0] == ',':
        rest = rest[1:]
        continue
      else:
        raise Exception("Zomg dont know what to do! %s" % rest)
    #  print "DONE: %s\n" % result
  def expect_done(self,err_msg=None):
    self.expect('done',err_msg)
  def expect(self,code,err_msg=None):
    if self.code != code:
      if err_msg:
        raise Exception(err_msg)
      else:
        raise Exception("Response code was %s. Expected %s" % (self.code,code))

def parse_multiple_breakpoint_info(hresp,clines):
  # build de-tabler
  ncols = len(hresp.BreakpointTable.hdr)
  detab_rexp = ""
  i = 0
  for col in hresp.BreakpointTable.hdr:
    col.base = i
    i += col.width+1

  # build clines
  if not re.match("Num\s+Type\s+Disp\s+Enb\s+Address\s+What",clines[0]):
    raise DebuggerException("Unexpected response.")
  clines = clines[1:]
  ret = []
  for line in clines:
#    print "[%s]" % line[:-1]
    o = GdbMiResponse("done", "")
    def getval(c):
      if c.col_name == 'addr':
        x= line[c.base:]
      else:
        x= line[c.base:c.base+c.width]
      x = _parse_bare_string(x.strip())
#      print "%s %i %i [%s]" % (c.col_name, c.base,c.width, x)
      return x

    for col in hresp.BreakpointTable.hdr:
      if col.col_name == 'what':
        continue
      v = getval(col)
      setattr(o, col.col_name, v)
#    print str(o)
    ret.append(o)

  return ret

def parse_console_style_location(l):
  # phase 1, rip out the program counter
  prog_ctr = None
  rest = None

  re1a = "^0x([0-9a-fA-F]+) in (.+)$"
  re1b = "^(\S+ \(.+\) at \S+)$"
  m = re.match(re1a,l)
  if m:
    prog_ctr = m.group(1)
    prog_ctr = long(prog_ctr,16)
  else:
    m = re.match(re1b,l)
    if m:
      prog_ctr = None
    else:
      raise Exception("not a frame: " + l)
  # phase 2, rip out function, filename and line number
  re2 = "(\S+) (.*) at (\S+):(\d+)"
  m = re.match(re2, l)
  if m:
    function = m.group(1)+m.group(2)
    filename = m.group(3)
    line_num = int(m.group(4))
    return Location(id=function,filename=filename,line_num=line_num,prog_ctr=prog_ctr)
  elif l == "?":
    if prog_ctr == None:
      raise Exception("Unrecognized location %s and no program counter provided" % l)
    return Location(prog_ctr=prog_ctr)
  else:
    raise Exception("unrecognized location: " + l)


class GdbVersion(object):
  @staticmethod
  def get(gdb_launch_str="gdb"):
    full_str = "%s --version" % gdb_launch_str
    args = shlex.split(full_str)
    gdb = subprocess.Popen(args,stdout=subprocess.PIPE)
    stdout_lines = gdb.communicate()[0].split("\n")
    return GdbVersion.parse_from_version_lines(stdout_lines)
  @staticmethod
  def parse_from_version_lines(gdblines):
    if len(gdblines) == 0:
      log2("No response to gdb-version")
      return GdbVersion()

    m = re.match("GNU gdb \(GDB\) (\d+).(\d+)(.+)?", gdblines[0])
    if m:
      ret = GdbVersion()
      ret.major = int(m.group(1))
      ret.minor = int(m.group(2))
      if m.group(3):
        ret.build = m.group(3)
      return ret
    else:
      log0("Warning: could not determine Gdb version. Consider contributing a patch to debugger/gdb_parsers's GdbVersion code")
      return GdbVersion()

  def __init__(self):
    self.major = 0
    self.minor = 0
    self.build = ""
  def __str__(self):
    return "GNU gdb (GDB) %s.%s%s" % (self.major,self.minor,self.build)



class GdbWordMatcher(object):
  def __init__(self):
    self._entries = {}
  def add(self, key,val):
    assert type(key) == str
    assert len(key) != 0
    assert val != None
    if self._entries.has_key(key):
      raise Exception("Duplicate key")
    self._entries[key] = val

  def has_key(self, key):
    """Precise match on key."""
    return self._entries.has_key(key)

  def exact_get(self, key):
    """Precise match on key."""
    return self._entries[key]

  def fuzzy_get(self, candidate, debug=False):
    assert type(candidate) == str
    if candidate == "":
      return
    matches = []
    for key in self._entries:
      if key.startswith(candidate):
        matches.append(key)
    if len(matches) == 0:
      if debug:
        log0("-> %s had no matches ", candidate)
      return None
    elif len(matches) == 1:
      if debug:
        log0("-> 1 match: %s", matches[0])
      return self._entries[matches[0]]
    for m in matches:
      if m == candidate:
        if debug:
          log0("-> %s had exact match", candidate)
        return self._entries[m] # exact matches win
    if debug:
      log0("-> %s had multiple candidates: %s", candidate, ",".join(matches))
    return None

class GdbPhraseMatcher(object):
  def __init__(self):
    self._roots = GdbWordMatcher()
  def add(self, prefix, val):
    assert type(prefix) == str

    words = prefix.split(" ")

    i = 0
    cur_wm = self._roots
    while i < len(words) - 1:
      word = words[i]
      if not cur_wm.has_key(word):
        sub = GdbWordMatcher()
        cur_wm.add(word, sub)
      else:
        sub = cur_wm.exact_get(word)
        assert type(sub) == GdbWordMatcher

      i += 1
      if i < len(words):
        cur_wm = sub
    assert cur_wm
    cur_wm.add(words[i], val)

  def fuzzy_get(self, prefix, debug=False):
    assert type(prefix) == str

    words = prefix.split(" ")

    i = 0
    cur_wm = self._roots
    while i < len(words) - 1:
      word = words[i]
      sub = cur_wm.fuzzy_get(word, debug)
      if debug:
        log0("For %s: processing %s", prefix, word)
      if sub == None:
        if debug:
          log0("For %s: no match, returning None", prefix)
        return [None]

      if type(sub) != GdbWordMatcher:
        if debug:
          log0("For %s: match is terminal", prefix)
        ret = [sub]
        ret += words[i+1:]
        return ret
      else:
        if debug:
          log0("For %s: match is wordmatcher", prefix)


      i += 1
      if i < len(words):
        cur_wm = sub

    if debug:
      log0("For %s: search ending on last word", prefix)
    assert cur_wm
    sub = cur_wm.fuzzy_get(words[-1],debug)
    if type(sub) != GdbWordMatcher:
      if debug:
        log0("Terminal word found: %s" % sub)
      return [sub]
    else:
      if debug:
        log0("Nonterminal word found.")
      return [None]
