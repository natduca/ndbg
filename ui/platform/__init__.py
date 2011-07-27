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

def is_gtk():
  try:
    import gtk
    return True
  except:
    return False

def is_wx():
  try:
    import wx
    return True
  except:
    return False

if is_gtk():
  from .gtk import *
elif is_wx():
  from .wx import *
else:
  raise Exception("Could not find a GUI toolkit")

