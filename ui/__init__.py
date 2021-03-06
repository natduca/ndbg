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
from __future__ import absolute_import

# our exports
from .main_window_base import MainWindowBase
from .main_control_base import MainControlBase
from .resources import Resources

# our imports needed for implementing run()
from util import MessageLoop,log0,log1,log2
import ndbg
from .platform import MainWindow, MainControl

_running = False
_mc = None

def run(settings, load_cb=None):
  global _running
  _running = True


  # actual init of the UI is done via this callback,
  # which is posted to the MessageLoop at the end of this function
  def do_init():
    # create them...
    resources = Resources(settings, ndbg.get_basedir())

    global _mc
    mw = MainWindow(settings, resources)

    def run_load_cb():
      log2("UI init: running on_load callback")
      if load_cb:
        load_cb(_mc)
      return False # ensure the timeout is a one-time thing
    def on_ready(*args):
      log2("UI init: window shown, scheduling load in 200ms")
      MessageLoop.add_delayed_message(run_load_cb, 200)
    if load_cb:
      mw.connect('show', on_ready)

    settings.set_delayed_save(True)
    _mc = MainControl(settings, mw)




  # Go! :)
  MessageLoop.add_message(do_init)
  MessageLoop.run()


  # cleanup
  _running = False
  if _mc:
    _mc.destroy()
  log2("ui.run done")

def is_running():
  return _running

def quit():
  if _running == False:
    raise Exception("UI not running")
  MessageLoop.quit()
