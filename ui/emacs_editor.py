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
import gtk
import vte
import sys
import pty
import os
import shlex
import subprocess
import tempfile
import time
import ui

from editor_base import *
from butter_bar import *

def _is_child_of(w,parent):
  cur = w
  while cur:
    if cur == parent:
      return True
    cur = cur.get_property('parent')
  return False


# This class implements EditorBase via emacs using a gtksocket
class EmacsEditor(EditorBase):
  def __init__(self, mc):
    EditorBase.__init__(self, mc)

    mc.settings.register("EmacsEditorFirstRun", bool, True)
    if mc.settings.EmacsEditorFirstRun:
      mc.settings.EmacsEditorFirstRun = False
      b = ButterBar("nDBG's emacs mode has a few quirks that you might want to know about...")
      b.set_stock_icon(gtk.STOCK_DIALOG_INFO)
      b.add_button("Tell me more...", self._on_more_emacs_information)
      b.add_close_button()
      mc.butter_bar_collection.add_bar(b)


    self._pending_cmds = []
    self._emacs = None # subprocess.Popen object for the emacs process
    self._emacs_socket_name = None # the unix socket used to talk to emacs, will be set up in _determine_socket_name
    self._socket = gtk.Socket()
    ed = self

    class MyEBox(gtk.EventBox):
      def __init__(self):
        gtk.EventBox.__init__(self)
      def grab_focus(self):
        # workaround: focus something else
        mc.mw.panels.values()[0].grab_focus()
        # focus the socket
        ed._socket.child_focus(gtk.DIR_TAB_FORWARD)
    self._ebox = MyEBox()
    self._ebox.add(self._socket)
    self._ebox.show_all()

    self._ebox.add_events(gtk.gdk.ALL_EVENTS_MASK)

    self._ebox.connect('realize', self.on_realize)

    self._buffers = {}
    self.mc.mw.menu_bar.connect('deactivate', self._on_menu_deactivate)

  def _on_more_emacs_information(self):
    msg = """
Great to see you've chosen to use Emacs for your text editor.

Due to bugs in GtkSocket and Emacs' plug implementation,
Emacs will sometimes think it does not have keyboard focus.
It will still recieve and process key presses, but the
 cursor will be hollow, i.e. as if the window wasn't focused.

Yuck!

As a nDBG user, you have two options:
1. Help us figure out why that happens! ;)
2. Press Control-Alt k. This will focus Emacs again.

"""
    def doit():
      dlg = gtk.MessageDialog(buttons=gtk.BUTTONS_OK, message_format=msg)
      dlg.run()
      dlg.destroy()
    MessageLoop.add_delayed_message(doit, 30)

  def _on_menu_deactivate(self,*args):
    MessageLoop.add_delayed_message(lambda: self.grab_focus(), 25)

  def _install_mw_hooks_to_handle_emacs_suckage(self):
    # The following goo restores the editor widget focus when the
    # window focus is restored with the mouse over emacs. In that
    # case, emacs gets into a wierd half-focused state where Gtk
    # thinks it is focused, but emacs itself doesn't. To fix this
    # situation, we need to UNFOCUS the socket, which emacs
    # understands, then re-focus it again.  Moreover, we can't do it
    # immediately --- since we're in a focusing callback when we
    # detect this, we have to defer the fixup a bit. So, we post a
    # message to fix the focusing.  Absolute insanity.
    w = self._ebox.get_toplevel()
    assert w
    cstage_was_last_focused = BoxedObject(False)
    def on_focus_in(*args):

      if cstage_was_last_focused.get():
#        print "Focus-focusing emacs"
        MessageLoop.add_message(lambda: w.panels.values()[0].grab_focus())
        MessageLoop.add_message(lambda: self.grab_focus())

    def on_focus_out(*args):
      # this is the window losing focus
      if _is_child_of(self._ebox.get_toplevel().get_focus(),self._socket):
#        print "Lost focus, but cstage had focus."
        cstage_was_last_focused.set(True)
      else:
        cstage_was_last_focused.set(False)


    w.connect('focus-in-event', on_focus_in)
    w.connect('focus-out-event', on_focus_out)

  def grab_focus(self):
    self._ebox.grab_focus()

  def _determine_socket_name(self):
    template = "/tmp/ndbg/emacs%i"
    i = 0
    while True:
      i += 1
      candidate_name = template % i
      log1("Socket candidate: %s" % candidate_name)
      # if the file doesn't even exist, we're good
      if os.path.exists(candidate_name) == False:
        log1("Socket candidate found.")
        self._emacs_socket_name = candidate_name
        return

      # skip if this is a directory
      if os.path.isdir(candidate_name):
        log1("Skipping, is directory")
        continue

      # try talking to the socket, maybe there isn't an emacs there anymore
      self._emacs_socket_name = candidate_name # temporarily set this, so remote_run works
      res = self.remote_run("-e '(+ 1 1)'")
      self._emacs_socket_name = None # unset the temporary set done above

      if re.search("connect: Connection refused", res):
        log1("Connection refused. This socket is safe to use.")
        try:
          os.unlink(candidate_name)
        except OSError:
          log1("Failed to unlink existing socket.")
          if os.path.exists(candidate_name):
            log1("Somethign is strange. Will not use this as a socket.")
            continue
        self._emacs_socket_name = candidate_name
        return
      else:
        log1("An emacs is running o06n this socket already.")
        continue



  def on_realize(self, *kw):

    self._determine_socket_name()

    bootstrap_file = tempfile.NamedTemporaryFile(delete=False)# open(f.name, "w")
    bootstrap_file.write("""(progn\n""")
    sock_dir = os.path.dirname(self._emacs_socket_name)
    sock_name = os.path.basename(self._emacs_socket_name)
    bootstrap_file.write("""  (setq server-socket-dir "%s")\n""" % sock_dir)
    bootstrap_file.write("""  (setq server-name "%s")\n""" % sock_name)
    bootstrap_file.write("""  (server-force-delete)\n""")
    bootstrap_file.write("""  (server-start)\n""")
    bootstrap_file.write(""")\n""")

    emacs_editor_el = open(os.path.join(self.mc.resources.base_dir, "ui/emacs_editor.el"), "r")
    bootstrap_file.write(emacs_editor_el.read())

    # this line IS KEY because it unlocks the "wait for emacs to start" loop below
    bootstrap_file.write("""(delete-file "%s")\n""" % bootstrap_file.name)
    bootstrap_file.close()

    assert os.path.exists(bootstrap_file.name)
    evalstr = """(load "%s")""" % bootstrap_file.name
    args = ["emacs", "--parent-id", "%s" % self._socket.get_id(), "--eval", evalstr]
    self._emacs = subprocess.Popen(args)

    assert self._emacs != None # process should have been created
    assert self._emacs.poll() == None # it should be running

    log1("Emacs process launched and inited with %s" % bootstrap_file.name)

    # wait for it to go away or a timeout
    start = time.time()
    while True:
      elapsed = time.time() - start
      if elapsed > 50:
        os.unlink(bootstrap_file.name)
        raise Exception("Timed out starting emacs. Consult the logfiles for diagnostics.")

      if os.path.exists(bootstrap_file.name) == False:
        log1("Emacs is up (emcacs deleted the bootstrap file)")
        break

      log1("waiting for emacs to become alive...")
      time.sleep(0.5) # wait more


    # veirfy that emacsclient agrees we're alive
    res = self.remote_run("-e '(selected-window)'",silent=True)
    error = False
    error |= res.startswith("emacsclient: connect: Connection refused")
    error |= res.startswith("emacsclient: can't find socket; have you started the server?")
    if error:
        print res
        raise Exception("Something unexpected happened when trying to talk to  emacs via emacsclient.")
    log1("Emacsclient is responding sanely.")

    # init marks
    self._init_marks()


    # emacs doesn't seem to listen to the first size that we give it, leaving it too small for a minute...
    # this hack basically waits a little bit before we see

    # focus us and get going
    self._install_mw_hooks_to_handle_emacs_suckage()
    self.grab_focus()

    # watch for emacs' death
    MessageLoop.add_delayed_message(self._check_alive,500)

  def _check_alive(self):
    if self._emacs:
      p = self._emacs.poll()
      if p != None:
        log0("Emacs exited. Quitting ndbg as well.")
        MessageLoop.quit()
      else:
        pass
    return True # keep timeout alive

  def destroy(self):
    EditorBase.destroy(self)
    if self._emacs:
      if self._emacs.poll() == None:
        log2("Emacs is still alive. Killing...")
        self._emacs.kill()
      self._emacs = None
      if os.path.exists(self._emacs_socket_name):
        try:
          os.unlink(self._emacs_socket_name)
        except OSError:
          log1("Error destroying emacs socket %s" % self._emacs_socket_name)



  @property
  def widget(self):
    return self._ebox

  def remote_eval(self,cmd):
    args = ["emacsclient", "-s", self._emacs_socket_name, "-e", cmd]
    return self.remote_run_ary(args)

  def remote_run(self,cmd,silent=False):
    args=shlex.split("emacsclient -s %s %s" % (self._emacs_socket_name, cmd))
    return self.remote_run_ary(args,silent)

  def push_remote_cmd(self, cmd):
    self._pending_cmds.append(cmd)
    if len(self._pending_cmds) == 1:
      MessageLoop.add_message(self._flush_pending_cmds)

  def _flush_pending_cmds(self):
    if len(self._pending_cmds) == 0:
      return
    tmp_file = tempfile.NamedTemporaryFile(delete=False)# open(f.name, "w")
    for cmd in self._pending_cmds:
      tmp_file.write(cmd)
      tmp_file.write("\n")
    tmp_file.write("\n")
    tmp_file.close()
    res = self.remote_eval("""(load "%s" nil t t)""" % tmp_file.name)
    del self._pending_cmds[:]
    os.unlink(tmp_file.name)

  def remote_run_ary(self,args,silent=False):
    log2("Launching %s", args)
    proc = subprocess.Popen(args, stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    res = proc.stdout.read()
    if not silent:
      if res.startswith("*ERROR*"):
        print "ERROR:\n%s\n%s\n\n" % (args,res.strip())
      if get_loglevel() == 3:
        log2("Done, got back [%s]", res)
      else:
        log2("Done, got back %s bytes", len(res))
    return res

  ###########################################################################

  def focus_file(self, file_handle, line_no = -1):
    if file_handle.exists:
      ret = self.remote_run("-e '(find-file \"%s\")'" % file_handle.absolute_name)
      if line_no != -1:
        cmd = "-e '(with-current-buffer (find-file-noselect \"%s\") (beginning-of-buffer) (forward-line %d))'" % (file_handle.absolute_name, line_no-1)
        self.remote_run(cmd)
    else:
      # TODO show the file not found tab...
      pass

  def get_current_location(self):
    self._flush_pending_cmds()
    # filename
    filename = self.remote_run("--e '(buffer-file-name (window-buffer (selected-window))))'").strip()
    if filename == None:
      raise NoCurrentLocationException("A non-file is selected currently.")
    if filename[0] != '"' or filename[-1] != '"':
      raise NoCurrentLocationException("Buffer is not a file: %s" % filename)
    filename = filename[1:-1]
    log2("Got %s from emacs for current buffer", filename)

    # lineno
    line_no_str = self.remote_run("-e '(with-current-buffer (window-buffer (selected-window)) (line-number-at-pos))'")
    line_no = int(line_no_str)

    fh = self.mc.filemanager.find_file(filename)
    return fh.make_location(line_no)

  def _init_marks(self):
    for m in self._mc.resources.mark_resources.values():
      s = """(setq ndbg-%s-image (find-image `((:type png :file "%s"))))""" % (m.el_name, m.filename_small)
      self.push_remote_cmd(s)

  def set_line_mark_states(self, file_handle, added, changed, removed):
    if len(added) + len(changed) + len(removed) == 0:
      return

    cmds = []
    abs_name = file_handle.absolute_name
    r = self._mc.resources
    def x(s):
      return "ndbg-%s-image" % s.get_mark_resource(r).el_name
    for l in removed:
      cmds += ['  (ndbg-remove-mark "%s" %i)' % (abs_name, l)]
    for l in changed:
      m = changed[l]
      cmds += ['  (ndbg-remove-mark "%s" %i)' % (abs_name, l)]
      cmds += ['  (ndbg-add-mark %s "%s" %i)' % (x(m), abs_name, l)]
    for l in added:
      m = added[l]
      cmds += ['  (ndbg-add-mark %s "%s" %i)' % (x(m), abs_name, l)]
    self.push_remote_cmd("\n".join(cmds))


if __name__ == "__main__":
  set_loglevel(3)
  class OverlayMock(object):
    def add_debug_menu_item(self,*args):
      pass
    def add_file_menu_item(self,*args):
      pass
    def add_tabs_menu_item(self,*args):
      pass

  class MockDebugger(object):
    def __init__(self):
      self.active_frame_changed = Event()
      self.breakpoints = BindingList()

  class MockMW(gtk.Window):
    def __init__(self):
      gtk.Window.__init__(self)
      self.set_title("EmacsTest")
      self.menu_bar = gtk.MenuBar()
      self.panels = {"panel1" : gtk.Notebook()}

  class MockResources(object):
    def __init__(self):
      self.base_dir = "."
      self.mark_resources = {}

  class MockMC(object):
    def __init__(self):
      self.debugger = MockDebugger()
      self.resources = MockResources()
      self.mw = MockMW()
    @property
    def when_debugging_overlay(self):
      return OverlayMock()

    def new_overlay (self, name):
      return OverlayMock()

  class MockFileHandle(object):
    def __init__(self,fn):
      self.absolute_name = os.path.realpath(fn)
    def exists(self):
      return os.path.exists(self.absolute_name)

  w = MockMW()
  ed = EmacsEditor(MockMC())
  hb = gtk.HBox()

  bn = gtk.Button("_Break line 8")
  def cb(*args):
    ed.focus_file(MockFileHandle("tests/apps/test2.c"), 8)
    ed.remote_eval("""(ndbg-set-current-line "tests/apps/test2.c" 8)""")
    ed.remote_eval("""(with-current-buffer (find-file-noselect "tests/apps/test2.c") (ndbg-set-image-at-line ndbg-test-image 8))""")
  bn.connect('clicked', cb)
  hb.pack_start(bn,False)

  bn = gtk.Button("_Unbreak line 8")
  def cb(*args):
    ed.remote_eval("""(with-current-buffer (find-file-noselect "tests/apps/test2.c") (ndbg-remove-image-at-line 8))""")
  bn.connect('clicked', cb)
  hb.pack_start(bn,False)

  entry = gtk.Entry()
  def on_press(w, event):
    keyname = gtk.gdk.keyval_name(event.keyval)
    if keyname == 'Return':
      text = entry.get_text()
#      entry.set_text("")
      print ed.remote_eval(text)
  entry.connect('key_press_event', on_press)
  hb.pack_start(entry,True)


  vbox = gtk.VBox()
  w.add(vbox)
  vbox.pack_start(ed.widget)
  vbox.pack_start(hb,False)

  def ondest(self,*args):
    MessageLoop.quit()
  w.connect('destroy', ondest)

  w.show_all()
  MessageLoop.add_cleanup(lambda: ed.destroy())
  MessageLoop.run()

