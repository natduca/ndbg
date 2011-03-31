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
###########################################################################

# This module is responsible for creating the overall debugger controls
# as well as setting up the UI's basic tabbed interface.
#
# Its additions are managed by the debug_overlay object, which contains all the
# MainWindow additions relating to debugger control.
import pygtk
pygtk.require('2.0')
import gtk
import os.path
import code
import exceptions
import sys

import dbus
import dbus.service

from util import *

from main_window import MainWindow
from resources import Resources

from call_stack_tab import CallStackTab
from thread_tab import ThreadTab
from process_tab import ProcessTab
from breakpoint_tab import *
from breakpoint_persistence_manager import *
from stack_explorer import StackExplorer
from output_tab import OutputTab
from interactive_tab import InteractiveTab
from python_tab import PythonTab
from attach_to_process_dialog import AttachToProcessDialog
from butter_bar import *
from main_options_dialog import *

from debugger import *

UI_STATUS_NOT_DEBUGGING = 'UI Status Not Debugging'
UI_STATUS_BREAK = 'UI Status Break'
UI_STATUS_RUNNING = 'UI Status Running'

UI_LAYOUT_EDIT = "UIEditMode"
UI_LAYOUT_RUN  = "UIRunMode"


class MainControl(dbus.service.Object):
  mw = property(lambda self: self._mw)
  always_overlay = property(lambda self: self._always_overlay)
  when_not_debugging_overlay = property(lambda self: self._when_not_debugging_overlay)
  when_debugging_overlay = property(lambda self: self._when_debugging_overlay)
  when_break_overlay = property(lambda self: self._when_break_overlay)
  when_running_overlay = property(lambda self: self._when_running_overlay)
  debugger = property(lambda self: self._debugger)
  editor = property(lambda self: self._editor)
  filemanager = property(lambda self: self._filemanager)
  resources = property(lambda self: self._mw.resources)
  settings = property(lambda self: self._settings)
  butter_bar_collection = property(lambda self: self._mw.butter_bar_collection)

  def new_overlay(self,name):
    return self._mw.new_overlay(name)

  def __init__(self, settings, mw):
    self._settings = settings
    self._mw = mw

    self._registered_process = RegisteredProcess()
    dbus.service.Object.__init__(self, dbus.SessionBus(), "/MainControl")

    self._mw.connect('show', self._on_show)
    self._when_running_overlay = self.new_overlay("Run only overlay")
    self._when_break_overlay = self.new_overlay("Break only overlay")
    self._when_not_debugging_overlay = self.new_overlay("Not debugging overlay")
    self._when_debugging_overlay = self.new_overlay("Debugging only overlay")
    self._always_overlay = self.new_overlay("Always-on overlay")

    self._debugger = Debugger()

    self._filemanager = FileManager(self.settings, self.debugger)

    assert self.ui_status == UI_STATUS_NOT_DEBUGGING
    self._mw.layout = UI_LAYOUT_EDIT

    self._init_launcher()
    self._init_bbar_system()

    # center stage setup... this doesn't go through an overlay yet, sigh
    if self.settings.Editor == "SourceViewEditor":
      log1("Initializing SourceViewEditor")
      sourceviewmodule = __import__("ui.source_view_editor",fromlist=[True])
      editor = sourceviewmodule.SourceViewEditor(self)
    elif self.settings.Editor == "GVimEditor":
      log1("Initializing GVimEditor")
      gvimeditormodule = __import__("ui.gvim_editor",fromlist=[True])
      editor = gvimeditormodule.GVimEditor(self)
    elif self.settings.Editor == "EmacsEditor":
      log1("Initializing EmacsEditor")
      emacseditormodule = __import__("ui.emacs_editor",fromlist=[True])
      editor = emacseditormodule.EmacsEditor(self)
    else:
      raise Exception("~/.ndbg : Editor=%s is not one of the recognieed settings." % self.settings.Editor)
    mw.add_center_stage(editor.widget)
    self._editor = editor
    self._always_overlay.add_tabs_menu_item("tabs.editor", lambda x,y: self.focus_editor())


    # persistence managers
    ###########################################################################
    bpm = BreakpointPersistenceManager(self)
    self._bpm = bpm

    # tabs and overlay setup
    ###########################################################################
    cs = CallStackTab(self)
    self._when_break_overlay.add_tab(cs,"tabpage.call_stack")
    self._when_break_overlay.add_tabs_menu_item("tabs.call_stack", lambda x,y: self._focus_tab(cs)),

    ot = OutputTab(self)
    self._always_overlay.add_tab(ot,"tabpage.output")
    self._always_overlay.add_tabs_menu_item("tabs.output", lambda x,y: self._focus_tab(ot))

    bt = BreakpointTab(self)
    self._always_overlay.add_tab(bt,"tabpage.breakpoints")
    self._always_overlay.add_tabs_menu_item("tabs.breakpoints", lambda x,y: self._focus_tab(bt)),

#    sx = StackExplorer(self)
#    self._when_break_overlay.add_tab(sx)

    tt = ThreadTab(self)
    self._when_break_overlay.add_tab(tt,"tabpage.threads")
    self._when_break_overlay.add_tabs_menu_item("tabs.threads", lambda x,y: self._focus_tab(tt)),

    pt = ProcessTab(self)
    self._when_debugging_overlay.add_tab(pt,"tabpage.processes")
    self._when_debugging_overlay.add_tabs_menu_item("tabs.processes", lambda x,y: self._focus_tab(pt))

    it = InteractiveTab(self)
    self._when_break_overlay.add_tab(it,"tabpage.interactive")
    def focus_interactive_tab():
      self._focus_tab(it)
      it.focus_entry()
    self._when_break_overlay.add_tabs_menu_item("tabs.interactive", lambda x,y: focus_interactive_tab())

    pyt = PythonTab(self)
    self._always_overlay.add_tab(pyt,"tabpage.python")
    def focus_python_tab():
      self._focus_tab(pyt)
      pyt.focus_entry()
    self._always_overlay.add_tabs_menu_item("tabs.python", lambda x,y: focus_python_tab())
    self._always_overlay.add_tools_menu_item('tools.options', self._on_tools_options_clicked)


    # debug menu items
    self._when_running_overlay.add_debug_menu_item("debug.break", self._on_break)

    self._when_break_overlay.add_debug_menu_item('debug.step_over', self._on_step_over)
    self._when_break_overlay.add_debug_menu_item('debug.step_into', self._on_step_into)
    self._when_break_overlay.add_debug_menu_item('debug.step_out',  self._on_step_out)
    self._when_break_overlay.add_debug_menu_item('debug.continue',  self._on_continue)

    self._always_overlay.add_debug_menu_item('debug.launch_process', lambda *args: self._launch_process())
    self._always_overlay.add_debug_menu_item('debug.attach_to_process', lambda *args: self._attach_to_pids())

    self._when_debugging_overlay.add_debug_menu_item('debug.end_debugging', self._end_debugging)

    # previous debugging
    settings.register("RunPrimaryExecutableMode", str, "active")
    self._when_not_debugging_overlay.add_debug_menu_item('debug.run_primary_executable', lambda *args: self._run_primary_executable())
    self._when_not_debugging_overlay.add_debug_menu_item('debug.run_primary_executable_suspended', lambda *args: self._run_primary_executable_suspended())

    self._primary_executable = None

    # event listening
    self._previous_ui_status = self.ui_status
    self._widget_that_had_focus = { UI_STATUS_NOT_DEBUGGING: None, UI_STATUS_BREAK: None, UI_STATUS_RUNNING: None }
    self._debugger.status_changed.add_listener(self._on_status_changed)
    self._debugger.passive_processes.changed.add_listener(lambda: self._update_title())

    # get it going
    mw.show()
    self._update_title()
    self._debugger.fire_all_listeners()

    for panel in mw.panels.values():
      self.resources.apply_small_fontsize(panel)

    # apply fontsize tweak
    for ovl in mw.overlays:
      for tab in ovl.tabs:
        self.resources.apply_small_fontsize(tab)

  def _on_tools_options_clicked(self,*args):
    dlg = MainOptionsDialog(self.settings)
    if self._primary_executable:
      dlg.primary_executable = self._primary_executable
    res = dlg.run()
    if res == gtk.RESPONSE_OK:
      changed =  ProcessUtils.shlex_join(self._primary_executable) != ProcessUtils.shlex_join(dlg.primary_executable)
      if changed and self.debugger.num_processes_of_all_types != 0:
        b = ButterBar("Changes to primary exectuable arguments will not take effect until you end debugging.")
        b.set_stock_icon(gtk.STOCK_DIALOG_WARNING)
        def on_restart():
          suspended = self.debugger.status == STATUS_BREAK
          self._end_debugging()
          self._run_primary_executable(suspended)
        b.add_button("Re-run program", on_restart)
        b.add_close_button()
        self.butter_bar_collection.add_bar(b)

      self._primary_executable = dlg.primary_executable
      self._on_status_changed()

  def D(self):
    import debugger.gdb_backend
    debugger.gdb_backend.gdb_toggle_enable_debug_window()

  def focus_editor(self):
    if hasattr(self._editor,'grab_focus'):
      log1("Focusing Editor via editor.grab_focus")
      self._editor.grab_focus()
    else:
      log1("Focusing Editor via editor.widget.grab_focus")
      self._editor.widget.grab_focus()

  def _on_load(self):
    log1("Main control: processing command line arguments...")
    if self._settings.ExecLaunch != None:
      self._primary_executable = self._settings.ExecLaunch
      self._run_primary_executable(suspended=True)
    elif self._settings.ExecAttach != -1:
      self._attach_to_pids([self._settings.ExecAttach])

  def _on_show(self,*args):
    log2("Main control: window shown, scheduling load in 200ms")
    glib.timeout_add(200, self._on_load)

  def _end_debugging(self,*args):
    for proc in list(self.debugger.launchable_processes):
      proc.end_debugging()
    for proc in list(self.debugger.passive_processes):
      if proc.was_launched:
        proc.kill()
      else:
        proc.detach()
    if self._debugger.status == STATUS_RUNNING:
      self._debugger.begin_interrupt().wait()
    procs = list(self._debugger.processes) # copy it 'cause we're about to muck around
    for proc in procs:
      if proc.was_launched:
        proc.kill()
      else:
        proc.detach()

  def _run_primary_executable(self, suspended = False):
    if self.settings.RunPrimaryExecutableMode == "active":
      self._run_primary_executable_active(suspended)
    elif self.settings.RunPrimaryExecutableMode == "passive":
      self._run_primary_executable_passive()
    else:
      raise Exception("Unrecognized rerun mode.")

  def _run_primary_executable_suspended(self):
    if self.settings.RunPrimaryExecutableMode == "active":
      self._run_primary_executable_active(True)
    elif self.settings.RunPrimaryExecutableMode == "passive":
      b = ButterBar("You have passive debugging selected. Debugging process anyway...")
      b.set_stock_icon(gtk.STOCK_DIALOG_INFO)
      b.add_close_button()
      self.butter_bar_collection.add_bar(b)
      def autoclose():
        if b.get_parent():
          self.butter_bar_collection.close_bar(b)
      MessageLoop.add_delayed_message(autoclose, 5000)
      self._run_primary_executable_active(True)
    else:
      raise Exception("Unrecognized rerun mode.")

  def _run_primary_executable_active(self,suspended = False):
    if self._primary_executable:
      self.find_tab(OutputTab).on_rerun()
      self._launch_process(self._primary_executable,suspended = suspended)
    else:
      self._launch_process(suspended = True) # prompt for program...

  def _run_primary_executable_passive(self):
    if self._primary_executable:
      args=self._primary_executable
      log2("Launching %s", args)
      sub = subprocess.Popen(args)
      proc = DPassiveProcess(sub, was_launched=True)
      self.debugger.passive_processes.append(proc)
      self._rerun_passive_process = proc

  def destroy(self):
    self._end_debugging()

    log2("Shutting down editor")
    self._editor.destroy()
    log2("Shutting down mw")
    self._mw.destroy()
    log2("Shutting down debugger")
    self._debugger.shutdown()
    log2("Destroying filemanager")
    self._filemanager.shutdown()
    log2("Destroy complete")
    self._registered_process = None

  def _launch_process(self,launch_args = None, suspended = True):
    if launch_args == None:
      dlg = gtk.Dialog("Launch process",
                       None,
                       gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                       (gtk.STOCK_OK,gtk.RESPONSE_OK,
                        gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
      hbox = gtk.HBox()
      label = gtk.Label("Command line:")
      entry = gtk.Entry()
      entry.set_size_request(400,-1)
      entry.set_activates_default(True)
      hbox.pack_start(label,False,False,4)
      hbox.pack_start(entry,True,True,0)
      hbox.show_all()
      dlg.get_content_area().pack_start(hbox,False,False,0)
      dlg.set_default_response(gtk.RESPONSE_OK)
      resp = dlg.run()
      dlg.hide()
      if resp != gtk.RESPONSE_OK or entry.get_text() == "":
        return
      launch_args = shlex.split(entry.get_text())

    # do launch
    self._focus_tab(self.find_tab(OutputTab))
    status_dlg = StatusDialog("Status")
    was_running = self.debugger.status == STATUS_RUNNING
    if was_running:
      status_dlg.status = "Stopping other processes..."
      self.debugger.begin_interrupt().wait()

    self._primary_executable = launch_args
    status_dlg.status = "Beginning launch..."
    launch_done = self.debugger.begin_launch_suspended(launch_args)
    status_dlg.status = "Loading symbols..."
    def on_done(proc):
      log2("Launch Done")
      status_dlg.destroy_please()
      if was_running or suspended == False:
        assert self.debugger.status == STATUS_BREAK
        self.debugger.active_thread.begin_resume()
    launch_done.when_done(on_done)

  def get_hidden_pids(self):
    hidden_pids = []
    # ui
    hidden_pids += [os.getpid()]

    # debuggers
    hidden_pids += [backend.debugger_pid for backend in self.debugger._backends if backend.debugger_pid]

    # currently attached processes
    hidden_pids += [proc.backend_info.pid for proc in self.debugger.processes if proc.backend_info]

    return hidden_pids

  def _attach_to_pids(self,pids = []):
    if type(pids) != list:
      raise "Expected pids to be a list"
    if len(pids) == 0:
      hidden_pids = self.get_hidden_pids()
      dlg = AttachToProcessDialog(self._settings, hidden_pids)
      resp = dlg.run()
      dlg.hide()
      if resp != gtk.RESPONSE_OK:
        return
      pids = dlg.selected_pids

    if len(pids) == 0:
      raise Exception("pids should be nonzero in length.")

    self._focus_tab(self.find_tab(OutputTab))
    status_dlg = StatusDialog("Debugger Status")

    was_running = self.debugger.status == STATUS_RUNNING
    if was_running:
      status_dlg.status =  "Stopping other processes..."
      self.debugger.begin_interrupt().wait()

    try:
      cmdline = ProcessUtils.get_pid_full_cmdline(pids[0])
      status_dlg.status =  "Attaching to pid %s:\n%s" % (pids[0], cmdline)
    except Exception, ex:
      status_dlg.status =  "Attaching to process #%s" % pids[0]

    pid_attached = self.debugger.begin_attach_to_pid(pids[0])
    def do_next_pid(proc):
      del pids[0]
      if len(pids) == 0:
        log2("no more pids")
        status_dlg.hide()
        if was_running:
          self.debugger.active_thread.begin_resume()
      else:
        try:
          cmdline = ProcessUtils.get_pid_full_cmdline(pids[0])
          status_dlg.status =  "Attaching to pid %s:\n%s" % (pids[0], cmdline)
        except Exception, ex:
          status_dlg.status =  "Attaching to process #%s" % pids[0]
        pid_attached = self.debugger.begin_attach_to_pid(pids[0])
        pid_attached.when_done(do_next_pid)
    pid_attached.when_done(do_next_pid)

  def find_tab_by_id(self,tab_id):
    for ovl in self._mw.overlays:
      t = ovl.find_tab_by_id(tab_id)
      if t:
        return t
    return None

  def find_tab(self,tabType):
    for ovl in self._mw.overlays:
      t = ovl.find_tab(tabType)
      if t:
        return t
    return None

  def _focus_tab(self,tab):
    book = tab.get_parent()
    book_pages = book.get_children()
    for i in range(0,len(book_pages)):
      if book_pages[i] == tab:
        book.set_current_page(i)

    if hasattr(tab, 'special_grab_focus'):
      tab.special_grab_focus()
      return

    firstChild = tab.get_children()[0]
    if type(firstChild) == gtk.ScrolledWindow:
      target = firstChild.get_children()[0]
      target.grab_focus()
    else:
      firstChild.grab_focus()


  def focus_location(self,l):
    self._editor.focus_location(l)
    self.focus_editor()

  def _on_break(self,*args):
    self.debugger.begin_interrupt()

  def _on_continue(self,*args):
    self.debugger.active_thread.begin_resume()

  def _on_step_into(self,*args):
    assert(self.debugger.status == STATUS_BREAK)
    self.debugger.active_thread.begin_step_into()

  def _on_step_over(self,*args):
    assert(self.debugger.status == STATUS_BREAK)
    self.debugger.active_thread.begin_step_over()

  def _on_step_out(self,*args):
    assert(self.debugger.status == STATUS_BREAK)
    self.debugger.active_thread.begin_step_out()

  ###########################################################################

  def _on_status_changed(self):
    self._update_title()
    self._update_overlays()

  def _update_title(self):
    debugger = self.debugger
    name = None
    if len(debugger.processes):
      assert len(debugger.processes) != 0
      assert debugger.first_added_process != None
      first_valid_name = None
      n_others = 0
      for proc in debugger.processes:
        if proc.backend_info:
          if not first_valid_name:
            first_valid_name = os.path.basename(proc.target_exe)
          else:
            n_others += 1
      if n_others > 0:
        name = "%s (+%i more)" % (first_valid_name, n_others)
      elif first_valid_name:
        name = first_valid_name
      else:
        name = None
    else:
      if self._primary_executable:
        app = self._primary_executable[0]
        name = os.path.basename(app)
      else:
        name = None

    import ndbg
    if ndbg.is_debug_python_runtime():
      prefix = "%i - " % os.getpid()
    else:
      prefix = ""

    if self.debugger.status == STATUS_RUNNING:
      self.mw.set_title("%sNicer Debugger - %s [Running]" % (prefix, name))
    else:
      if len(self.debugger.processes):
        self.mw.set_title("%sNicer Debugger - %s [Stopped]" % (prefix, name))
      else:
        if len(self.debugger.passive_processes):
          substat = "Background processes running";
        else:
          substat = "Not debugging";

        if name:
          self.mw.set_title("%sNicer Debugger - %s [%s]" % (prefix, name, substat))
        else:
          self.mw.set_title("%sNicer Debugger - [%s]" % (prefix, substat))

  @property
  def ui_status(self):
    if self.debugger.status == STATUS_RUNNING:
      return UI_STATUS_RUNNING
    else:
      if self._debugger.num_processes_of_all_types:
        return UI_STATUS_BREAK
      else:
        return UI_STATUS_NOT_DEBUGGING

  def _update_overlays(self):
    if self._previous_ui_status != self.ui_status:
      self._widget_that_had_focus[self._previous_ui_status] = self._mw.get_focus()

    if self.ui_status == UI_STATUS_RUNNING:
      self._when_not_debugging_overlay.visible = False
      self._when_debugging_overlay.visible = True
      self._when_running_overlay.visible = True
      self._when_break_overlay.visible = True
      self._when_break_overlay.enabled = False
    elif self.ui_status == UI_STATUS_BREAK:
      self._when_not_debugging_overlay.visible = False
      self._when_debugging_overlay.visible = True
      self._when_running_overlay.visible = False
      self._when_break_overlay.visible = True
      self._when_break_overlay.enabled = True
    else:
      assert self.ui_status == UI_STATUS_NOT_DEBUGGING
      self._when_not_debugging_overlay.visible = True
      self._when_debugging_overlay.visible = False
      self._when_running_overlay.visible = False
      self._when_break_overlay.visible = False

    if self.ui_status == UI_STATUS_NOT_DEBUGGING:
      self._mw.layout = UI_LAYOUT_EDIT
    else:
      self._mw.layout = UI_LAYOUT_RUN

    if self._previous_ui_status != self.ui_status:
      if self._widget_that_had_focus[self.ui_status] != None:
        self._widget_that_had_focus[self.ui_status].grab_focus()
      # set mainwindow layout to the new mode...

    self._previous_ui_status = self.ui_status

  # bbar system puts up butterbars for passive and launchable processes
  ###########################################################################
  def _init_bbar_system(self):
    self._butter_bars_by_process = {}

  def _on_launchable_process_added(self, idx, proc):
    # create butter bar, keep it up until the process is gone
    b = ButterBar("Request to launch a new process: %s" % " ".join(proc.target_full_cmdline))
    b.set_stock_icon(gtk.STOCK_DIALOG_INFO)
    def on_accept():
      proc.launch()

    def on_ignore():
      proc.ignore_launch()

    b.add_button("_Accept and Launch", on_accept)
    b.add_button("_Ignore", on_ignore)
    b.add_close_button(on_ignore)
    self._butter_bars_by_process[proc] = b
    self.butter_bar_collection.add_bar(b)

  def _on_launchable_process_deleted(self, idx, proc):
    if self._butter_bars_by_process.has_key(proc):
      b = self._butter_bars_by_process[proc]
      self.butter_bar_collection.close_bar(b)
      del self._butter_bars_by_process[proc]

  def _on_passive_process_added(self, idx, proc):
    # create butter bar, but set timeout to remove it in 5 seconds
    cmdline = proc.target_full_cmdline
    if cmdline:
      title = "Process %i is running: %s" % (proc.pid, " ".join(cmdline))
    else:
      title = "Process %i is running" % (proc.pid)

    b = ButterBar(title)
    b.set_stock_icon(gtk.STOCK_DIALOG_INFO)
    def on_accept():
      proc.attach()

    def on_ignore_or_timeout():
      if not self._butter_bars_by_process.has_key(proc):
        return
      self.butter_bar_collection.close_bar(b)
      del self._butter_bars_by_process[proc]

    MessageLoop.add_delayed_message(on_ignore_or_timeout, 5000)

    b.add_button("_Attach", on_accept)
    b.add_button("_Ignore", on_ignore_or_timeout)
    b.add_close_button(on_ignore_or_timeout)

    self._butter_bars_by_process[proc] = b
    self.butter_bar_collection.add_bar(b)
    self._on_status_changed()


  def _on_passive_process_deleted(self, idx, proc):
    log2("passive process deleted %s", proc);
    if self._butter_bars_by_process.has_key(proc):
      b = self._butter_bars_by_process[proc]
      self.butter_bar_collection.close_bar(b)
      del self._butter_bars_by_process[proc]

    # pass message down to launcher, which needs to know this too
    self._launcher_on_passive_process_deleted(proc)
    self._on_status_changed()

  # backend control for ndbg -e flow
  ###########################################################################
  @staticmethod
  def get_all_remote_instances():
    """Presents user with a list of MainControl's that are running, and lets them pick one."""
    remote_dbus_names = RegisteredProcess.find_registered_dbus_names()
    bus = dbus.SessionBus()
    log1("Found existing processes: %s", remote_dbus_names)
    mcs = [bus.get_object(remote_bus_name, "/MainControl") for remote_bus_name in remote_dbus_names]
    return mcs

  @dbus.service.method(dbus_interface='ndbg.MainControl')
  def get_title(self):
    return self._mw.get_title()

  def _init_launcher(self):
    self._debugger.launchable_processes.item_added.add_listener(self._on_launchable_process_added)
    self._debugger.launchable_processes.item_deleted.add_listener(self._on_launchable_process_deleted)
    self._debugger.passive_processes.item_added.add_listener(self._on_passive_process_added)
    self._debugger.passive_processes.item_deleted.add_listener(self._on_passive_process_deleted)

    self._next_launcher_id = 0
    self._launchable_processes_by_launcher_id = {}
    self._passive_processes_by_launcher_id = {}

  @dbus.service.method(dbus_interface='ndbg.MainControl', sender_keyword="sender")
  def add_launchable_process(self, cmdline, sender):
    launcher = dbus.SessionBus().get_object(sender, "/Launcher")

    cmdline = [str(x) for x in cmdline]

    id = self._next_launcher_id
    id = "%s/%s" % (dbus.SessionBus().get_unique_name(), self._next_launcher_id)
    self._next_launcher_id += 1

    log1("Add launchable process for %s", cmdline)
    def on_launch():
      launcher.on_accept_launch(id)
      del self._launchable_processes_by_launcher_id[id]
    def on_ignore_launch():
      launcher.on_ignore_launch(id)
    def on_detach():
      launcher.on_kill_launch(id)

    proc = DLaunchableProcess(cmdline, on_launch, on_ignore_launch, on_detach)
    self._debugger.launchable_processes.append(proc)

    # watch the launcher --- if it disappears, remove this launchable process
    launcher_pid = BoxedObject()
    def check_launcher_aliveness():
      if launcher_pid.get() == None:
        print "getting launcher pid"
        launcher_pid.set(launcher.get_pid())
        MessageLoop.add_delayed_message(check_launcher_aliveness, 250)

      if not self._launchable_processes_by_launcher_id.has_key(id):
        return False

      if not ProcessUtils.is_proc_alive(launcher_pid.get()):
        log1("Launchable process host %s gone. Removing launched process.", id)
        del self._launchable_processes_by_launcher_id[id]
        if proc in self._debugger.launchable_processes:
          self._debugger.launchable_processes.remove(proc)
        return False
      return True
    MessageLoop.add_message(check_launcher_aliveness)

    # return the id of this process
    log1("Added launchable process %s", id)
    self._launchable_processes_by_launcher_id[id] = proc
    return id

  @dbus.service.method(dbus_interface='ndbg.MainControl')
  def attach_to_launched_pid(self, launched_pid):
    launched_pid = int(launched_pid)
    log1("on_accept_launch_complete(%i)", launched_pid);
    self._attach_to_pids([launched_pid])


  @dbus.service.method(dbus_interface='ndbg.MainControl', sender_keyword="sender")
  def remove_launchable_process(self, id, sender):
    log1("Remove launchable process %s", id)
    proc = self._launchable_processes_by_launcher_id[id]
    del self._launchable_processes_by_launcher_id[id]
    if proc in self.debugger.launchable_processes:
      self.debugger.launchable_processes.remove(proc)

  @dbus.service.method(dbus_interface='ndbg.MainControl', sender_keyword="sender")
  def add_passive_process(self, pid, was_launched, sender):
    launcher = dbus.SessionBus().get_object(sender, "/Launcher")

    pid = int(pid)
    id = "%s/%s" % (dbus.SessionBus().get_unique_name(), self._next_launcher_id)
    self._next_launcher_id += 1

    log1("Add passive process for %i", pid)
    def on_attach():
      launcher.notify_of_attach(id)
    proc = DPassiveProcess(pid, on_attach, was_launched)
    self.debugger.passive_processes.append(proc)
    self._passive_processes_by_launcher_id[id] = proc

    return id

  def _launcher_on_passive_process_deleted(self, proc):
    for id in self._passive_processes_by_launcher_id:
      if self._passive_processes_by_launcher_id[id] == proc:
        del self._passive_processes_by_launcher_id[id]
        break

  @dbus.service.method(dbus_interface='ndbg.MainControl')
  def remove_passive_process(self, id):
    proc = self._passive_processes_by_launcher_id[id]
    self._debugger.passive_processes.remove(proc)
