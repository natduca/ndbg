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
import unittest
import threading
import Queue
import ui
import time
import gc
import traceback

from util.logging import *
from util.message_loop import *

 # a run command issued to the UI is treated as hung if this many seconds elapse
UI_THREAD_TIMEOUT = 10

class UIThreadException(Exception):
  def __init__(self,exc,msg):
    self._inner_exception = exc
    self._message = msg

  @property
  def inner_exception():
    self._inner_exception

  def __str__(self):
    return self._message

class UITimeoutException(Exception):
  pass

class UITestHarness(object):
  def __init__(self,options=None):
    self._mc = None
    self._loaded = threading.Event()
    self._options = options

    log2("UITestHarness: Starting UI")
    self._ui_thread = threading.Thread(target=self._ui_main)
    self._ui_thread.setName("ndbg UI thread")
    self._ui_thread.start()
    log2("UITestHarness: *********************************")

    log2("UITestHarness: Waiting for UI to become responsive")
    self._loaded.wait(5)
    if not self._loaded.is_set():
      log2("UITestHarness: UI is not responding. Test harness init failed.")
      raise Exception("Timed out initializing the UI")
    log2("UITestHarness: UI is up.")
    self._loaded = None


  def _ui_main(self):
    log2("UI thread: ui running.")
    def on_load_cb(mc):
      log2("UI thread: ui loaded. Notifying test thread.")
      self._mc = mc
      self._loaded.set()
    ui.run(self._options, on_load_cb)
    log2("UI thread: ui stoped.")

  def run_on_ui(self,cb,timeout):
    """Runs cb(mc) on the UI thread, where mc is the MainControl object for the UI.
    timeout is the amount of time to wait before considering the test hung.
    """
    exceptions = []
    ret = []
    done_event = threading.Event()
    def run_uitest_cmd():
      log2("UI thread: run_uitest_cmd begin...")
      if MessageLoop.has_unhandled_exceptions():
        excs = MessageLoop.get_unhandled_exceptions()
        assert len(excs) != 0
        uberexc = "Original exception:\n" + "\n\n".join(excs)
        MessageLoop.reset_unhandled_exceptions()
        exceptions.append(Exception("Unhandled exceptions"))
        exceptions.append(uberexc)
        log2("UI thread: run_uitest_cmd aborted due to unhandled exceptions.")
        done_event.set()
        return

      try:
        rv = cb(self._mc)
        ret.append(rv)
      except Exception,exc:
        log2("Exception raised when processing an add_message")
        fmt = traceback.format_exc()
        exceptions.append(exc)
        exceptions.append(fmt)
      log2("UI thread: run_uitest_cmd done.")
      done_event.set()
    MessageLoop.add_message(run_uitest_cmd)
    done_event.wait(timeout=timeout)
    if not done_event.is_set():
      log2("UITestHarness: run_uitest_cmd timed out.")
      raise UITimeoutException("Test timed out.")
    else:
      log2("UITestHarness: run_uitest_cmd done.")

    if len(ret):
      return ret[0]
    else:
      exc = exceptions[0]
      formatted_exc = exceptions[1]
      raise UIThreadException(exc, formatted_exc)

  def tearDown(self):
    log2("UITestHarness: Begin teardown")
    if self._ui_thread == None:
      log2("UITestHarness: Teardown stopped, already torn down")
      return

    log2("UITestHarness: Telling UI thread to exit.")
    MessageLoop.quit()

    # wait for the UI thread to exit
    self._ui_thread.join()
    self._ui_thread = None
    self._mc = None
    log2("UITestHarness: UI thread has exited. Teardown complete.")
    gc.collect()


class UITestCaseBase(unittest.TestCase):
  def setUp(self,options=None):
    self._harness = UITestHarness(options)

  def run_on_ui(self, cb, timeout=UI_THREAD_TIMEOUT):
    """Runs cb(mc) on the UI thread. The return value or excception
    are returned synchronously to the test thread."""
    return self._harness.run_on_ui(cb,timeout)

  def assertNoUnhandledExceptions(self):
    def do_nothing(mc):
      pass
    self.run_on_ui(do_nothing)

  def pause(self):
    import sys
    sys.stdout.write("Press enter to continue test...\n")
    sys.stdin.readline()

  def tearDown(self):
    self._harness.tearDown()

class UITestCaseSingle(UITestCaseBase):
  def setUp(self,testapp,options=None):
    UITestCaseBase.setUp(self,options)
    self.run_on_ui(lambda mc: mc.debugger.begin_launch_suspended(testapp).wait())

class UITestCaseMultiple(UITestCaseBase):
  def setUp(self,launch,options=None):
    """Initializes the UI with the specified options and launches the
    specified applications.

    launch should be a list of applications or applications + arguments to launch_suspended.

    options is the ndbg-style options result from optparse to be passed to the UI.
    """
    UITestCaseBase.setUp(self,options)
    i = 1
    for testapp in launch:
      proc = self.run_on_ui(lambda mc: mc.debugger.begin_launch_suspended(testapp).wait())
      attrname = "proc%i" % i
      setattr(self,attrname,proc)
      i += 1
