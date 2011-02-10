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

import sys
import os
import exceptions
import subprocess
import shlex

import ndbg
from util import *

class MainControlLauncher(dbus.service.Object):
  def __init__(self, mcs, launch_cmd):
    dbus.service.Object.__init__(self, dbus.SessionBus(), "/Launcher")

    self._mcs = mcs # maincontrols, remoted
    self._launch_cmd = launch_cmd # launch args, either ExecAttach or ExecLaunch
    self._raw_proc = None
    self._launchable_processes = []
    self._passive_processes = []
    MessageLoop.add_keyboard_interrupt_hook(self._on_keyboard_interrtupt)
    MessageLoop.add_quit_hook(self._on_quit)

    MessageLoop.add_delayed_message(self._on_timeout, 5000)

    # phase 1, send a bunch of shit to all the mc's saying "blahblah wants to do blah blah"
    if hasattr(self._launch_cmd,'ExecLaunch'):
      self._add_launchable_process_to_mcs()
    elif hasattr(self._launch_cmd,'ExecAttach'):
      self._add_passive_process_to_mcs(self._launch_cmd.ExecAttach,False)
      MessageLoop.add_delayed_message(self._check_proc_is_alive, 250)
    else:
      raise Exception("This can't happen")

  @property
  def _proc(self):
    return self._raw_proc
  @_proc.setter
  def _proc(self,proc):
    self._raw_proc = proc
    if proc:
      MessageLoop.add_delayed_message(self._check_proc_is_alive, 250)

  @dbus.service.method(dbus_interface="ndbg.Launcher")
  def get_pid(self):
    return os.getpid()


  # state 1: waiting for someone to launch
  ###########################################################################
  def _add_launchable_process_to_mcs(self):
    """Put up launchable process into all of the debuggers."""
    for mc in self._mcs:
      proc = DynObject()
      proc.mc = mc
      proc.id = mc.add_launchable_process(self._launch_cmd.ExecLaunch)
      self._launchable_processes.append(proc)
      log2("DLaunchableProcess %s opened on %s", proc.id, mc)

  @dbus.service.method(dbus_interface="ndbg.Launcher")
  def on_accept_launch(self, proc_id):
    proc = remove_first(self._launchable_processes, lambda proc: proc.id == proc_id)
    log1("%s accepted: ",  proc.mc)

    # remove other launchable processes
    for p2 in self._launchable_processes:
      p2.mc.remove_launchable_process(p2.id)
    del self._launchable_processes[:]

    # launch the process
    launcher_exe = os.path.abspath(os.path.join(ndbg.get_basedir(), "launcher/ndbg_launcher"))
    if os.path.exists(launcher_exe):
      self._proc = subprocess.Popen([launcher_exe] + self._launch_cmd.ExecLaunch)
    else:
      print "Could not find ndbg_launcher binary. It should be in $NDBG_DIR/launcher, but you have to compile it first!"
      print "ndbg_in_existing will still work, but will not be able to debug startup."
      self._proc = subprocess.Popen(self._launch_cmd.ExecLaunch)
    log2("Launched locally as pid=%i", self._proc.pid)
    def send_launch_complete():
      proc.mc.attach_to_launched_pid(self._proc.pid)
    MessageLoop.add_message(send_launch_complete)

  @dbus.service.method(dbus_interface="ndbg.Launcher")
  def on_ignore_launch(self, proc_id):
    log1("LaunchableProcess ignored by %s" % proc_id)
    remove_first(self._launchable_processes, lambda proc: proc.id == proc_id)
    if len(self._open_bars) == 0 and self._proc == None:
      MessageLoop.add_message(self._on_all_mcs_ignore_launchable)

  @dbus.service.method(dbus_interface="ndbg.Launcher")
  def on_kill_launch(self, proc_id):
    log1("LaunchableProcess killed by %s" % proc_id)
    remove_first(self._launchable_processes, lambda proc: proc.id == proc_id)
    for proc in self._launchable_processes:
      proc.mc.remove_launchable_process(proc.id)
    MessageLoop.quit()

  # state 1.5a: no process running, all debuggers ignored
  ###########################################################################
  def _on_all_mcs_ignore_launchable(self):
    log1("All LaunchableProcesses were ignored.")

    self._proc = subprocess.Popen(self._launch_cmd.ExecLaunch)
    log2("Launched locally as pid=%i", self._proc.pid)

    self._add_passive_process_to_mcs(self._proc.pid, True)

  # state 1.5b: no process running, timeout happened before any user action.
  ###########################################################################
  def _on_timeout(self):
    if self._proc:
      return

    """Called by MessageLoop when 5 seconds elapse without a GUI responding"""
    print "ndbg: Timed out waiting for ndbg GUI to pick process."
    print "ndbg: Directly launching: %s" % self._launch_cmd.ExecLaunch

    for proc in self._launchable_processes:
      proc.mc.remove_launchable_process(proc.id)

    args=self._launch_cmd.ExecLaunch
    self._proc = subprocess.Popen(args)
    log2("Process started locally as %i", self._proc.pid)

    self._add_passive_process_to_mcs(self._proc.pid,True)


  # state 2: process running
  ###########################################################################
  def _add_passive_process_to_mcs(self, pid, was_launched):
    """Put a passive process into all the debuggers"""
    for mc in self._mcs:
      proc = DynObject()
      proc.mc = mc
      proc.id = mc.add_passive_process(pid, was_launched)
      self._passive_processes.append(proc)
      log2("DPassiveProcess %s opened on %s", proc.id, mc)

  @dbus.service.method(dbus_interface="ndbg.Launcher")
  def notify_of_attach(self, proc_id):
    proc = find_first(self._open_bars, lambda proc: b.id == proc_id)
    log1("%s attached to %s: ",  proc.mc, proc_id)
    for proc in self._passive_processes:
      proc.mc.remove_passive_process(proc)

  # general infrastructural crap
  ###########################################################################
  def _check_proc_is_alive(self):
    if self._proc:
      res = self._proc.poll()
      if res:
        log2("Process %s exited with %i", self._proc.pid, res)
        self._proc = None
        MessageLoop.quit()
      else:
        return True
    elif self._launch_cmd.ExecAttach:
      alive = ProcessUtils.is_proc_alive(self._launch_cmd.ExecAttach)
      if not alive:
        log2("Process %s exited with %i", self._proc.pid, res)
        MessageLoop.quit()
      else:
        return True

  def _on_quit(self):
    pass

  def _on_keyboard_interrtupt(self):
    if self._proc and self._proc.poll() == None:
      log1("Killing proc")
      self._proc.kill()

