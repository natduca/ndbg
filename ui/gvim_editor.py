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
import os.path
import shlex
import subprocess
import tempfile

from editor_base import *

_USE_ASYNC = False

def SanityCheck(settings):
  """
  Makes sure vim aliases/scripts aren't wrapping the actual vim executable.
  """
  ok,status = _SanityCheckInternal(settings)
  if not ok:
    status ="""While trying to launch, ndbg encountered a problem with your current
system's vim configuration:

%s
""" % (status)
  return (ok, status)

def _TryCommunicate(args):
  try:
    p = subprocess.Popen(args, stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  except OSError:
    return None
  return p.communicate()[0]

def _SanityCheckInternal(settings):
  settings.register("GVimEditorVimExecutable", str, "vim")
  resp = _TryCommunicate([settings.GVimEditorVimExecutable, "--version"])
  if resp == None or not resp.startswith("VIM - Vi IMproved "):
    resp2 = _TryCommunicate(["/usr/bin/vim", "--version"])
    if resp2.startswith("VIM - Vi IMproved "):
      return (False,"""%s existed but did respond as expected to --version.
However, /usr/bin/vim exists and responds as expected. Maybe you've aliased vim.

Consider adding a field to ~/.ndbg to point at vim directly:
  "GVimEditorVimExecutable": "/usr/bin/vim"

""" % settings.GVimEditorVimExecutable)
    if resp == None:
      return (False, """Could not launch executable. Do you have vim at all?""")

    return (False,""""vim existed but did respond as expected to --version.

Maybe you have your path poitned at something wierd. If needed, add a field
 ~/.ndbg to point at the vim executable:

  "GVimEditorVimExecutable": "/usr/bin/vim"

""")

  lines = resp.split('\n')

  expected_args = set(['gtk', 'clientserver', 'X11'])
  found_args = set()
  for a in expected_args:
    if resp.find(a) != -1:
      found_args.add(a)
  if found_args != expected_args:
    return (False, "Missing support for %s\n" % ", ".join(expected_args))
  return (True, "OK")

# This class implements EditorBase via gvim using a gtksocket
class GVimEditor(EditorBase):
  def __init__(self, mc):
    EditorBase.__init__(self, mc)

    mc.settings.register("GVimEditorFirstRun", bool, True)
    if mc.settings.GVimEditorFirstRun:
      mc.settings.GVimEditorFirstRun = False
      b = ButterBar("nDBG's GVim mode has a few quirks that you might want to know about...")
      b.set_stock_icon(gtk.STOCK_DIALOG_INFO)
      b.add_button("Tell me more...", self._on_more_gvim_information)
      b.add_close_button()
      mc.butter_bar_collection.add_bar(b)

    mc.settings.register("GVimEditorVimExecutable", str, "vim")

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

    self._socket = gtk.Socket()
    self._ebox.add(self._socket)
    self._ebox.add_events(gtk.gdk.KEY_PRESS_MASK | gtk.gdk.BUTTON_PRESS_MASK)
    self._ebox.show_all()
    self._ebox.connect('realize', self.on_realize)

    self._pending_flush_proc = None
    self._pending_exprs = []

    self._vim = None
    self._vim_alive = False

  def _on_more_gvim_information(self):
    msg = """
Great to see you've chosen to use GVim for your text editor.

Due to bugs in GtkSocket and GVim' plug implementation,
GVim will sometimes think it does not have keyboard focus.
It will still recieve and process key presses, but the
 cursor will be hollow, i.e. as if the window wasn't focused.

Yuck!

As a nDBG user, you have two options:
1. Help us figure out why that happens! ;)
2. Press Control-Alt k. This will focus GVim again.

"""
    def doit():
      dlg = gtk.MessageDialog(buttons=gtk.BUTTONS_OK, message_format=msg)
      dlg.run()
      dlg.destroy()
    MessageLoop.add_delayed_message(doit, 30)

  def destroy(self):
    EditorBase.destroy(self)
    if self._vim:
      # send quit command to vim
      self.vim_remote("NdbgQuit()")
      log2("Waiting for vim to exit...")
      start_wait = time.time()
      while self._vim.poll() and time.time() < start_wait + 1:
        time.sleep(0.1)
      if self._vim.poll():
        log2("Timed out waiting for vim to exit; killing...")
        self._vim.kill()
      else:
        log2("Vim exited gracefully.")

  def _determine_server_name(self):
    resp = subprocess.Popen([self.mc.settings.GVimEditorVimExecutable, "--serverlist"], stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
    serverlist = resp.split("\n")
    template = "NDBG%i"
    i = 0
    while True:
      i += 1
      candidate_name = template % i
      if candidate_name not in serverlist:
        log1("NDBG candidate match: %s" % candidate_name)
        self._server_name = candidate_name
        return


  def on_realize(self, *kw):
    # pick a vim name
    self._determine_server_name()

    # XXX Get gvimrc location from resources.
    log2("Launching vim")

    bootstrap_file = tempfile.NamedTemporaryFile(delete=False)
    template_file = open(os.path.join(self.mc.resources.base_dir, 'ui/ndbg.vim'), 'r')
    for line in template_file.readlines():
      if line.startswith("__NDBG_AUTOGENERATED_SIGNS__\n"):
        for m in self._mc.resources.mark_resources.values():
          if m.integer_id == 0:
            sign = 'sign define %s icon=%s linehl=Search' % (m.name, m.filename)
          else:
            sign = 'sign define %s icon=%s' % (m.name, m.filename)
          bootstrap_file.write("exe \"%s\"" % sign)
          bootstrap_file.write("\n")
        m = ", ".join(["%s:'%s'" % (x.integer_id, x.name) for x in self._mc.resources.mark_resources.values()])
#        0:'current', 1:'breakpoint', 2:'callstack'}
        print m
        bootstrap_file.write("let s:id_to_sign = {%s}\n" % m)


#let s:id_to_sign = {0:'current', 1:'breakpoint', 2:'callstack'}
#exe "sign define current icon=".images_dir."/current_line.png linehl=Search"
#exe "sign define breakpoint icon=".images_dir."/all_break.png"
#exe "sign define callstack icon=".images_dir."/on_callstack.png"
      else:
        bootstrap_file.write(line)
    bootstrap_file.close()
    print bootstrap_file.name
    self._vim = subprocess.Popen(shlex.split(
            "vim -g --servername %s --socketid %d -S %s" %
            (self._server_name,
             self._socket.get_id(),
             bootstrap_file.name
             )))
    log2("Vim launched pid=%i", self._vim.pid)


    self._wait_for_vim_to_become_alive()
    assert self._vim
#    os.unlink(bootstrap_file.name)

    # watch for its death
    MessageLoop.add_delayed_message(self._check_alive,250)

  def grab_focus(self):
    self._ebox.grab_focus()

  def _wait_for_vim_to_become_alive(self):
    # wait until we get vim up and responding to serverlist
    def server_running():
      resp = subprocess.Popen([self.mc.settings.GVimEditorVimExecutable, "--serverlist"], stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
      if resp[0].find(self._server_name) != -1:
        log2("VIM confirmed alive")
        self._vim_alive = True
        return True
      return False
    MessageLoop.run_until(server_running)

  def _check_alive(self):
    resp = subprocess.Popen([self.mc.settings.GVimEditorVimExecutable, "--serverlist"], stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
    serverlist = resp.split("\n")
    if self._server_name not in serverlist:
      log0("Vim exited. Quitting ndbg as well.")
      MessageLoop.quit()
      return False
    return True # keep timeout alive

  @property
  def widget(self):
    return self._ebox

  def vim_remote(self, expr, remote_flavor="--remote-expr"):
    self._flush_pending_exprs(async=False)

    args = ("vim --servername %s" % self._server_name).split() + [remote_flavor, expr]

    if self._vim == None:
      raise Exception("Cannot communicate with gvim. Not launched yet.")
    log2("Launching %s", args)
    proc = subprocess.Popen(args, stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    res = proc.stdout.read()
#    res = proc.communicate()
    log2("Done, got back %s bytes", len(res))
#    print "%s->%s" % (args, res)
    if proc.poll() == None:
      proc.kill() # just in case...
    return res

  def push_remote_expr(self, expr):
    self._pending_exprs.append(expr)
    if len(self._pending_exprs) == 1:
      if _USE_ASYNC:
        MessageLoop.add_delayed_message(self._flush_pending_exprs, 5)
      else:
        MessageLoop.add_message(self._flush_pending_exprs)

  def _flush_pending_exprs(self,async=True):
    if self._pending_flush_proc:
      if not self._pending_flush_proc.poll():
#        log0("Waiting on previous flush")
        self._pending_flush_proc.wait()
      os.unlink(self._pending_temp_file)
      self._pending_temp_file = None
      self._pending_flush_proc = None

    if len(self._pending_exprs) == 0:
      return

    tmp_file = tempfile.NamedTemporaryFile(delete=False)
    for expr in self._pending_exprs:
      tmp_file.write("call ")
      tmp_file.write(expr)
      tmp_file.write("\n")
    tmp_file.write("\n")
    tmp_file.close()
    del self._pending_exprs[:]

#    if _USE_ASYNC:
#      self.grab_focus()

    args = [self.mc.settings.GVimEditorVimExecutable, "--servername", self._server_name, "--remote-expr", "NdbgRunScript(\'%s\')" % tmp_file.name]
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    if not async or not _USE_ASYNC:
      proc.wait()
      os.unlink(tmp_file.name)
    else:
      self._pending_flush_proc = proc
      self._pending_temp_file = tmp_file.name
#      MessageLoop.add_delayed_message(self._try_redraw, 5)

#  def _try_redraw(self):
#    if self._pending_flush_proc == None:
#      return
#    print "Pending", self._pending_flush_proc.pid
#    res= self._pending_flush_proc.poll()
#    if res:
#      print "Redrawing"
#      xa = [self.mc.settings.GVimEditorVimExecutable, "--servername", self._server_name, "--remote-expr", "NdbgRedraw()"]
#      x = subprocess.Popen(xa, stdout=subprocess.PIPE)
#      return False
#    else:
#      print "Can't redraw yet, poll returned none"
#      return True

  # EditorBase methods
  ############################################################################
  def focus_file(self, file_handle, line_no = -1):
    if file_handle.exists:
      self.push_remote_expr("NdbgDrop('%s')" % file_handle.absolute_name)
      if line_no != -1:
        self.push_remote_expr("setpos('.', [0,%d,0,0])" % (line_no))
    else:
      # TODO show the file not found message...
      pass

  def get_current_location(self):
    self._flush_pending_exprs()
    filename = self.vim_remote("expand('%:p')").strip()
    fh = self.mc.filemanager.find_file(filename)
    line_no = int(self.vim_remote("line('.')"))
    return fh.make_location(line_no)

  def set_line_mark_states(self, file_handle, added, changed, removed):
    if not file_handle.exists:
      return

    res = self._mc.resources
    def convert_mark_state(m):
      r = m.get_mark_resource(res)
      if r == None:
        return -1
      return r.integer_id

    log2("set_line_mark_states: %s %s %s", added, changed, removed)
    vim_added = [[l, convert_mark_state(m)] for l, m in added.iteritems()]
    vim_changed = [[l, convert_mark_state(m)] for l, m in changed.iteritems()]
    log2("after: %s %s %s", vim_added, vim_changed, removed)
    self.push_remote_expr("NdbgLineMarkStates(%s, %s, %s, '%s')" %
                         (vim_added, vim_changed, removed,
                          file_handle.absolute_name))
