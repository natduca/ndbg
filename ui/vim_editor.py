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

from editor_base import *

# This class implements EditorBase via Vim running in a terminal [for now]
class VimEditor(EditorBase):
  def __init__(self,mc):
    EditorBase.__init__(self)
    self._mc = mc

    self._vbox = gtk.VBox()

    pty_fds = pty.openpty()
    self._pty_fds = pty_fds

    slavedev = os.ttyname(pty_fds[1])

    # create terminl
    self._term = vte.Terminal()
    self._term.set_pty(self._pty_fds[0])
    self._vbox.add(self._term)
    self._vbox.show_all()

    # launch vim
    cmdline = "vim"
    args = shlex.split(cmdline)
    self._vim = subprocess.Popen(args,stdin=pty_fds[1],stdout=pty_fds[1],stderr=pty_fds[1])


  @property
  def widget(self):
    return self._vbox
