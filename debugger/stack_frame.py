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
import re
from . import *

class StackFrame:
  def __init__(self,frame_number,location):
    if type(frame_number) != int:
      raise Exception("Invalid type")
    self.frame_number = frame_number
    self.location = location
  def __str__(self):
    return "#%s %s" % (self.frame_number, str(self.location))

