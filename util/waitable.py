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
from util import MessageLoop
from util.base import *
import traceback

class Waitable(object):
  def __init__(self):
    pass

  # helpers
  @property
  def return_value(self):
    return self.get_return_value()

  # abstracts
  @property
  def is_done(self):
    raise Exception("Not implemented")

  def wait(self):
    raise Exception("Not implemented")

  def get_return_value(self):
    raise Exception("Not implemented")

  def when_done(self, cb, *args):
    raise Exception("Not implemented")



class PollUntilTrueWaitable(Waitable):
  def __init__(self,poll_cb):
    self._done = False
    self._poll_cb = poll_cb
    self._when_done_cbs = []
    self._ret_val = None
    self._exception = None

  def wait(self):
    if not self._done:
      MessageLoop.run_until(lambda: argn(self._perform_poll(), self._done))
    if self._exception:
      raise Exception(self._exception)
    else:
      return self._ret_val

  def set_return_value(self, v):
    self._ret_val = value

  def when_done(self, cb, *args):
    """Runs cb whne this waitable is complete. The signature of cb is
    cb(ret_val)"""
    if cb == None:
      raise Exception("Wtf")
    if self._done:
      try:
        cb(self._ret_val, *args)
      except Exception,e:
        print "Exception in when_done callback:"
        traceback.print_stack()
        traceback.print_exc()


    self._when_done_cbs.append(lambda v: cb(v,*args))
    if len(self._when_done_cbs) == 1:
      MessageLoop.add_delayed_message(self._perform_poll,10)

  @property
  def is_done(self):
    if self._done:
      return True
    self._perform_poll()
    return self._done

  def _perform_poll(self):
#    print "Needs re polling"
    try:
      if self._poll_cb() == False:
#        print "Needs re polling"
        return True # re-poll again
    except Exception, exc:
#      print "Exception raised during polling"
      self._done = True
      self._exception = "".join(traceback.format_exc())
      return # don't run callbacks... TODO(nduca) add when_fail callbacks
#    print "Poll returned true"

    cbs = list(self._when_done_cbs)
    self._done = True
    del self._when_done_cbs[:]
    for cb in cbs:
      try:
        cb(self._ret_val)
      except Exception,e:
        print "Error on when_done callback:"
        traceback.print_stack()
        traceback.print_exc()
#        print "\n\n"


class PollWhileTrueWaitable(PollUntilTrueWaitable):
  def __init__(self, cb):
    PollUntilTrueWaitable.__init__(self, lambda: not cb())


class CallbackDrivenWaitable(Waitable):
  def __init__(self):
    self._done = False
    self._ret_val = None
    self._aborted = False # if aborted, then done is also true
    self._abort_exc = None
    self._when_done_cbs = []
    self._check_for_abort = lambda: False

  def set_done(self, ret_val):
    self._done = True
    self._ret_val = ret_val
    cbs = list(self._when_done_cbs)
    del self._when_done_cbs[:]
    for cb in cbs:
      try:
        cb(self._ret_val)
      except Exception,e:
        print "Exception in when_done callback:"
        traceback.print_stack()
        traceback.print_exc()

  def set_check_for_abort_cb(self, cb):
    self._check_for_abort = cb

  def abort(self, abort_exc = Exception("Aborted")):
    self._done = True
    self._aborted = True
    self._abort_exc = abort_exc

  @property
  def is_done(self):
    if not self._done:
      if self._check_for_abort():
        self._aborted = True
        self._abort_exc = Exception("Aborted during is_done because of abort cb")
        self._done = True
    return self._done

  def wait(self):
    def poll():
      if self._done:
        return True
      if self._check_for_abort():
        self._done = True
        self._aborted = True
        self._abort_exc = Exception("Aborted because of abort cb")
        return True
      return False
    MessageLoop.run_until(poll)
    if self._aborted:
      raise self._abort_exc
    return self._ret_val

  def get_return_value(self):
    if not self._done:
      raise Exception("Cant get return value, not done.")
    if self._aborted:
      raise self._abort_exc
    return self._ret_val

  def when_done(self, cb, *args):
    if cb == None:
      raise Exception("Wtf")

    if self._done:
      try:
        cb(self._ret_val, *args)
      except Exception,e:
        print "Exception in when_done callback:"
        traceback.print_stack()
        traceback.print_exc()

    self._when_done_cbs.append(lambda v: cb(v, *args))


class CounterWaitable(Waitable):
  def __init__(self,initial_val,goal_val):
    if initial_val == goal_val:
      raise Exception("initial_val == goal_val")
    self._val = initial_val
    self._goal = goal_val
    self._done = False
    self._aborted = False
    self._when_done_cbs = []
    self._ret_val = None

  def inc(self, amt = 1):
    self._val += amt
    if self._val == self._goal:
      self._done = True
      self._fire()

  def dec(self, amt = 1):
    self._val -= amt
    if self._val == self._goal:
      self._done = True
      self._fire()

  def abort(self):
    self._done = True
    self._aborted = True

  def set_return_value(self, v):
    self._ret_val = v

  def _fire(self):
    cbs = list(self._when_done_cbs)
    del self._when_done_cbs[:]
    for cb in cbs:
      try:
        cb(self._ret_val)
      except Exception,e:
        print "Exception in when_done callback:"
        traceback.print_stack()
        traceback.print_exc()

  @property
  def is_done(self):
    return self._done

  def wait(self):
    MessageLoop.run_until(lambda: self._done)
    if self._aborted:
      raise Exception("Aborted")
    return self._ret_val

  def get_return_value(self):
    if not self._done:
      raise Exception("Cant get return value, not done.")
    if self._aborted:
      raise Exception("Aborted")
    return self._ret_val

  def when_done(self, cb, *args):
    if cb == None:
      raise Exception("Wtf")
    if self._done:
      raise Exception("Can't add listener. Already executed.")
    self._when_done_cbs.append(lambda v: cb(v, *args))

