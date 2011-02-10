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
_loglevel = 0
_prefix_mode = True

import sys
import traceback
import os

def set_loglevel(l):
  global _loglevel
  if type(l) != int:
    raise Exception("Expected int")
  _loglevel = l
  get_loglevel()

def get_loglevel():
  return _loglevel

def set_prefixes_enabled(en):
  global _prefix_mode
  assert type(en) == bool
  _prefix_mode = en

def get_caller_module(offset=0):
  tb = traceback.extract_stack(limit=2+offset)
  filename = tb[-offset-1][0]
  modwithext = os.path.basename(filename)
  mod = os.path.splitext(modwithext)[0]
  if mod == "__init__":
    modname = os.path.basename(os.path.dirname(filename))
    return modname
  else:
    return mod

def log0_raw(fmt, *args):
  if _loglevel >= 0:
    res = fmt % args
    sys.stdout.write(res)
    sys.stdout.write("\n")
    sys.stdout.flush()

def log0(fmt, *args):
  if _loglevel >= 0:
    if _prefix_mode:
      sys.stdout.write("%20s" % get_caller_module(2))
      sys.stdout.write(": ")
    res = fmt % args
    sys.stdout.write(res)
    sys.stdout.write("\n")
    sys.stdout.flush()

def log1(fmt, *args):
  if _loglevel >= 1:
    if _prefix_mode:
      sys.stdout.write("%20s" % get_caller_module(2))
      sys.stdout.write(": ")
    res = fmt % args
    sys.stdout.write(res)
    sys.stdout.write("\n")
    sys.stdout.flush()

def log2(fmt, *args):
  if _loglevel >= 2:
    if _prefix_mode:
      sys.stdout.write("%20s" % get_caller_module(2))
      sys.stdout.write(": ")
    res = fmt % args
    sys.stdout.write(res)
    sys.stdout.write("\n")
    sys.stdout.flush()

def log3(fmt, *args):
  if _loglevel >= 3:
    if _prefix_mode:
      sys.stdout.write("%20s" % get_caller_module(2))
      sys.stdout.write(": ")
    res = fmt % args
    sys.stdout.write(res)
    sys.stdout.write("\n")
    sys.stdout.flush()

def log4(fmt, *args):
  if _loglevel >= 4:
    if _prefix_mode:
      sys.stdout.write("%20s" % get_caller_module(2))
      sys.stdout.write(": ")
    res = fmt % args
    sys.stdout.write(res)
    sys.stdout.write("\n")
    sys.stdout.flush()

if __name__ == "__main__":
  print get_caller_module()
