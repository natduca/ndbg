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
import os
import code
import thread as pythread
import threading
import weakref
import time
import re
import Queue
import sys
import pty
import subprocess
import shlex




from util import *

from gdb_parsers import *
import debugger
from debugger_backend import *
from dprocess import *
from dthread import *
from dpty import *

_active_gdb_backends = []

GDB_STATUS_BREAK = "GDB_STATUS_BREAK"
GDB_STATUS_RUNNING = "GDB_STATUS_RUNNING"

_cleanup_added = False

_gdb_backend_id = 1

_debug_window = None
_debug_slave_file = None

def gdb_toggle_enable_debug_window():
  global _debug_window
  global _debug_slave_file
  if _debug_window:
    _debug_window.hide()
    _debug_slave_file.close()
    _debug_slave = None
    _debug_window = None
  else:
    import gtk
    import vte
    import pty
    master,slave = pty.openpty()
    _debug_slave_file = os.fdopen(slave,'w')
    _debug_slave_file.write("Commands sent to GDB backends will appear here\n");
    class GdbDebugWindow(gtk.Window):
      def __init__(self):
        gtk.Window.__init__(self)
        self.set_title("GDB Innards")
        self.term = vte.Terminal()
        self.term.set_pty(master)
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(self.term)
        self.add(sw)
        self.set_size_request(800,500)
        self.show_all()

      def hide(self):
        self.destroy()
    _debug_window = GdbDebugWindow()

class GdbBackend(DebuggerBackend):
  @staticmethod
  def supports_multiple_processes():
    return False # right now, gdb7.2 supports multiple process but will only run one at a time

  def __init__(self):
    DebuggerBackend.__init__(self)
    global _gdb_backend_id
    self._id = _gdb_backend_id
    _gdb_backend_id += 1

    # tell the main loop to clean us up
    global _cleanup_added
    if not _cleanup_added:
      MessageLoop.add_cleanup(GdbBackend._cleanup)
      _cleanup_added = True

    # init
    self._initialized = True
    _active_gdb_backends.append(weakref.ref(self)) # add cleanup here because we have a thread
    self._init_gdb()

    # state vars --- minimal but needed before we can run commands
    self._status = GDB_STATUS_BREAK
    self._status_changed = Event()
    self._symbols_changed = Event()
    self._symbols_changed_posted = False
    self._num_running_messages = 0

    # do feature detection
    self._init_and_determine_gdb_features()

    # get going
    self._first_inferior_free = True
    self._init_procs_and_threads()
    self._init_breakpoints()
    self._ptys = BindingList()

    resp = self._run_cmd("interpreter-exec console \"set width 9999\"")
    resp = self._run_cmd("interpreter-exec console \"set breakpoint pending off\"")
    resp = self._run_cmd("interpreter-exec console \"set interactive-mode off\"")
    resp = self._run_cmd("interpreter-exec console \"set inferior-events on\"")
    log1("GdbBackend Init complete")

  def __str__(self):
    return "GdbBackend #%s" % self._id

  def __repr__(self):
    return "GdbBackend #%s" % self._id

  def _trace(self,fmt,*args):
    log3(fmt,*args)

    if _debug_slave_file:
      if len(args):
        line = fmt % args
      else:
        line = fmt
      _debug_slave_file.write(line)
      _debug_slave_file.write("\n")
      _debug_slave_file.flush()


  def _determine_gdb_version(self):
    # determine version --- for some stuff, its just going to be easier doign version-based features
    resp = self._run_cmd("gdb-version")
    resp.expect_done()
    return GdbVersion.parse_from_version_lines(resp.gdblines)

  def _init_and_determine_gdb_features(self):
    ver = self._determine_gdb_version()

    # We don't secondary process creation right now because Gdb's wont run more than
    # one inferior at once.
    self._allow_multiple_processes = False

  @staticmethod
  def _cleanup():
    global _cleanup_added
    _cleanup_added = False

    global _active_gdb_backends
    new_active_gdb_backends = []
    for b_wr in _active_gdb_backends:
      b = b_wr()
      if b:
        new_active_gdb_backends.append(b_wr)
        log1("GdbBackend: Forcing shutdown of %s", b)
        try:
          b.shutdown(force=True)
        except:
          traceback.print_exc()
    _active_gdb_backends = new_active_gdb_backends

  @property
  def debugger_pid(self):
    if self.gdb:
      return self.gdb.pid
    else:
      return None

  status = property(lambda self: self._status)
  status_changed = property(lambda self: self._status_changed)

  """Symbols changed is a utils.Event with signatre cb(GdbBackend)
  fired when symbols change. You should recreate breakpoitns when this
  happens."""
  symbols_changed = property(lambda self: self._symbols_changed)

  def _on_symbols_changed(self):
    if self._status == GDB_STATUS_RUNNING:
      def fire():
        self._symbols_changed_posted = False
        self._symbols_changed.fire(self)
      if not self._symbols_changed_posted:
        self._symbols_changed_posted = True
        self._run_when_stopped(fire)
    else:
      self._symbols_changed.fire(self)
  ptys = property(lambda self: self._ptys)

  def shutdown(self, force=False):
    if self._initialized == False:
      return
    log1("GdbBackend #%s: Shutdown with initialized=%s", self._id,self._initialized)
    if force:
      self._initialized = False
      log1("GdbBackend #%s: Forcing shutdown", self._id)
      if self.status != GDB_STATUS_BREAK:
        try:
          self.begin_interrupt().wait()
        except:
          pass
      procs = list(self.processes)
      procs.reverse()
      for p in procs:
        try:
          self.kill_process(p)
        except:
          traceback.print_exc()
    else:
      if self.status != GDB_STATUS_BREAK:
        raise DebuggerException("Can't shutdown when status is not break")
      if len(self.processes):
        raise Exception("Can't shutdown when processes are running")
      self._initialized = False

    self._shutdown_gdb()


    for i in range(len(_active_gdb_backends)):
      if _active_gdb_backends[i]() == self:
        del _active_gdb_backends[i]
        log2("Removed %s from active backend list", self)
        break

    if len(self.processes):
      raise DebuggerException("Wasn't able to shut down all processes.")

  # Command channel type behaviors...
  def _init_gdb(self):
    self._run = True
    cmdline = "gdb -n --interpreter mi3"
    args = shlex.split(cmdline)
    self.gdb = subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    self._recvThread = threading.Thread(target=lambda: self._watcher(self.gdb.stdout))
    self._recvThread.setName("GDB watcher thread")
    self._recvThread.start()
    self._pendingCommands = {}
    self._cmdNum = self._id * 10000

  def _shutdown_gdb(self):
    log2("%s Shutting down gdb watcher thread...", self)
    # set run to false...
    # in all liklihood, the watcher thread is blocked waiting for gdb to output something
    # so echo a newline to gdb which will cause it to vomit back xx^done\n(gdb)\n
    # at this point, the thread will exit properly
    assert(self._run == True)
    self._run = False
    if not self.gdb.stdin.closed:
      try:
        self.gdb.stdin.write("\n")
        self.gdb.stdin.flush()
      except:
        log1("Gdb.stdin write failed....")
        pass
    else:
      log1("Gdb.stdin seems partially shutdown....")
    self._recvThread.join(1)
    if self._recvThread.isAlive():
      log2("%s Timed out waiting for reader thread. Killing gdb to unblock.", self)
      self.gdb.kill()
      log2("%s Waiting again for reader thread to die.", self)
      self._recvThread.join()
      log2("%s Reader thread closed.", self)
    else:
      log2("%s Killing gdb process...", self)
      self.gdb.kill()

    log2("%s Shutdown done.", self)

  def _watcher(self, input):
    log2("GdbBackend #%i: Stdin watcher thread running...", self._id)
    pending_commands  = []
    gdblines = []
    while self._run:
      l = input.readline()
      l=re.sub('\n$',"",l)
      if get_loglevel() >= 3 or _debug_slave_file:
        MessageLoop.add_message(self._trace, "     GDB%i<: %s", self._id, l) # push to messageloop to keep logical ordering

      if l == "": # not sure how these arise but don't freak out for the time being
        continue;

      # output delimiter
      if l == "(gdb) ":
        # run any command responses we got... we defer these so we send any
        # exec messages first (e.gg. running)
        for c in pending_commands:
          MessageLoop.add_message(c[0],c[1],c[2],c[3],c[4])
        pending_commands = []
        gdblines = []
        continue

      # GDB CLI stream
      if l.startswith("~"):
        actual_line = l[2:-1] # always is the string ~"...\n"
        actual_line = actual_line.replace("\\n", "") # eek
        actual_line = actual_line.replace("\\t", "\t")
        actual_line = actual_line.replace('\\"', '"')
        gdblines.append(actual_line)
        continue

      # Target output
      if l.startswith("@"):
        # we don't recieve this right now... :(
        continue

      # GDB debug messages
      if l.startswith("&"):
        continue

      # exec-async-output
      if l.startswith("*"):
        MessageLoop.add_message(self._on_exec_message, l)
        continue

      # status-async-output
      if l.startswith("+"):
        continue

      # notify-async-output
      if l.startswith("="):
        MessageLoop.add_message(self._on_notify_message, l)
        continue

      # command response
      m = re.match("^(\d+)\^(.[a-z]+),?(.*)$",l)
      if m:
        # an actual response...
        id = int(m.group(1))
        code = m.group(2)
        resp = m.group(3)
        pending_commands.append([self._on_cmd_complete, id, code, resp, gdblines])
        continue

      print "********* unrecognized: [%s] *****" % l
    log2("GdbBackend #%i: Stdin watcher thread exiting", self._id)

  # cmd running system
  def _run_cmd_async(self,c,cb = None): # cb gets run on main thread via MessageLoop.run_once()
    if c.startswith("-"):
      raise DebuggerException("Commands may not start with hyphen.")

    cmd = "%i-%s" % (self._cmdNum, c)
    if cb == None:
      cb = lambda x: 0
    self._pendingCommands[self._cmdNum] = cb
    self.gdb.stdin.write(cmd + "\n")
    self.gdb.stdin.flush()
    self._trace("");
    self._trace("*****GDB%i>: %s", self._id,cmd)

    self._cmdNum += 1

  def _on_cmd_complete(self,cmdNum,code,resp,gdblines):
    if not self._pendingCommands.has_key(cmdNum):
      raise DebuggerException("No pending command of id %i" % cmdNum)
    cb = self._pendingCommands[cmdNum]
    del self._pendingCommands[cmdNum]
    res = GdbMiResponse(code,resp)
    setattr(res,"gdblines",gdblines)
    cb(res)

  def _run_cmd(self,c):
    recvd = []
    def on_result(res):
      recvd.append(res)
    self._run_cmd_async(c,on_result);
    MessageLoop.run_while(lambda: len(recvd) == 0 and self._run)
    if len(recvd):
      return recvd[0]
    else:
      return GdbMiResponse("exited","")

  def _run_cmd_async_with_waitable(self, c, cb = None):
    waitable = CallbackDrivenWaitable()
    waitable.set_check_for_abort_cb(lambda: self._run == False)
    def on_result(res):
      waitable.set_done(res)
      if cb:
        cb(res)
    self._run_cmd_async(c,on_result);
    return waitable

  ###########################################################################
  # Processes and Threads
  ###########################################################################
  def _init_procs_and_threads(self):
    self._cur_inferior = 1
    self._processes = IdentifiedItemListBase( lambda x: x.backend_id)
    self._threads = IdentifiedItemListBase(lambda x: x.backend_id)
    self._run_when_stopped_queue = []

    self._creating_process = False # when set to true, neither processes nor threads are added
    self._killing_process = False # when set to true, neither processes nor threads are deleted
    self._new_process = None
    self._new_tid_that_stopped = None
    self._new_threads = []

    self._exited_process = None
    self._exited_threads = []

    self._attaching = False # durign attaching, we need a workaround to detect the stopped thread
    self._thread_that_stopped = None

    self._stop_pending = False
    self._processes_exit_code = None
  processes = property(lambda self: self._processes)
  threads = property(lambda self: self._threads)
  main_thread = property(lambda self: self._main_thread)
  thread_that_stopped = property(lambda self: self._thread_that_stopped)

  def _alloc_inferior(self):
    if self._first_inferior_free:
      self._first_inferior_free = False
      return 1
    else:
      resp = self._run_cmd("interpreter-exec console \"add-inferior\"")
      m = re.match("Added inferior (\d+)", resp.gdblines[0])
      if not m:
        raise DebuggerException("Could not create inferior.")
      else:
        i = int(m.group(1))
        log1("Inferior created %i", i)
        return i

  def _free_inferior(self, inf):
    if inf == 1:
      self._first_inferior_free = True
    else:
#      resp = self._run_cmd("interpreter-exec console \"remove-inferior %i\"" % inf)
      pass

  def _set_inferior(self, inf):
#    if self._cur_inferior != inf:
    self._cur_inferior = inf
    self._run_cmd("interpreter-exec console \"inferior %i\"" % inf) # mi doesn't support yet wtff

  def _on_notify_message(self, l): # message of type "=reason,stuffs"
    m = re.match("=(.+?),(.+)", l)
    if not m:
      raise Exception("Could not parse notify message.")
    resp = GdbMiResponse(m.group(1),m.group(2))
    if resp.code == "thread-group-added": # issued by gdb7.2
      pass
    elif resp.code == "thread-group-started": # issued by gdb7.2 and 7.1
      assert self._creating_process
      for p in self.processes:
        if p.backend_info and p.backend_info.pid == resp.pid:
          return # it already exists...
      log1("Added process pid=%s inferior=%s", resp.pid,self._cur_inferior)
      proc = DProcess(self, resp.id)
      proc._gdb_inferior = self._cur_inferior
      self._new_process = proc
    elif resp.code == "thread-group-created": # issued by gdb7.1 only, id is the pid
      log1("Added process pid=%s inferior=%s", resp.id,self._cur_inferior)
      assert self._creating_process
      proc = DProcess(self, resp.id)
      proc._gdb_inferior = self._cur_inferior
      self._new_process = proc
    elif resp.code == "thread-created":
      if self._creating_process:
        log1("Adding thread %s to new process", resp.id)
        assert self._new_process
        thr = DThread(self, resp.id, self._new_process)
        self._new_threads.append(thr)
      else:
        log1("Added thread %s", resp.id)
        proc = self._processes[resp.group_id]
        thr = DThread(self, resp.id, proc)
        proc.threads.append(thr)
        self._threads.add(thr)
    elif resp.code == "thread-selected": # issued by gdb7.2
      pass
    elif resp.code == "thread-exited":
      if self._creating_process:
        # happens eg when the process is linnked against a shared library that is missing
        # will exit before main runs
        raise Exception(" I have not implemented this path yet!!!")
      elif self._killing_process:
        log1("Thread %s exited during KILL", resp.id)
        thr = self._threads[resp.id]
        self._exited_threads.append(thr)
      else:
        log1("Thread %s exited", resp.id)
        proc = self._threads[resp.id].process
        thr = self._threads[resp.id]
        thr._processes = None
        thr._fire_changed()
        assert proc.backend_info # the process is complete... remove with event
        proc.threads.remove(thr)
        self._threads.remove(thr)

    elif resp.code == "thread-group-exited":
      if self._creating_process:
        raise Exception(" I have not implemented this path yet!!!")
      elif self._killing_process:
        log1("Thread group %s exited during KILL", resp)
        assert self._exited_process == None
        proc = self._processes[resp.id]
        self._exited_process = proc
      else:
        log1("Thread group %s exited", resp)
        if len(self._processes[resp.id].threads) != 0:
          raise Exception("Destroying process when its threads aren't all dead")
        proc = self._processes[resp.id]
        if proc.pty:
          self._ptys.remove(proc.pty)
          proc._set_pty(None)
        self._processes.remove(proc)
        self._free_inferior(proc.backend_info.inferior)
        proc._on_exited()
        self._on_symbols_changed()

    elif resp.code == "library-loaded":
      if not self._creating_process:
        self._on_symbols_changed()
    elif resp.code == "library-unloaded":
      if not self._creating_process:
        self._on_symbols_changed()
    else:
      print "Unrecognized notify: %s resp=[%s]" % (resp.code, str(resp))


  # messages of type * [ stopped, started, etc]
  def _conv_mi_threads_to_list(self,threads):
    if threads == "all":
      return [x for x in self._threads]
    else:
      if type(threads) == int:
        t = self._threads[threads]
        return [t]
      else:
        ids = threads.split(" ")
        return [self._threads[x] for x in ids]

  def _run_when_stopped(self,cb):
    if self._status == GDB_STATUS_RUNNING:
      self._run_when_stopped_queue.append(cb)
    else:
      cb()

  def _on_exec_message(self, l):
    m = re.match("\*running,(.+)", l)
    if m:
      resp = GdbMiResponse('running', m.group(1))
      log1("%i: Running confirmed by gdb with cur_status=%s: %s", self._id, self._status, resp.code)

      # forget stopped info..
      self._thread_that_stopped = None
      self._last_seen_thread_during_stop = None

      # set changed
      changed = self._status != GDB_STATUS_RUNNING
      thrs = self._conv_mi_threads_to_list(resp.thread_id)
      if changed:
        log2("%i: Set status to running", self._id)
        self._status = GDB_STATUS_RUNNING
        for thr in thrs:
          thr._set_status(STATUS_RUNNING)

      # track the num_running_messages... we use this for waiting on running
      self._num_running_messages += 1

      # now fire events
      if changed and not self._creating_process:
        self._status_changed.fire(self)
        for thr in thrs:
          thr._fire_changed()
      return

    m = re.match("\*stopped,?(.*)", l)
    if m:
      resp = GdbMiResponse("stopped", m.group(1))
      log1("%i: Stopped confirmed by gdb: %s", self._id, resp.code)

      reason = ""
      if hasattr(resp,"reason"):
        reason = resp.reason

      # clear the stop pending flag
      self._stop_pending = False

      # remember who caused us to stop
      self._thread_that_stopped = None
      self._processes_exit_code = None
      if reason == 'exited':
        self._processes_exit_code = resp.exit_code
      elif reason == 'exited-normally':
        self._processes_exit_code = 0
      elif reason == 'exited-signalled':
        self._processes_exit_code = resp.signal_name
      elif reason:
        if self._creating_process:
          self._new_tid_that_stopped = resp.thread_id
        else:
          self._thread_that_stopped = self._threads[resp.thread_id]

      if self._attaching and hasattr(resp, 'thread_id'):
        if self._creating_process:
          self._new_tid_that_stopped = resp.thread_id
        else:
          self._thread_that_stopped = self._threads[resp.thread_id]

      # change status but don't fire changed events
      if hasattr(resp,"stopped_threads"):
        thrs = self._conv_mi_threads_to_list(resp.stopped_threads)
      else:
        thrs = []

      changed = self._status != GDB_STATUS_BREAK
      if changed:
        log2("%i Set status to break.", self._id)
        self._status = GDB_STATUS_BREAK
        for thr in thrs:
          thr._set_status(STATUS_BREAK) # set but dont fire events

      # run everythign in the stopped queue before we fire status_changed
      tmp = self._run_when_stopped_queue
      self._run_when_stopped_queue = [] # reset it before cbs in case cbs cause runs
      for cb in tmp:
        cb()
      self._run_when_stopped_queue = []
      log2("Ran the stopped queue.")

      # fire status_changed
      if changed and not self._creating_process:
        self._status_changed.fire(self)
        for thr in thrs:
          thr._fire_changed()

      # breakpoint hit
      if reason == 'breakpoint-hit':
          self._on_breakpoint_hit(resp)


      return

    raise Exception("Wtf is this?!!! %s" % l)

  # Launching, ataching, et cetera
  ###########################################################################
  def begin_launch_suspended(self,cmdline):
    """Begins to launch task. Returns waitable for the completion of the task."""
    if cmdline == None:
      raise DebuggerException("Cmdline must not be null.")
    if self._status == GDB_STATUS_RUNNING:
      raise DebuggerException("Expected break or not-running status")
    if len(self.processes) == 1 and self._allow_multiple_processes == False:
      raise Exception("Your version of GDB does not support multiple processes. Use debugger.Debugger to hide this fact from you.")

    # create an inferior
    inf = self._alloc_inferior()
    self._set_inferior(inf)

    # set the tty
    pty_fds = pty.openpty()
    slavedev = os.ttyname(pty_fds[1])
    resp = self._run_cmd("inferior-tty-set %s" % slavedev)
    resp.expect_done()
    dpty = DPty(pty_fds[0],pty_fds[1])
    dpty.name = "tty for inferior %i" % inf
    self._ptys.append(dpty) # should cause FE to attach a VTE or similar to it

    # launch the process
    words = cmdline.split(" ")
    prog = words[0]
    args = " ".join(words[1:])

    # now, we will load symbols.... this may take a while, so we will
    # do it asynchronously. We will return a waitable so the UI can be
    # productive in the meantime.
    log1("Loading symbosl for prog=%s", prog)
    symbols_loaded = self._run_cmd_async_with_waitable("file-exec-and-symbols %s" % prog)

    # switch status [passively] to running here...
    self._status = GDB_STATUS_RUNNING


    # the totally done task represents completion of on_symbols_loaded
    totally_done = CallbackDrivenWaitable()
    def on_symbols_loaded(resp):
      log1("Symbols loaded. Launching...")
      if resp.code != "done":
        self._ptys.remove(dpty)
        self._status = GDB_STATUS_BREAK
        totally_done.abort(DebuggerException("Error: %s" % resp.msg))
        return
      resp = self._run_cmd("exec-arguments %s" % args)
      resp.expect_done()

      # listen for process add
      self._creating_process = True

      # get the program going....
      bkpt = self._run_cmd("break-insert main")
      bkpt.expect_done()

      waitable_for_status_break = self._make_status_break_waitable()
      resp = self._run_cmd("exec-run")
      resp.expect('running')

      # wait a bit... we should eventually stop...
      def finalize_launch():
        self._creating_process = False

        # we should have procss that was added...
        if not self._new_process:
          self._new_process = None
          del self._new_threads[:]
          totally_done.abort(DebuggerException("A processes wasn't created. This is kind of a problem."))
          self._status = GDB_STATUS_BREAK
          return

        proc = self._new_process
        if len(self._new_threads) == 0:
          log1("Process launch failed with return code: %i" % self._process_exit_code)
          dpty.name = "error message for %s"
          totally_done.abort(DebuggerException("Process launch failed with return code: %i" % self._process_exit_code))
          return
        log1("Process launch seems to have worked.")

        # delete the breakpoint we used to get to main...
        resp = self._run_cmd("break-delete %i" % bkpt.bkpt.number)
        resp.expect_done("Couldn't delete temp breakpoint we set on main.")

        # store backend info for the new process
        proc._set_backend_info(self._get_process_info(proc), True)

        # bind to its pty
        proc._set_pty(dpty)

        # add the process & threads to the public process and thread lists
        for t in self._new_threads:
          t._set_status(STATUS_BREAK)
          proc.threads.append(t)
        self.processes.add(proc)
        assert proc._debugger != None
        for t in self._new_threads:
          self._threads.add(t)
        del self._new_threads[:]
        if self._new_tid_that_stopped:
          self._thread_that_stopped = self._threads[self._new_tid_that_stopped]
        self._new_tid_that_stopped = None

        # fire status changed even though its a lie
        self._status_changed.fire(self)

        # fire symbols changed
        self._on_symbols_changed()

        # we're done
        totally_done.set_done(proc)

        #MessageLoop.add_delayed_message(lambda: totally_done.set_done(proc), 10000)
      #waitable_for_status_break.when_done(finalize_launch)
      waitable_for_status_break.wait() # temporary hack while i clean up process addition logic
      finalize_launch()

    symbols_loaded.when_done(on_symbols_loaded)
    return totally_done

  def begin_attach_to_pid(self,pid,was_launched_hint):
    print "****: %s" % was_launched_hint
    if self._status == GDB_STATUS_RUNNING:
      raise DebuggerException("Expected break or not-running status")
    if len(self.processes) == 1 and self._allow_multiple_processes == False:
      raise Exception("Your version of GDB does not support multiple processes. Use debugger.Debugger to hide this fact from you.")

    # create an inferior
    inf = self._alloc_inferior()
    self._set_inferior(inf)

    # listen for process add
    self._creating_process = True

    # in the case of attaching, gdb doesn't raise a 'stopped' message
    # with a reason this confuses our thread-that-stopped logic.  The
    # thead-that-stopped logic has a workaround that is enabled when
    # the following flag is set...
    self._attaching = True

    # switch status [passively] to running first...
    self._status = GDB_STATUS_RUNNING

    # we will attach in the background and do the rest in a followup.
    # we use a custom waitable here instead of a
    # _make_status_break_waitable because that intrinsic expects us to
    # get a "*running" message whereas in the attach case, we won't!
    aborted = BoxedObject(False)
    def on_cmd_done(resp):
      if resp.code == "error":
        log0("Error during attach: %s", resp)
        aborted.set(True)
    self._run_cmd_async("target-attach %i" % pid, on_cmd_done)
    attached = PollUntilTrueWaitable(lambda: aborted.get() or (self._status == GDB_STATUS_BREAK and self._new_process))
    totally_done = CallbackDrivenWaitable()
    def finalize_attach(res):
      log2("finalizing attach")
      # clear various flags
      self._attaching = False

      # see if the target-attach commmand failed
      if aborted.get():
        log2("attach aborted")
        self._creating_process = False
        self._new_process = None
        del self._new_threads[:]
        self._status = GDB_STATUS_BREAK
        totally_done.abort(DebuggerException("No process found."))
        return

      # we should have procss that was added...
      if not self._new_process:
        log2("no new process")
        self._creating_process = False
        self._status = GDB_STATUS_BREAK
        self._new_process = None
        del self._new_threads[:]
        totally_done.abort(DebuggerException("A processes wasn't created. This is kind of a problem."))
        return

      proc = self._new_process
      self._new_process = None

      # Ensure that the thread-that-stopped attaching workaround caused us to
      # obtain the stopped thread id.
      assert(self._new_tid_that_stopped)

      # figure out if we're a ndbg_launcher
      resp = self._run_cmd("interpreter-exec console \"info address __is_ndbg_launcher_waiting\"")
      if resp.code == "done":
        # this is an ndbg launcher
        log1("Detected an app launched by ndbg_launcher.")

        log1("Unblocking")
        resp = self._run_cmd("interpreter-exec console \"call __is_ndbg_launcher_waiting=0\"")

        log1("Catching exec")
        resp = self._run_cmd("interpreter-exec console \"tcatch exec\"")

        # send a raw continue command --> this will continue and load the new library
        # eventually we will go to stopped, which will put is in the new process w00t
        # we will also see a command from gdb
        # ~"process 8662 is executing new program: /foo/bar\n"
        # the process will be in _start, not main()
        print "******Phase1***************************************"
        waitable_for_status_break = self._make_status_break_waitable(chatty=False)
        resp = self._run_cmd("exec-continue") # need to supress events firing!!!!
        resp.expect('running')

        # continue
        log1("Waiting for new process to _start")
        waitable_for_status_break.wait()
        print "******Phase2***************************************"

        bkpt = self._run_cmd("break-insert main")
        bkpt.expect_done()

        waitable_for_status_break = self._make_status_break_waitable(chatty=False)
        resp = self._run_cmd("exec-continue")
        resp.expect('running')

        # wait a bit... at_main will be called when we eventually stop...
        def at_main(resp):
          self._creating_process = False
          # update the backend info...
          proc._set_backend_info(self._get_process_info(proc), True)
          log2("new proc is %s" % proc.target_exe)

          # add the process & threads to the public process and thread lists
          for t in self._new_threads:
            t._set_status(STATUS_BREAK)
            proc.threads.append(t)
          self.processes.add(proc)
          for t in self._new_threads:
            self._threads.add(t)
          del self._new_threads[:]
          if self._new_tid_that_stopped:
            self._thread_that_stopped = self._threads[self._new_tid_that_stopped]
          self._new_tid_that_stopped = None

          # fire status changed even though its a lie
          self._status_changed.fire(self)

          # fire symbols changed
          self._on_symbols_changed()

          # we're done...
          totally_done.set_done(proc)

        # wait for the breakpoitn to be hit
        waitable_for_status_break.when_done(at_main)

      else:
        self._creating_process = False
        log2("Getting backend info");
        # store backend info for the new process
        if was_launched_hint:
          proc._set_backend_info(self._get_process_info(proc), was_launched_hint)
        else:
          proc._set_backend_info(self._get_process_info(proc), False)

        # add the process & threads to the public process and thread lists
        for t in self._new_threads:
          t._set_status(STATUS_BREAK)
          proc.threads.append(t)
        self.processes.add(proc)
        for t in self._new_threads:
          self._threads.add(t)
        del self._new_threads[:]
        if self._new_tid_that_stopped:
          self._thread_that_stopped = self._threads[self._new_tid_that_stopped]
        self._new_tid_that_stopped = None

        # fire status changed even though its a lie
        self._status_changed.fire(self)

        # fire symbols changed
        self._on_symbols_changed()

        # we're done...
        totally_done.set_done(proc)

    attached.when_done(finalize_attach)
    return totally_done

  def _get_process_info(self,proc):
    out = DynObject()
    # select a thread from the process so interpreter-exec gets a decent thread
    #thr = list(proc.threads)[0]
    #self._run_cmd_async("thread-select %s" % thr.backend_id, lambda x: None )

    # figure out pid
    resp = self._run_cmd("interpreter-exec console \"info proc\"")
    procInfo = parse_loose_dict(resp.gdblines)
    pid = int(procInfo.process)
    out.target_cwd = str(procInfo.cwd)
    out.target_exe = str(procInfo.exe)

    # figure out cdir
    resp = self._run_cmd("interpreter-exec console \"where\"")
    resp.expect_done()
#    print "last is %s" % resp.gdblines[-1];
    m = re.match("#(\d+)", resp.gdblines[-1])
    assert m
    last_frame_number = int(m.group(1))
#    print "last_frame is %i" % last_frame_number
    resp = self._run_cmd("interpreter-exec console \"thread 1\"")
    resp.expect_done()
    resp = self._run_cmd("interpreter-exec console \"frame %i\"" % last_frame_number)
    resp.expect_done()
    resp = self._run_cmd("interpreter-exec console \"info source\"")
    resp.expect_done()
    found = False
    for l in resp.gdblines:
      m = re.match("^Compilation directory is (.+)$",l)
      if m:
        out.compilation_directory = m.group(1)
        found = True
        break
    if found == False:
      out.compilation_directory = None

    # figure out cmdline
    out.full_cmdline = ProcessUtils.get_pid_full_cmdline_as_array(pid)

    # remember the pid
    out.pid = pid

    # remember the inferior
    out.inferior = self._cur_inferior

    # we're done
    return out

  def kill_process(self, proc):
    if proc.backend_info == None: # not running
      print "kill proc called with proc not running"
      raise DebuggerException("Process %s is not running" % proc)


    self._killing_process = True

    log2("Kill process %s inf=%s begins", proc,proc.backend_info.inferior)
    inf = proc.backend_info.inferior
    self._set_inferior(inf)

    resp = self._run_cmd("interpreter-exec console \"kill inferior %i\"" % inf)
    self._killing_process = False

    # error handling for failed exit
    if resp.code == "error":
      raise DebuggerException("Could not kill process %s: %s" % (proc,resp.msg))
    assert( resp.code == "exited" or resp.code == "done" )

    if self._exited_process == None:
      raise DebuggerException("Process kill succeeded but no exited process found. WTF?")
    if len(self._exited_threads) == 0:
      log0("Process kill succeeded but no exited threads found. Non-critical but strange.")

    # get rid of backend on the process
    log2("After kill, beginning to remove process %s" % proc)
    proc = self._exited_process
    backend_info = proc.backend_info
    be_id = proc.backend_id
    proc._on_exiting() # clear the backend info

    assert proc in self._processes
    self._exited_process = None

    # remove threads
    for thr in self._exited_threads:
      log2("After kill, removing thread %s" % thr)
      thr._process = None
      thr._fire_changed()
      proc.threads.remove(thr)
      self._threads.remove(thr)
    self._exited_threads = []

    # remove pty, remove the process itself
    log2("After kill, cleaning up process %s" % proc)
    assert len(proc.threads) == 0
    self._processes.remove_key(be_id)

    if proc.pty:
      self._ptys.remove(proc.pty)
      proc._set_pty(None)
    proc._on_exited()

    # bookkeeping
    self._free_inferior(backend_info.inferior)
    self._on_symbols_changed()



    log2("Kill process %s complete", proc)

  def detach_process(self, proc):
    resp = self._run_cmd("interpreter-exec console \"detach inferior %i\"" % proc.inferior)
    # target-detach pid

  # flow control
  ###########################################################################
  def begin_resume_nonspecific(self, thr):
    """
    Resumes the debugger on all threads that the backend choses. Same caveats as _begin_resume apply.
    """
    return self._begin_resume(None)

  def begin_resume(self, thr):
    """
    Resumes the debugger on all threads. Same caveats as _begin_resume apply.
    """
    return self._begin_resume(thr)

  def _begin_resume(self, thr=None):
    """
    Begins to resume the debugger. Note that status is still break when you return from here!!!!
    If you are counting on the debugger going to running, then make sure you wait on the returned object.
    E.g. begin_resume.wait()
    """
    if self._status != GDB_STATUS_BREAK:
      raise DebuggerException("GdbBackend %s: Cannot resume when status is already %s" % (self._id, self._status))

    log2("%i: begin resume with cur status=%s", self._id, self._status)
    orig_num_runnings = self._num_running_messages

    changed = self._status != GDB_STATUS_RUNNING
    self._status = GDB_STATUS_RUNNING
    for thr in self._threads:
      thr._set_status(STATUS_RUNNING)
    if changed:
      self._status_changed.fire(self)
      for thr in self._threads:
        thr._fire_changed()

    if thr:
      self._run_cmd_async("exec-continue --thread %s"% thr.backend_id, lambda res: 1)
    else:
      self._run_cmd_async("exec-continue", lambda res: 1)

    return PollWhileTrueWaitable(lambda: self._num_running_messages == orig_num_runnings)

  def begin_interrupt(self):
    if self._stop_pending:
      log2("%i: begin_interrupt and _stop_pending", self._id)
      return PollWhileTrueWaitable(lambda: self._status == GDB_STATUS_RUNNING)
    log2("%i: begin_interrupt", self._id)
    self._stop_pending = True
    for proc in self._processes:
      if proc.backend_info == None:
	raise DebuggerException("Cannot interrupt %s, not running." % proc)
      else:
        os.system("kill -INT %s" % proc.backend_info.pid)
    return PollWhileTrueWaitable(lambda: self._status == GDB_STATUS_RUNNING)

  def _make_status_break_waitable(self,chatty=False): # waits on NEXT break -- if we're break already, it doesn't count
    orig_num_runnings = self._num_running_messages
    def check_break():
      # have we gone into resume?
      if chatty:
        print "checkbrk: %i %i %s" % (self._num_running_messages, orig_num_runnings, self._status)
      if self._num_running_messages == orig_num_runnings:
        return False
      return self._status == GDB_STATUS_BREAK

    return PollUntilTrueWaitable(check_break)

  def begin_step_over(self,thread ):
    log2("%i: begin_step_over", self._id)
    w = self._make_status_break_waitable()
    changed = self._status != GDB_STATUS_RUNNING
    self._status = GDB_STATUS_RUNNING
    if changed:
      self._status_changed.fire(self)
    self._run_cmd_async("exec-next --thread %s" % thread.backend_id, lambda res: 1)
    return w

  def begin_step_into(self, thread):
    log2("%i: begin_step_into", self._id)
    w = self._make_status_break_waitable()
    changed = self._status != GDB_STATUS_RUNNING
    self._status = GDB_STATUS_RUNNING
    if changed:
      self._status_changed.fire(self)
    self._run_cmd_async("exec-step --thread %s" % thread.backend_id, lambda res: 1)
    return w

  def begin_step_out(self, thread):
    log2("%i: begin_step_out", self._id)
    w = self._make_status_break_waitable()
    changed = self._status != GDB_STATUS_RUNNING
    self._status = GDB_STATUS_RUNNING
    if changed:
      self._status_changed.fire(self)
    self._run_cmd_async("exec-finish --thread %s" % thread.backend_id, lambda res: 1)
    return w



  # program execution
  ###########################################################################
  def _init_breakpoints(self):
    self._breakpoint_map_id_to_hit_cb = {}
    pass

  """Should return an object with an id and location_list=list(Locations)"""
  def new_breakpoint(self,location,hit_cb):
    if location.has_pc:
      bcmd = "break-insert *%s"% location.prog_ctr
    elif location.has_file_location:
      bcmd = "break-insert %s:%i" % (location.filename, location.line_num)
    elif location.has_identifier:
      bcmd = "break-insert %s" % (location.identifier)
    else:
      raise DebuggerException("Don't know how to create bkpt for %s" % location)

    # create it
    resp = self._run_cmd(bcmd)

    # parse response...
    if resp.code == "error":
      raise DebuggerException(resp.msg)

    # remember cb
    self._breakpoint_map_id_to_hit_cb[resp.bkpt.number] = hit_cb

    # is it a compound breakpoint?
    if resp.bkpt.addr == "<MULTIPLE>":
      hinfo = self._run_cmd("break-info %i" % resp.bkpt.number)
      cinfo = self._run_cmd("interpreter-exec console \"info breakpoint %i\"" % resp.bkpt.number)
      bps = parse_multiple_breakpoint_info(hinfo,cinfo.gdblines)
      if bps[0].type != "breakpoint":
        raise DebuggerException("Unexpected response.")
      real_bps = bps[1:]
      locations = []
      for b in real_bps:
        l = parse_console_style_location(b.addr)
        log1("Got %s", l)
        locations.append(l)
      return DynObject({"id" : resp.bkpt.number,
                        "location_list" : locations})
    else:
      l = parse_location(resp.bkpt)
      return DynObject({"id" : resp.bkpt.number,
                        "location_list" : [l] })

  def enable_breakpoint(self,id):
    resp = self._run_cmd("break-enable % i" % id)

  def disable_breakpoint(self,id):
    resp = self._run_cmd("break-disable %i" % id)

  def _on_breakpoint_hit(self,resp):
    if self._breakpoint_map_id_to_hit_cb.has_key(resp.bkptno):
      self._breakpoint_map_id_to_hit_cb[resp.bkptno]()

  def delete_breakpoint(self,id):
    del self._breakpoint_map_id_to_hit_cb[id]
    resp = self._run_cmd("break-delete %i" % id)


  # State accessors - always done with a thread
  ###########################################################################
  def get_call_stack(self,thr):
    if self._status != GDB_STATUS_BREAK:
      raise DebuggerException("Only valid in breakpoint mode.")
    resp = self._run_cmd("stack-list-frames --thread %s" % thr.backend_id)
    return [parse_stack_frame(x) for x in resp.stack]
  def get_frame(self,thr,frame):
    if self._status != GDB_STATUS_BREAK:
      raise DebuggerException("Only valid in breakpoint mode.")
    assert type(frame) == int
    resp = self._run_cmd("stack-list-frames --thread %s %i %i" % (thr.backend_id, frame, frame))
    if not hasattr(resp, "stack"):
      import pdb; pdb.set_trace()

    assert len(resp.stack) == 1
    return parse_stack_frame(resp.stack[0])

  def begin_interpreter_exec_async(self,thr,expr,cb):
    if expr == "debug":
      gdb_toggle_enable_debug_window()
      res= DynObject()
      res.valid = True
      res.value = "OK"
      w = CallbackDrivenWaitable()
      MessageLoop.add_message(lambda: argn(cb(res), w.set_done(res)))
      return w

    quoted_expr = expr.replace('\\', '\\\\')
    quoted_expr = quoted_expr.replace('"', '\\"')

    cmd = "interpreter-exec --thread %i --frame %i console \"%s\"" % (thr.backend_id,thr.active_frame_number, quoted_expr)
    def cleanup_result(resp):
      res = DynObject()
      if resp.code == "error":
        res.valid = False
        res.value = resp.msg
      else:
        res.valid = True
        res.value = "\n".join(resp.gdblines)
      cb(res)
    w = self._run_cmd_async_with_waitable(cmd,cleanup_result)
    return w

  def get_expr_value_async(self,thr,expr,cb):
    cmd = "data-evaluate-expression --thread %s --frame %i %s" % (thr.backend_id,thr.active_frame_number, expr)
    def cleanup_result(resp):
      res = DynObject()
      if resp.code == "done":
        res.valid = True
        res.value = resp.value
      else:
        res.valid = False
        res.error = resp.msg
      cb(res)
    w = self._run_cmd_async_with_waitable(cmd,cleanup_result)
    return w
