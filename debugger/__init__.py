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
STATUS_RUNNING = "Running"
STATUS_BREAK = "Break"

class DebuggerException(Exception):
  def __init__(self,msg):
    Exception.__init__(self)
    self.message = msg
  def __str__(self):
    return "DebuggerException(%s)" % self.message

from dlaunchable_process import *
from dpassive_process import *

from debugger import *
from location import *
from stack_frame import *
from breakpoint import *
from file_manager import *
from dprocess import *
from dthread import *
from dpty import *

def __init__():
  print "Debugger module initialized"
  print type(StackFrame)
