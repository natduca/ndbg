#!/usr/bin/env python2.6
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
  import pygtk
  pygtk.require('2.0')
except:
  pygtk = None

import sys
import os
import re
import threading
from optparse import OptionParser
import traceback
import exceptions
import subprocess
import shlex
import signal


from util import *

try:
  import ui
  from ui.main_control_launcher import *
except:
  print "While importing ui:"
  traceback.print_exc()
  ui = None

def _onsig_USR1(signum, frame):
  print "SIGUSR1 recieved."
  traceback.print_stack()
  print " "

signal.signal(10, _onsig_USR1)

def exists(f):
  return os.path.exists(f)

class LoadException(Exception):
  def __init__(self,msg):
    Exception.__init__(self)
    self.message = msg

def get_basedir():
  return os.path.dirname(sys.argv[0])

_debug_python_runtime = False
def set_debug_python_runtime():
  global _debug_python_runtime
  _debug_python_runtime = True

def is_debug_python_runtime():
  return _debug_python_runtime

def run_tests(options,args):
  MessageLoop.init_hooks()
  testmod = __import__("tests")
  testmod.set_debug_mode(options.test_debug == True)

  try:
    if len(args) > 0:
      testmod.run(args)
    else:
      testmod.run(None)
  except exceptions.KeyboardInterrupt:
    traceback.print_exc()
  log2("ndbg.run_tests complete")
  MessageLoop.shutdown_hooks()

CUR_SETTINGS_VERSION = 3 # bump this to force firstRun to run on old .ndbg files
def _first_run(settings):
  log1("_first_run...")
  global CUR_SETTINGS_VERSION
  settings.SettingsVersion = CUR_SETTINGS_VERSION # bump

  # prompt user via GUI which editor they want to use
  from ui.editor_selection_dialog import EditorSelectionDialog
  dlg = EditorSelectionDialog()
  resp = dlg.run()
  assert resp == gtk.RESPONSE_OK
  settings.Editor = dlg.editor # force it to a value, making it a user-specific setting

def process_options(options, args):
  """Returns dict with keys that need to be applied to the settings object"""
  res = DynObject()
  if options.exec_with_args:
    if not exists(options.exec_with_args[0]):
      print "%s is not a file. Cannot continue" % options.exec_with_args[0]
      return None
    res.ExecLaunch = options.exec_with_args
  else:
    if len(args) == 1:
      if re.match("^\d+$",args[0]):
        pid = int(args[0])
        res.ExecAttach = pid
      elif exists(args[0]):
        res.ExecLaunch = [args[0]]
      else:
        print "%s is not a file, nor a pid. Cannot continue" % args[0]
        return None
    elif len(args) == 2:
      if not exists(args[0]):
        print "%s is not a file. Cannot continue" % args[0]
        return
      if not re.match("^\d+$", args[1]):
        print "Second argument should be a pid" % args[1];
        return
      res.ExecAttach = int(args[1])
    else:
      log1("No arguments")
  return res

def launch_in_existing(options, args):
  # handle options first
  res = process_options(options, args)
  if not res:
    return
  if hasattr(res, 'ExecAttach') == False and hasattr(res, 'ExecLaunch') == False:
    print "Need to specify PID or executable when using the --existing flag."
    return

  # get MainControl proxies in existing ndbg processes
  from ui.main_control import MainControl
  mcs = MainControl.get_all_remote_instances()

  # If no ndbg exists, prompt the user to launch a new one
  # TODO(nduca): multiple dialogs may be presented at once. If they press yes on one,
  #              then broadcast to all other ndbg instances to close the open dialog
  #              and retry.
  if len(mcs) == 0:
    print "No nicer debugger instance found. Launch one and try again."
    return


  MessageLoop.add_message(lambda: MainControlLauncher(mcs, res))
  MessageLoop.run()




def run_ui(options, args):
  global ui
  if not ui:
    print "Cannot run UI.\n"
    return 255

  settings = new_settings()

  # defaults
  settings.register("SettingsVersion", int, 0)
  settings.register("Editor", str, None)
  global CUR_SETTINGS_VERSION
  if settings.SettingsVersion != CUR_SETTINGS_VERSION:
    _first_run(settings)

  # update settings object based on the editor stuffs
  if hasattr(options,"gvim") and options.gvim:
    settings.set_temporarily("Editor", "GVimEditor")
  elif hasattr(options,"emacs") and options.emacs:
    settings.set_temporarily("Editor", "EmacsEditor")
  elif hasattr(options,"sourceview") and options.sourceview:
    settings.set_temporarily("Editor", "SourceViewEditor")

  if settings.Editor == 'GVimEditor':
    import ui.gvim_editor
    ok, error = ui.gvim_editor.SanityCheck(settings)
    if not ok:
      print error
      return 255

  # debuger init
  settings.register("ExecLaunch", list, None)
  settings.register("ExecAttach", int, -1)
  res = process_options(options, args)
  if not res:
    return
  if hasattr(res,'ExecAttach'):
    settings.set_temporarily("ExecAttach", res.ExecAttach)
  elif hasattr(res,'ExecLaunch'):
    settings.set_temporarily("ExecLaunch", res.ExecLaunch)

  # UI init
  ui.run(settings) # engages main loop
  return 0

def main():
  # basic options
  log1("ndbg.main(argv=%s)\n" % sys.argv)

  parser = OptionParser()
  def handle_args(option,opt_str,value,parser,*args,**kwargs):
    value = []
    for arg in parser.rargs:
      value.append(arg)
    del parser.rargs[:len(value)]
    setattr(parser.values, option.dest, value)

  parser.add_option("--test", dest="test", action="store_true", default=False, help="Run internal tests. Any arguments passed will be regexps for the tests to run.")
  parser.add_option("--test-debug", dest="test_debug", action="store_true", default=False, help="Run internal tests, reporting errors immediately as they occurr. Any arguments passed will be regexps for the tests to run.")
  parser.add_option("--args", dest="exec_with_args", action="callback", callback=handle_args, help="Specify program to run plus arguments")
  parser.add_option("-v", action="count", dest="verbosity", help="Increase the verbosity level. Specifying repeatedly increases more.")

  parser.add_option("--sourceview", action="store_true", default=False, dest="sourceview", help="Enables use of SourceView as the editor component")
  parser.add_option("--gvim", action="store_true", default=False, dest="gvim", help="Enables use of GVimEditor as the editor component")
  parser.add_option("--emacs", action="store_true", default=False, dest="emacs", help="Enables use of EmacsEditor as the editor component")
  parser.add_option("-e", "--existing", action="store_true", default=False, dest="launch_in_existing", help="Launches the program inside an existing debugger instance rather than creating a new one.")

  parser.add_option("-D", action="store_true", default=False, dest="debug_gdb", help="Launches UI for debugging GDB operation.")

  (options,args) = parser.parse_args()

  # set verbosity
  if options.verbosity:
    set_loglevel(options.verbosity)
  else:
    set_loglevel(0)

  if options.debug_gdb:
    import debugger.gdb_backend
    debugger.gdb_backend.gdb_toggle_enable_debug_window()


  # test mode check
  if options.test or options.test_debug:
    run_tests(options,args)
  elif options.launch_in_existing:
    launch_in_existing(options, args)
  else:
    run_ui(options,args)

if __name__ == "__main__":
  try:
    main()
  except Exception, e:
    traceback.print_exc()

  log1("Performing final exit steps")
  threads =  threading.enumerate()
  threads.remove(threading.current_thread())
  if len(threads) == 0:
    log2("Exiting via sys.exit()")
    sys.exit(0)
  else:
    log1("Warning: threads are still running:")
    for t in threads:
      log1(" %s", t)
    log1("Exiting via os._exit")
    os._exit(0) # do this so we truly exit... even if we have a lingering thread [eew]
#  assert(False)
