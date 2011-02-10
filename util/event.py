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
import pygtk
pygtk.require('2.0')
import gtk
import glib
import traceback
import types
import pickle

from message_loop import MessageLoop

class Event(object):
  def __init__(self):
    self._listeners = []
    self._posted = False # used by post_if_not_already_posted

  def add_listener(self,cb):
    self._listeners.append(cb)

  def remove_listener(self,cb):
    self._listeners.remove(cb)

  def __getstate__(self):
    return {}
  def __setstate__(self,d):
    self._listeners = []

  def fire(self,*args):
    for cb in self._listeners:
      try:
        cb(*args)
      except Exception,e:
#        cur_stack = traceback.extract_stack()
        print "Error on callback:"
        traceback.print_stack()
        traceback.print_exc()
        print "\n\n"

  def post(self,*args):
    """This function fires the listeners via the message loop, meaning notification won't happen until the toplevel message pump."""
    def do_fire():
      self.fire(*args)
    MessageLoop.add_message(do_fire)

  def post_if_not_already_posted(self,*args):
    """This function fires the listeners via the message loop.
    If you call this function multiple times before the message loop runs,
    only the first post_if_not_already_posted will be run"""
    if self._posted:
      return
    self._posted = True
    def do_fire():
      self._posted = False
      self.fire(*args)
    MessageLoop.add_message(do_fire)

class AlreadyFiredEvent(object): # drop-in-replacement for Event that you can use in case someone adds a listener after the fact
  def __init__(self,*fire_args):
    self._fire_args = fire_args

  def add_listener(self, cb):
    self.post(cb,*self._fire_args) # use post so its not in the same call stack

  def remove_listener(self, cb):
    pass
