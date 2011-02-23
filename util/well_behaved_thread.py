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
from util.logging import *
from util.exponential_backoff import *
from util.event import *

import threading
import traceback

import Queue


class WellBehavedThread():
  def __init__(self, name, idle_cb=None):
    """
    cb should return True if work was performed, False if no work was found.
    """
    self._name = name
    self._idle_event = Event()
    if idle_cb:
      self._idle_event.add_listener(idle_cb)
    self._thread = None
    self._run = False
    self._message_queue = Queue.Queue()

  def __del__(self):
    if self._thread:
      self.stop()

  @property
  def name(self):
    return self._name

  @property
  def on_idle(self):
    return self._idle_event

  @property
  def should_run(self):
    """Returns whether the thread should be running. Will go to false
    before the actual thread stops."""
    return self._run and not MessageLoop.is_quit_requested()

  def is_runinng(self):
    """Returns whether the thread is running."""
    return self._thread != None

  def start(self):
    if self._thread:
      raise Exception("Already running")
    self._run = True
    self._thread = threading.Thread(target=self._thread_main)
    self._thread.setName(self._name)
    self._thread.start()
    log2("%s thread running", self._name)

  def _thread_main(self):
    exp = ExponentialBackoff()
    while self._run and not MessageLoop.is_quit_requested():
      self._run_message_queue()
      try:
        ret = self._idle_event.fire()
        if ret:
          exp.reset()
        else:
          exp.sleep()
      except:
        print "On %s thread:" % self._name
        traceback.print_exc()


  def stop(self):
    log2("%s thread stopping", self._name)
    self._run = False
    try:
      self._thread.join()
    except RuntimeError:
      pass
    log2("%s thread stopped", self._name)
    self._thread = None

  def add_message(self, cb,*args):
    if not callable(cb):
      raise Exception("must be callable")
    self._message_queue.put(Message(cb,args))

  def _run_message_queue(self):
    """
    Runs the message queue until it is empty. Don't do this unless you're cofident that nobody else is posting messages.
    """
    while True:
      try:
        msg = self._message_queue.get(block=False)
        self._run_cb(msg.cb,*msg.ud)
      except Queue.Empty:
        return
      except Exception, ex:
        print ex
        return


  def _run_cb(self,cb,*args):
    """Runs a callback and saves exceptions if needed."""
    try:
      ret = cb(*args)
    except QuitException:
      raise
    except Exception:
      traceback.print_exc()
      ret = None
    return ret

