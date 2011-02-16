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
import subprocess
import shlex

import os
import code
import thread
import threading

import time
import re
import Queue

import weakref

from util import *

from . import *

from debugger_base import *
from gdb_backend import GdbBackend, GDB_STATUS_BREAK, GDB_STATUS_RUNNING
from gdb_parsers import GdbPhraseMatcher
from dpassive_process import *

import ui

class Debugger(DebuggerBase):
  def __init__(self,use_multiple_gdb_backends_override=False):
    DebuggerBase.__init__(self)
    self._first_added_process = None
    self._processes = IdentifiedItemListBase(lambda p: p.frontend_id)

    self._launchable_processes = BindingList()
    self._launchable_processes.item_added.add_listener(self._on_launchable_process_added)
    self._launchable_processes.item_deleted.add_listener(self._on_launchable_process_deleted)

    self._passive_processes = BindingList()
    self._passive_processes.item_added.add_listener(self._on_passive_process_added)
    self._passive_processes.item_deleted.add_listener(self._on_passive_process_deleted)


    self._threads = IdentifiedItemListBase(lambda t: t.frontend_id)
    self._ptys = BindingList()

    # backend managment
    self._backends = []
    self._gdb_backend = None # don't access this directly, use self._get_backend_for_new_process
    self._use_multiple_gdb_backends_override = use_multiple_gdb_backends_override
    self._pending_on_status_break_callbacks = [] # callbacks to run when we next hit status = break

    # processes, threads, status
    self._status_changed = Event()
    self._active_thread = None
    self._set_active_thread_pending = False
    self._active_frame_changed = Event()

    # other stuff
    self._init_breakpoints()
    self._init_interpreter()

  def _get_backend_for_new_process(self):
    if GdbBackend.supports_multiple_processes() and self._use_multiple_gdb_backends_override == False:
      if self._gdb_backend == None:
        log1("Debugger: Creating backend")
        rebind_breakpoints = self._temporarily_unbind_all_breakpoints()
        self._gdb_backend = GdbBackend()
        self._backends.append(self._gdb_backend)
        self._set_listening_to_backend(self._gdb_backend, True)
        rebind_breakpoints()
      return self._gdb_backend
    else:
      # search for a backend with zero processes
      for backend in self._backends:
        if len(backend.processes) == 0:
          log1("Debugger: Found backend with no processes")
          return backend

      log1("Debugger: Creating backend")
      rebind_breakpoints = self._temporarily_unbind_all_breakpoints()
      backend = GdbBackend()
      self._backends.append(backend)
      self._set_listening_to_backend(backend, True)
      rebind_breakpoints()
      return backend

    # pass
  def _set_listening_to_backend(self,backend,listen):
    if listen:
      backend.status_changed.add_listener(self._on_backend_status_changed)
      backend.symbols_changed.add_listener(self._on_backend_symbols_changed)
      backend.ptys.item_added.add_listener(self._on_backend_pty_added)
      backend.ptys.item_deleted.add_listener(self._on_backend_pty_deleted)
      backend.processes.item_added.add_listener(self._on_backend_process_added)
      backend.processes.item_deleted.add_listener(self._on_backend_process_deleted)
      backend.threads.item_added.add_listener(self._on_backend_thread_added)
      backend.threads.item_deleted.add_listener(self._on_backend_thread_deleted)
    else:
      backend.status_changed.remove_listener(self._on_backend_status_changed)
      backend.symbols_changed.remove_listener(self._on_backend_symbols_changed)
      backend.ptys.item_added.remove_listener(self._on_backend_pty_added)
      backend.ptys.item_deleted.remove_listener(self._on_backend_pty_deleted)
      backend.processes.item_added.remove_listener(self._on_backend_process_added)
      backend.processes.item_deleted.remove_listener(self._on_backend_process_deleted)
      backend.threads.item_added.remove_listener(self._on_backend_thread_added)
      backend.threads.item_deleted.remove_listener(self._on_backend_thread_deleted)

  def _check_backend_for_gc(self, backend):
    if GdbBackend.supports_multiple_processes() and self._use_multiple_gdb_backends_override == False:
      return # delete backend only on shutdown of the debugger
    else:
      # delete the backend if it has no more processes and isn't the last backend
      if self._backends > 1 and len(backend.processes) == 0 and len(backend.threads) == 0:
        log1("Debugger: Shutting down backend")
        rebind_breakpoints = self._temporarily_unbind_all_breakpoints()
        backend.shutdown(force=True)
        self._set_listening_to_backend(backend,False)
        self._backends.remove(backend)
        rebind_breakpoints()

  def shutdown(self):
    log1("Debugger: Shutting down")
    self._shutdown_breakpoints()
    log1("Debugger: Shutting backends")
    for backend in self._backends:
      self._set_listening_to_backend(backend,False)
      backend.shutdown(force=True)
    del self._backends[:]

  # basic stuff
  @property
  def first_added_process(self):
    return self._first_added_process

  def begin_launch_suspended(self,cmdline):
    """Begins to launch the specified process. Returns a Waitable
    object.  If process launch fails, calling wait, the return value
    stored in the waitable will be None."""
    if cmdline == None:
      raise DebuggerException("cmdline must not be null")
    if isinstance(cmdline,list):
      cmdline = ProcessUtils.shlex_join(cmdline)
    backend = self._get_backend_for_new_process()
    return backend.begin_launch_suspended(cmdline)

  def begin_attach_to_pid(self, pid, was_launched = None):
    if type(pid) != int:
      raise DebuggerException("Pid must be an int")

    backend = self._get_backend_for_new_process()
    return backend.begin_attach_to_pid(pid, was_launched)
  
  # launchable process list
  @property
  def launchable_processes(self):
    return self._launchable_processes

  def _on_launchable_process_added(self,idx,proc):
    proc._set_frontend_info(self)

  def _on_launchable_process_deleted(self,idx,proc):
    proc._set_frontend_info(None)


  # passive process list
  @property
  def passive_processes(self):
    return self._passive_processes
  def _on_passive_process_added(self,idx,proc):
    proc._set_frontend_info(self)

  def _on_passive_process_deleted(self,idx,proc):
    proc._set_frontend_info(None)

  # the omg i'm lost bomb
  def fire_all_listeners(self):
    self.status_changed.fire()
    self.active_frame_changed.fire()
    self.processes.changed.fire()
    self.threads.changed.fire()
    self._breakpoints.changed.fire()

  # Process status control --- needs to push to threads
  @property
  def status(self):
    if len(self.threads) != 0:
      # return STATUS_RUNNING until all backend report break status [this is to deal with the "interrupting" case]
      all_break = True
      for backend in self._backends:
        if backend.status != GDB_STATUS_BREAK:
          all_break  = False
      if all_break:
        return STATUS_BREAK
      else:
        return STATUS_RUNNING
    else:
      return STATUS_BREAK

  @property
  def status_changed(self):
    return self._status_changed

  def _fire_status_changed(self):

    if self.status == STATUS_BREAK:
      log1("Running %i on_status_break callbacks", len(self._pending_on_status_break_callbacks))
      for cb in self._pending_on_status_break_callbacks:
        log1("cb=%s", cb)
        cb()
      del self._pending_on_status_break_callbacks[:]
      log1("Done running on_status_break callbacks")
    log1("Debugger.status_changed to %s", self.status)
    self._status_changed.fire()

  def begin_interrupt(self):
    if self.status != STATUS_RUNNING:
      raise DebuggerException("Cannot resume when status != STATUS_RUNNING")

    wait = CounterWaitable(len(self._backends),0)
    for backend in self._backends:
      w = backend.begin_interrupt()
      w.when_done(lambda v: wait.dec(1))
    return wait

  # resume was requested for a specific thread
  # resume the other backends as well
  def _on_begin_resume(self,requesting_thread):
    if self.status != STATUS_BREAK:
      raise DebuggerException("Cannot resume when status != STATUS_BREAK")
    log2("_on_begin_resume(%s)", requesting_thread)
    wait = CounterWaitable(len(self._backends),0)
    w0 = requesting_thread._backend.begin_resume(requesting_thread)
    w0.when_done(lambda v: wait.dec())
    for backend in self._backends:
      if backend != requesting_thread._backend:
        w = backend.begin_resume_nonspecific(self)
        w.when_done(lambda v: wait.dec())
    return wait

  def _perform_begin_step(self,stepping_thread,step_action_cb):
    """General purpose mechanism for executing the various step commands."""

    if self.status != STATUS_BREAK:
      raise DebuggerException("Cannot step when status != STATUS_BREAK")
    log2("_perform_begin_step(%s)", stepping_thread)
    # the step over waitable will wait until the backend goes to status break
    # the begin_resume_nonspecific will wait until the backend goes to resume
    w0 = step_action_cb()
    for backend in self._backends:
      if backend != stepping_thread._backend:
        backend.begin_resume_nonspecific(self)

    def is_done():
      # wait for the actual step to complete [stepping_thread.backend status goes to break]
      # AND
      # wait for all the other backends  go to stop
      # which should happen automatically by the w0.wait going to breakf
      def test_all_break():
        all_break = True
        for be in self._backends:
          all_break &= be.status == GDB_STATUS_BREAK
        return all_break
      return w0.is_done and test_all_break()
    return PollUntilTrueWaitable(is_done)

  def _on_begin_step_over(self,requesting_thread):
    return self._perform_begin_step(requesting_thread, lambda: requesting_thread._backend.begin_step_over(requesting_thread))

  def _on_begin_step_into(self,requesting_thread):
    return self._perform_begin_step(requesting_thread, lambda: requesting_thread._backend.begin_step_into(requesting_thread))

  def _on_begin_step_out(self,requesting_thread):
    return self._perform_begin_step(requesting_thread, lambda: requesting_thread._backend.begin_step_out(requesting_thread))

  def _on_backend_breakpoint_hit(self, hit_backend, breakpoint):
    # stop all the other backends...
    log1("Debugger._on_backend_breakpoint_hit(%s,%s)", hit_backend, breakpoint)
    for backend in self._backends:
      if backend == hit_backend:
        continue
      backend.begin_interrupt()
    def fire_bkpt_changed():
      log1("Firing breakpoint %s hit", breakpoint)
      breakpoint.on_hit.fire()
    self._run_on_status_break(fire_bkpt_changed)

  def wait_for_status_break(self):
    def keep_waiting():
      if self.status == STATUS_RUNNING:
        return True
      else:
        return False
    MessageLoop.run_while(keep_waiting)

  # there is no wait_for_status_break because if you do that and the app exits,
  # then the loop would hang
  def _on_backend_status_changed(self,backend_that_changed):
    log1("Debugger._on_backend_status_changed: %s -> %s", backend_that_changed, backend_that_changed.status)
    if False: # for debugging state change events
      import traceback
      traceback.print_stack(limit=4)
      print "\n"
    if backend_that_changed.status == GDB_STATUS_BREAK:
      if backend_that_changed.thread_that_stopped != None:
        log1("Thread stopped with a thread_that_stopped.")
        self._set_active_thread_when_stopped(backend_that_changed.thread_that_stopped)
      else:
        log1("Thread stopped but thread_that_stopped is None.")
      for backend in self._backends:
        if backend != backend_that_changed and backend.status == GDB_STATUS_RUNNING:
          log1("Debugger: interrupting backend %s", backend)
          backend.begin_interrupt()
      self._fire_status_changed()
    else:
      self._fire_status_changed()
      self._active_frame_changed.fire()

  def _run_on_status_break(self,cb):
    self._pending_on_status_break_callbacks.append(cb)

  def _on_backend_symbols_changed(self,backend_that_changed):
    log1("Debugger._on_backend_symbols_changed")
    rebind = self._temporarily_unbind_all_breakpoints()
    rebind()

  # ptys
  @property
  def ptys(self):
    return self._ptys

  def _on_backend_pty_added(self,idx,pty):
    self._ptys.append(pty)

  def _on_backend_pty_deleted(self,idx,pty):
    self._ptys.remove(pty)

  # processes
  @property
  def num_processes_of_all_types(self):
    return len(self.processes) + len(self.passive_processes) + len(self.launchable_processes)

  @property
  def processes(self):
    return self._processes

  def _on_backend_process_added(self, proc):
    fe_id = 1
    while True:
      if self._processes.has_key(fe_id):
        fe_id += 1
        continue
      proc._set_frontend_info(self, fe_id)
      break

    log2("Debugger: Adding process fe_id=%s be_id=%s", proc.frontend_id, proc.backend_id)
    self._processes.add(proc)
    if self._first_added_process == None:
      self._first_added_process = proc


  def _on_backend_process_deleted(self, proc):
    log1("Debugger: Removing process fe_id=%s be_id=%s", proc.frontend_id, proc.backend_id)
    assert(proc._backend)
    self._check_backend_for_gc(proc._backend)

    fe_id = proc.frontend_id
    proc._set_frontend_info(None,None)

    self._processes.remove_key(fe_id)
    self._fire_status_changed()

    if len(self._processes) == 0:
      self._first_added_process = None


  # threads
  @property
  def threads(self):
    return self._threads
  @property
  def active_frame_changed(self):
    return self._active_frame_changed

  def _active_thread_somehow_changed(self):
    self._active_frame_changed.fire()

  @property
  def active_thread(self):
    if self.status == STATUS_BREAK:
      return self._active_thread
    else:
      return None

  @active_thread.setter
  def active_thread(self, thread):
    log2("Active thread set to %s", thread)
    if self._active_thread != None:
      self._active_thread.changed.remove_listener(self._active_thread_somehow_changed)
    self._active_thread = thread
    if self._active_thread:
      self._active_thread.process.last_active_thread = self._active_thread
      self._active_thread.changed.add_listener(self._active_thread_somehow_changed)
    self._active_frame_changed.fire()
  def _set_active_thread_when_stopped(self, thread):
    if self._set_active_thread_pending:
      return
    self._set_active_thread_pending = True

    def do_set_active_thread():
      assert(self.status == STATUS_BREAK)
      log1("Debugger: setting active thread to %s", thread)
      self.active_thread = thread
      self._set_active_thread_pending = False
    log1("Debugger: deferring active thread switch request to %s", thread)
    self._run_on_status_break(do_set_active_thread)



  def _on_backend_thread_added(self, thread):
    fe_id = 1
    while True:
      if self._threads.has_key(fe_id):
        fe_id += 1
        continue
      thread._set_frontend_info(fe_id)
      break
    log2("Debugger: Adding thread fe_id=%s be_id=%s", thread.frontend_id, thread.backend_id)
    self._threads.add(thread)

  def _on_backend_thread_deleted(self, thread):
    log2("Debugger: Removing thread fe_id=%s be_id=%s", thread.frontend_id, thread.backend_id)
    fe_id = thread.frontend_id
    thread._set_frontend_info(None)
    self._threads.remove_key(fe_id)

    if self._active_thread == thread:
      remaining_threads = list(self._threads)
      found = False
      for thr in remaining_threads:
        # just pick another thread... in future, try to pick one from this process...
        if thr.process and thr.process.backend_info: # pick one that is alive
          log2("Switchign active thread to %s", thr)
          self.active_thread = thr
          found = True
          break
        else:
          log2("Can't use thread %s, its process is dead too.", thr)
        
      if not found:
        log2("Setting active thread to None")
        self.active_thread = None
    self._fire_status_changed()
  # breakpoint logic
  ###########################################################################
  def _init_breakpoints(self):
    self._breakpoints = BindingList()
    def on_added(idx,b):
      log2("Breakpoint %s added", b)
      was_running = False
      if self.status == STATUS_RUNNING:
        log1("Breakpoint added while runnign. Interrupting teporarily...")
        self.begin_interrupt().wait()
        was_running = True
      if b._get_debugger() == None: # backend may have already been bound by the begin_interrupt symbols were added. sigh
        b._set_debugger(self)
      if was_running:
        log1("Resuming.")
        self.active_thread.begin_resume()
    def on_deleted(idx,b):
      log2("Breakpoint %s deleted", b)
      was_running = False
      if self.status == STATUS_RUNNING:
        log1("Breakpoint deleted while runnign. Interrupting teporarily...")
        self.begin_interrupt().wait()
        was_running = True
      if b._get_debugger() != None: # it may have gotten unbound if symbols changed
        b._set_debugger(None)
      if was_running:
        log1("Resuming.")
        self.active_thread.begin_resume()
    self._breakpoints.item_added.add_listener(on_added)
    self._breakpoints.item_deleted.add_listener(on_deleted)

  def _temporarily_unbind_all_breakpoints(self):
    """Unbinds all breakpoints and returns a function to rebind them."""
    log2("Unbinding %i breakpoints", len(self._breakpoints))
    bps = list(self._breakpoints)
    for b in bps:
      b._set_debugger(None)
    def rebind():
      log2("Rebinding %i breakpoints", len(bps))
      for b in bps:
        b._set_debugger(self)
    return rebind

  def _on_breakpoint_needs_update(self,b):
    was_running = False
    if self.status == STATUS_RUNNING:
      log1("Breakpoint added while runnign. Interrupting teporarily...")
      self.begin_interrupt().wait()
      was_running = True
    b._update()
    if was_running:
      log1("Resuming.")
      self.active_thread.begin_resume()

  def _on_breakpoint_changed(self,b):
    self._breakpoints.changed.fire()

  def _shutdown_breakpoints(self):
    log1("Shutting down breakpoints")
    for b in self._breakpoints:
      b._set_debugger(None)

  @property
  def breakpoints(self):
    return self._breakpoints

  def _eval_direct(self):
    """Symbol used to force direct eval."""
    raise Exception("Should never be called directly.")

  # simple command interpreter
  def begin_interpreter_exec(self, expr, cb, squash_exceptions=True):
    # Directly evaluate commands that start with *
    if expr.startswith("*"):
      expr = expr[1:]
      log1("Forced direct eval of %s" % expr)
      def call_cb(val):
        cb(val.value)
      self.active_thread._backend.begin_interpreter_exec_async(self.active_thread, expr, call_cb)
      return

    # Filter out certain gdb-style commands
    debug = get_loglevel() >= 1
    resp = self._immediate_exprs.fuzzy_get(expr,debug=debug)
    if resp[0] != None and resp[0] != self._eval_direct:
      expr_cb = resp[0]
      args = resp[1:]
      log1("interpreter_eval: special eval of %s via %s(%s)", expr, expr_cb, args)
      try:
        res = expr_cb(*args)
        cb(res)
      except Exception, ex:
        if squash_exceptions:
          cb(str(ex))
        else:
          raise
      return PollUntilTrueWaitable(lambda: True)

    # Command isn't blacklisted... pass it to the backend for evaluation
    log1("interpreter_eval: direct eval of %s", expr)
    def call_cb(val):
      cb(val.value)
    # todo reidrect this
    self.active_thread._backend.begin_interpreter_exec_async(self.active_thread, expr, call_cb)

  def _init_interpreter(self):
    self._immediate_exprs = GdbPhraseMatcher()
    def immed(expr, cb):
      self._immediate_exprs.add(expr, cb)

    # processes
    def info_processes(*args):
      s = ""
      for proc in self.processes:
        s += "%s\n" % str(proc)
      return s
    immed("info procs", info_processes)
    immed("info processes", info_processes)

    def proc(id_str = None):
      if id_str:
        id = int(id_str)
        if self.processes.has_key(id):
          proc = self.processes[id]
          return "Switching to thread %s" % str(proc)
          proc.make_active()
        else:
          raise Exception("Process ID %s not known." % str(id))
      else:
        return str(self.active_thread.process)
    immed("process", proc)

    immed("p", self._eval_direct) # force these to direct eval
    immed("print", self._eval_direct) # force these to direct eval

    # threads
    def info_threads(*args):
      s = ""
      for thread in self.threads:
        f0 = thread.call_stack[thread.active_frame_number]
        s += "%3s %s\n" % (thread.frontend_id, f0)
      return s
    immed("info threads", info_threads)

    def thread(arg0 = None, arg1 = None):
      if arg0 == None:
        return str(self.active_thread)
      elif re.match("^\d+$", arg0):
        id = int(arg0)
        if self.threads.has_key(id):
          thr = self.threads[id]
          return "Switching to thread %s" % str(thr)
          self.active_thread = thr
        else:
          raise Exception("Thread ID %s not known." % str(id))
      elif arg0 == 'apply':
        raise Exception("Not implemented,")
      else:
        raise Exception("Unrecognized command.")
    immed("thread", thread)

    def frame(frame_str = None):
      if frame_str:
        n = int(frame_str)
        cs = self.active_thread.call_stack
        if n < len(cs):
          self.active_thread.active_frame_number = n
          return ("%s" % str(cs[n]))
        else:
          raise Exception("Invalid frame number: %s" % str(n))
      else:
        return str(self.active_thread.active_frame_number)
    immed("f", frame) # required to disambiguate from finish
    immed("frame", frame)

    def up(delta=1):
      if type(delta) == str:
        delta = int(delta)
      new_afn = self.active_thread.active_frame_number + delta
      if new_afn < 0:
        self.active_thread.active_frame_number = 0
      elif new_afn >= len(self.active_thread.call_stack):
        self.active_thread.active_frame_number = len(self.active_thread.call_stack)-1
      else:
        self.active_thread.active_frame_number = new_afn
      return "%s" % str(self.active_thread.call_stack[self.active_thread.active_frame_number])
    immed("up", up)

    def down(delta = 1):
      if type(delta) == str:
        delta = int(delta)
      new_afn = self.active_thread.active_frame_number + delta
      if new_afn < 0:
        self.active_thread.active_frame_number = 0
      elif new_afn >= len(self.active_thread.call_stack):
        self.active_thread.active_frame_number = len(self.active_thread.call_stack)-1
      else:
        self.active_thread.active_frame_number = new_afn
      return "%s" % str(self.active_thread.call_stack[self.active_thread.active_frame_number])
    immed("down", down)

    # exiting
    def quit(*args):
      ui.quit()
      return "OK"
    immed("quit", quit)

    # breakpoints
    def info_breakpoints(*args):
      s = ""
      for b in self.breakpoints:
        if b.enabled:
          en = "Y"
        else:
          en = "N"
        s += "%4s %3s %s\n" % (b.id, en, b.location)
      return s
    immed("info breakpoints", info_breakpoints)

    # Disallowed commands. Things that you shouldn't muck with because it will
    # break assumptions in the heart of debugger
    def _disallowed(*args):
      cb("This command is not permitted because it would confuse my tiny little brain.")
    immed("info inferiors", _disallowed)
    immed("inferior", _disallowed)
    immed("add inferior", _disallowed)
    immed("remove inferior", _disallowed)
    immed("reverse", _disallowed)


    # just not implemented, haven't had the time
    def _not_implemented(*args):
      cb("Not implemented.")
    immed("attach", _not_implemented)
    immed("exec-run", _not_implemented)
    immed("exec", _not_implemented)
    immed("target", _not_implemented)
    immed("run", _not_implemented)
    immed("detach", _not_implemented)
    immed("disconnect", _not_implemented)
    immed("start", _disallowed)


    immed("break", _not_implemented)
    immed("enable", _not_implemented)
    immed("disable", _not_implemented)


    immed("return", _not_implemented)
    immed("next", _not_implemented)
    immed("nexti", _not_implemented)
    immed("jump", _not_implemented)
    immed("step", _not_implemented)
    immed("stepi", _not_implemented)
    immed("continue", _not_implemented)
    immed("finish", _not_implemented)
    immed("advance", _not_implemented)
    immed("signal", _disallowed)


    def kill_active_process(*args):
      self.active_thread.process.kill()
      return "Ok"
    immed("kill", kill_active_process)

