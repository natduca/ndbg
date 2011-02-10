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
from util.event import *
import pango

class NConsole(gtk.VBox):
  """
  A NConsole provides a VERY simple UI for terminal-style input

    c = NConsole()
    c.line_entered.add_listener(lambda line: print("Line: %s" % line))
    c.output("Hello world")

  """
  def __init__(self,mc):
    gtk.VBox.__init__(self)
    self._mc = mc

    self._line_entered = Event()

    self._tb = gtk.TextBuffer()

    self._sw = gtk.ScrolledWindow()
    self._sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

    self._tv = gtk.TextView(self._tb)
    self._sw.add(self._tv)

    self._tv.set_editable(False)
    self._tv.set_property('can-focus', False)
    self._entry = gtk.Entry()

    self._line_history_pos = 0
    self._line_history = [""]

    font_desc = pango.FontDescription('monospace %s' % mc.resources.CODE_FONT_SIZE)
    if font_desc:
      self._tv.modify_font(font_desc)
      self._entry.modify_font(font_desc)
      mc.resources.add_fontsize_skip(self._tv)
      mc.resources.add_fontsize_skip(self._entry)
    else:
      log0("Error finding monospace font")

    self._entry.connect('key_press_event', self._on_entry_key_press_event)

    self.pack_start(self._sw, True, True, 0)
    self.pack_start(self._entry, False, True, 0)

    self._tv.set_wrap_mode(gtk.WRAP_CHAR)

    self.show_all()

  def focus_entry(self):
    self._entry.grab_focus()

  def _on_entry_key_press_event(self, w, event):
    keyname = gtk.gdk.keyval_name(event.keyval)
    if keyname == 'Return':
      text = self._entry.get_text()
      self.output("%s\n" % text)
      self._fire_line_entered(text)
      return True
    elif keyname == "Up":
      print self._line_history_pos
      if self._line_history_pos == len(self._line_history) - 1:
        self._line_history[-1] = self._entry.get_text()
      self._line_history_pos = max(self._line_history_pos - 1, 0)
      if self._line_history_pos >= 0 and self._line_history_pos < len(self._line_history):
        self._entry.set_text(self._line_history[self._line_history_pos])
        self._entry.set_position(-1)
      return True
    elif keyname == "Down":
      self._line_history_pos = min(self._line_history_pos + 1, len(self._line_history) - 1)
      if self._line_history_pos >= 0 and self._line_history_pos < len(self._line_history):
        self._entry.set_text(self._line_history[self._line_history_pos])
        self._entry.set_position(-1)
      return True

  @property
  def mc(self):
    return self._mc

  def _fire_line_entered(self, text):
    if self._line_history_pos != len(self._line_history) - 1 and self._line_history[self._line_history_pos] == text:
      # repeated command
      print "repeated command"
      self._line_history[-1] = ""
      self._line_history_pos = len(self._line_history) - 1
    else:
      self._line_history[-1] = text
      if self._line_history[-1] != '':
        self._line_history.append("")
        self._line_history_pos = len(self._line_history) - 1
    self._line_entered.fire(text)
    self._entry.set_text("")

  @property
  def line_entered(self):
    return self._line_entered

  def output(self, text):
    self._tb.insert(self._tb.get_end_iter(), text)
    l = self._tb.get_end_iter()
    self._tb.move_mark_by_name("insert", l)
    self._tb.move_mark_by_name("selection_bound", l)
    self._tv.scroll_mark_onscreen(self._tb.get_mark("insert"))



