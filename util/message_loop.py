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
try:
  import glib
  import gtk
except:
  pass

import Queue
import traceback
import sys
import exceptions
import time
import threading
import thread

from util.logging import *

# TODO : this system is horribly thought out and organically grown. It pegs the CPU when there's nothing to do.
#
# I think a Task system might work better. Tasks that can be enqueued to threads, waited on, etc.
#
# The salient things it needs to do are:
#  - support for adding a tasks to run on the primary thread
#  - run_while(lambda) and run_until(lambda) that will pump the message loop until the condition is true
#  - run_* variants should work even on the primary thread [but can block the UI in that case]
#  - primary thread != main thread ---> the test framework runs the UI in a secondary thread
#  - quit needs to break any wait calls

_deferred_event_queue = Queue.Queue()
_cleanup_hooks = []
_keyboard_interrupt_hooks = []
_test_mode = False
_quit_requested = False

_initialied = False
_original_excepthook = None
_idle_hook_enabled = False
_run_thread = None
_run_thread_is_gtk = False


_unhandled_exceptions = []

import heapq
_pending_message_heap_lock = threading.Lock()
_pending_message_heap = []


class Message :
  def __init__(self,cb,ud):
    self.cb = cb
    self.ud = ud

class CancellableMessage(object):
  def __init__(self):
    self._run = True
    self._has_run = False
  def cancel(self):
    if self._has_run:
      raise Exception("Message has already been run. Cannot cancel.")
    self._run = False

class QuitException(Exception):
  pass

class MessageLoop:
  @staticmethod
  def set_in_test_mode(b):
    global _test_mode
    assert(type(b) == bool)
    _test_mode = True

  @staticmethod
  def get_in_test_mode():
    return _test_mode

  @staticmethod
  def add_cleanup_hook(cb):
    """
    Use a cleanup function to get rid of any stray objects, e.g. threads, that
    might have been left alive due to unexpected termination.
    """
    _cleanup_hooks.append(cb)

  @staticmethod
  def add_message(cb,*args):
    _deferred_event_queue.put(Message(cb,args))

  @staticmethod
  def add_delayed_message(cb, timeout_ms, *args):
    """Runs the cb in specified ms. Note that if cb returns True, the cb will be run again."""
    try:
      _pending_message_heap_lock.acquire()
      ts = (time.time() * 1000) + timeout_ms
      heapq.heappush(_pending_message_heap, (ts, cb, timeout_ms, args))
    finally:
      try:
        _pending_message_heap_lock.release()
      except thread.error:
        pass

  @staticmethod
  def add_cancellable_delayed_message(cb, timeout_ms, *args):
    msg = CancellableMessage()
    def run_msg():
      if not msg._run:
        return
      msg._has_run = True
      cb(*args)
    MessageLoop.add_delayed_message(run_msg, timeout_ms)
    return msg

  @staticmethod
  def _run_pending_messages():
    now = (time.time() * 1000) # this has to be outside the loop to avoid stalling when a callback aggressively renews itself
    while True:
      x = MessageLoop._try_pop_ready_message(now)
      if not x:
        break

      cb,timeout_ms,args = x

      # run the cb
      resp = MessageLoop._run_cb(cb,*args)
      if resp == True:
        MessageLoop.add_delayed_message(cb,timeout_ms,*args)


  @staticmethod
  def _try_pop_ready_message(now):
    try:
      _pending_message_heap_lock.acquire()
      if len(_pending_message_heap) == 0:
        return None
      ts = _pending_message_heap[0][0]
      if now > ts:
        x = heapq.heappop(_pending_message_heap)[1:]
        return x
      return None
    finally:
      try:
        _pending_message_heap_lock.release()
      except thread.error:
        pass

  @staticmethod
  def _run_pending_messages_xx():
    now = (time.time() * 1000) # this has to be outside the loop to avoid stalling when a callback aggressively renews itself
    cbs_to_run = []
    try:
      _pending_message_heap_lock.acquire()
      while True:
        if len(_pending_message_heap) == 0:
          break
        ts = _pending_message_heap[0][0]
        if now > ts:
          x = heapq.heappop(_pending_message_heap)[1:]
          cbs_to_run.append(x)
        else:
          break
    finally:
      try:
        _pending_message_heap_lock.release()
      except thread.error:
        pass

    for x in cbs_to_run:
      cb,timeout_ms,args = x
      # run the cb
      resp = MessageLoop._run_cb(cb,*args)
      if resp == True:
        MessageLoop.add_delayed_message(cb,timeout_ms,*args)

  @staticmethod
  def _add_delayed_message_using_gtk(cb, timeout_ms, *args):
    def run_cb(*unused):
      return MessageLoop._run_cb(cb, *args)
    glib.timeout_add(timeout_ms, run_cb)

  @staticmethod
  def run_until(cb):
    """
    Runs the message queue until cb returns true.
    Raises a QuitException if MessageLoop.Quit is issued during waiting.
    """
    if not callable(cb):
      raise Exception("cb is not callable")
    if cb():
      return
    while not cb():
      if _quit_requested:
        raise QuitException()
      time.sleep(0.001)
      MessageLoop._run_until_empty()
      MessageLoop._run_pending_messages()

  @staticmethod
  def run_while(cb):
    """
    Runs the message queue while cb returns true.
    Raises a QuitException if MessageLoop.Quit is issued during waiting.
    """
    if not callable(cb):
      raise Exception("cb is not callable")
    if not cb():
      return
    while cb():
      if _quit_requested:
        raise QuitException()
      time.sleep(0.001)
      MessageLoop._run_until_empty()
      MessageLoop._run_pending_messages()

  @staticmethod
  def _run_until_empty():
    """
    Runs the message queue until it is empty. Don't do this unless you're cofident that nobody else is posting messages.
    """
    while True:
      try:
        msg = _deferred_event_queue.get(block=False)
        MessageLoop._run_cb(msg.cb,*msg.ud)
      except Queue.Empty:
        return
      except Exception, ex:
        print ex
        return


  @staticmethod
  def _run_cb(cb,*args):
    """Runs a callback and saves exceptions if needed."""
    try:
      ret = cb(*args)
    except QuitException:
      raise
    except Exception:
      if _test_mode and threading.current_thread() == _run_thread:
        log2("MessageLoop: saving unhandled exception caused by add_message")
        fmt = traceback.format_exc()
        _unhandled_exceptions.append(fmt)
      else:
        traceback.print_stack()
        traceback.print_exc()
      ret = None
    return ret

  @staticmethod
  def init_hooks():
    log2("MessageLoop: Init hooks")
    global _initialied
    if _initialied:
      raise Exception("Already initialized.")
    _initialied = True
    # gtk idle hook
    global _idle_hook_enabled
    _idle_hook_enabled = True
    def on_idle():
      MessageLoop._run_until_empty()
      MessageLoop._run_pending_messages()
      return _idle_hook_enabled
    glib.idle_add(on_idle)

    # install exception hook
    global _original_excepthook
    _original_excepthook = sys.excepthook
    def excepthook(type, value, tb):
      if type == exceptions.KeyboardInterrupt:
        if _run_thread:
          log0("%i At excepthook, KeyboardInterrupt recieved, calling quit.", os.getpid())
          traceback.print_exception(type, value, tb)
          for cb in _keyboard_interrupt_hooks:
            try:
              cb()
            except:
              traceback.print_exc()
          MessageLoop.quit()
        else:
          print("Trapped keyboard interrupt inside excepthook. Raising")
          for cb in _keyboard_interrupt_hooks:
            try:
              cb()
            except:
              traceback.print_exc()
          raise # just re-raise it
      elif type == QuitException and _quit_requested == True:
        log1("MessageLoop: Unhandled quit exception, ignoring: %s", traceback.format_exception(type, value, tb))
      else:
        if _test_mode and threading.current_thread() == _run_thread:
          fmt = "".join(traceback.format_exception(type,value,tb))
#          log1("MessageLoop: unhandled exception during test:\n%s\n\n" % fmt)
          _unhandled_exceptions.append(fmt)
        else:
          fmt = "".join(traceback.format_exception(type,value,tb))
          log1("MessageLoop: unhandled exception:")
          _original_excepthook(type, value, tb)

    # override the except hook
    sys.excepthook = excepthook

  @staticmethod
  def shutdown_hooks():
    log2("MessageLoop: Shutdown hooks")
    global _initialied
    if not _initialied:
      raise Excepthook("Not initialized")
    _initialied = False

    # fix the idle proc
    _idle_hook_enabled = False

    # run cleanup_hooks
    MessageLoop._run_cleanup_hooks()

    if len(_unhandled_exceptions):
      MessageLoop.print_unhandled_exceptions()
      MessageLoop.reset_unhandled_exceptions()
    # restore excepthook
    sys.excepthook = _original_excepthook

    log1("MessageLoop: Shutdown of hooks complete.")

  @staticmethod
  def _run_cleanup_hooks():
    # run cleanup_hooks
    log1("MessageLoop: running cleanup_hooks.")
    cc = list(_cleanup_hooks) # copy them in case the cb changes
    for cb in cc:
      try:
        cb()
      except:
        traceback.print_stack()
        traceback.print_exc()

    del _cleanup_hooks[:]

  @staticmethod
  def run_no_gtk(idle_cb):
    global _run_thread
    _run_thread = threading.current_thread()
    global _run_thread_is_gtk
    _run_thread_is_gtk = False

    global _quit_requested
    _quit_requested = False

    did_init = False
    if _initialied == False:
      MessageLoop.init_hooks()
      did_init = True
    else:
      log2("Not initializing hooks.")

    # run gtk main loop
    while not _quit_requested:
      MessageLoop._run_until_empty()
      MessageLoop._run_pending_messages()
      try:
        idle_cb()
      except KeyboardInterrupt:
        log0("%i: At run_no_gtk, KeyboardInterrupt received", os.getpid())
#        traceback.print_exc()
        for cb in _keyboard_interrupt_hooks:
          try:
            cb()
          except:
            traceback.print_exc()
        MessageLoop.quit()
      except:
        print "Exception occurred in idle cb:"
        traceback.print_exc()

    _run_thread_is_gtk = False

    if did_init:
      MessageLoop.shutdown_hooks()

  @staticmethod
  def run():
    global _run_thread
    _run_thread = threading.current_thread()
    global _run_thread_is_gtk
    _run_thread_is_gtk = True

    global _quit_requested
    _quit_requested = False

    did_init = False
    if _initialied == False:
      MessageLoop.init_hooks()
      did_init = True
    else:
      log2("Not initializing hooks.")

    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

    # run gtk main loop
#    if _test_mode:
#      print "Putting GTK into threaded mode."
#      gtk.gdk.threads_init()
    gtk.main()
    _run_thread_is_gtk = False

    if did_init:
      MessageLoop.shutdown_hooks()


  @staticmethod
  def is_ui_running():
    return _run_thread != None

  @staticmethod
  def quit(intentionally_outside_main_loop=False):
    if not _run_thread and not intentionally_outside_main_loop:
      raise Exception("Quit not valid outside run")

    global _quit_requested
    _quit_requested = True # break any message loops

    # run cleanup_hooks

    if _run_thread_is_gtk:
      gtk.main_quit()
    elif intentionally_outside_main_loop:
      MessageLoop._run_cleanup_hooks()


  @staticmethod
  def is_quit_requested():
    return _quit_requested

  @staticmethod
  def has_unhandled_exceptions():
    return len(_unhandled_exceptions) != 0

  @staticmethod
  def get_unhandled_exceptions():
    return list(_unhandled_exceptions)

  @staticmethod
  def reset_unhandled_exceptions():
    del _unhandled_exceptions[:]

  @staticmethod
  def print_unhandled_exceptions():
    print "Unhandled exceptions:"
    for e in _unhandled_exceptions:
      print e
      print ""


  @staticmethod
  def add_keyboard_interrupt_hook(cb):
    _keyboard_interrupt_hooks.append(cb)
