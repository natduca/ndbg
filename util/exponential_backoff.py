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
import time
from util.message_loop import *
###########################################################################
_INITIAL = 0.0005 # seconds
_MAX_SLEEP_TIME = 0.25 # seconds
class ExponentialBackoffCounter(object):
  def __init__(self):
    self._val = 0
    self.reset()
  def reset(self):
    self._val = _INITIAL

  def inc(self):
    self._val = min(self._val * 2, _MAX_SLEEP_TIME)

  @property
  def val(self):
    """val is in seconds"""
    return self._val

###########################################################################
class ExponentialBackoff(object):
  def __init__(self):
    self._ctr = ExponentialBackoffCounter()

  def reset(self):
    self._ctr.reset()

  def sleep(self):
    if self._ctr != _INITIAL:
      time.sleep(self._ctr.val)
    self._ctr.inc()

class ThrottledCallback(object):
  def __init__(self, cb, sleep_multiplier = 1):
    """
    cb should return True if we processed useful work.
    sleep_multiplier should get larger if you want the loop to be less agressive.
    """
    self._cb = cb
    self._ctr = ExponentialBackoffCounter()
    self._run = True
    self._sleep_multiplier = sleep_multiplier * 1000
    MessageLoop.add_delayed_message(self._run_cb, self._ctr.val * self._sleep_multiplier)

  def stop(self):
    self._run = False

  def _run_cb(self):
    ret = self._cb()
    if ret:
      self._ctr.reset()
    else:
      self._ctr.inc()
    if self._run:
#      print "ret waas %s, so sleep ms is %s\n" % (ret, self._ctr.val * self._sleep_multiplier)
      MessageLoop.add_delayed_message(self._run_cb, self._ctr.val * self._sleep_multiplier)
    return False # dont let this delayed message re-trigger the callback

###########################################################################
if __name__ == "__main__":
  if 0:
    exp = ExponentialBackoffCounter()
    for i in range(20):
      print exp.val
      exp.inc()
  elif 1:
    from util.base import *
    ib = BoxedObject(0)
    def cb():
      i = ib.get()
      v = i % 10 == 0
      print "cb [i=%i] --> %s" % (i,v)
      ib.set(i+1)
      return v
    cb_throttle = ThrottledCallback(cb)
    MessageLoop.run()
