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
import os.path
import gtk
import gobject
import gtksourceview2 as gtksourceview
import gio
import pango
import gobject

from editor_base import *

def get_language_for_mime_type(mime):
  lang_manager = gtksourceview.language_manager_get_default()
  lang_ids = lang_manager.get_language_ids()
  for i in lang_ids:
    lang = lang_manager.get_language(i)
    for m in lang.get_mime_types():
      if m == mime:
        return lang
  return None

def init_buffer(full_filename):
  buffer = gtksourceview.Buffer()
  mgr = gtksourceview.style_scheme_manager_get_default()
  style_scheme = mgr.get_scheme('classic')
  if style_scheme:
      buffer.set_style_scheme(style_scheme)

  f = gio.File(os.path.abspath(full_filename))
  path = f.get_path()

  info = f.query_info("*")

  mime_type = info.get_content_type()
  language = None

  if mime_type:
      language = get_language_for_mime_type(mime_type)
      if not language:
          print 'No language found for mime type "%s"' % mime_type
  else:
      print 'Couldn\'t get mime type for file "%s"' % full_filename

  buffer.set_language(language)
  buffer.set_highlight_syntax(True)

  f = open(full_filename, "r")
  buffer.set_text(f.read())
  f.close()
  return buffer


class SourceViewTab(gtk.ScrolledWindow):
  def __init__(self,editor,file_handle):
    if file_handle.exists == False:
      raise Exception("Cannot create SourceViewTab with a nonexistant file.")
    gtk.ScrolledWindow.__init__(self)
#    self.set_shadow_type(gtk.SHADOW_IN)
    self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

    self._editor = editor
    self._file_handle = file_handle

    self.buffer = init_buffer(file_handle.absolute_name)
    self._view = gtksourceview.View(self.buffer)

    self.add(self._view)

    font_desc = pango.FontDescription('monospace %s' % editor.mc.resources.CODE_FONT_SIZE)
    if font_desc:
        self._view.modify_font(font_desc)

    self._view.set_show_line_numbers(True)
    self._view.set_editable(False)
    self._view.set_show_line_marks(True)

    self._view.set_property('highlight-current-line', True)

    self._view.connect_object('button-press-event', self._on_button_pressed,None)
    self._view.connect('size-allocate', self._on_size_allocated)

    self._current_line_tag = self.buffer.create_tag(None,background=editor.mc.resources.COLOR_CURRENT_LINE)
    self._active_frame_tag = self.buffer.create_tag(None,background=editor.mc.resources.COLOR_ACTIVE_FRAME)

    for mark_res in  self._editor._mc.resources.mark_resources.values():
      self._view.set_mark_category_pixbuf(mark_res.name, mark_res.pixmap)

  def grab_focus(self):
    self._view.grab_focus()

  def focus_line(self,line):
    l = self.buffer.get_iter_at_line(line-1)
    self.buffer.move_mark_by_name("insert", l)
    self.buffer.move_mark_by_name("selection_bound", l)
    self._view.scroll_mark_onscreen(self.buffer.get_mark("insert"))

  @property
  def file_handle(self):
    return self._file_handle

  def _on_size_allocated(self,a,b):
    self._view.scroll_mark_onscreen(self.buffer.get_mark("insert"))

  def get_current_line(self):
    line = self.buffer.get_iter_at_mark(self.buffer.get_mark("insert")).get_line()+1
    return line

  def set_line_mark_states(self,added,changed,removed):
    for l in added.keys():
      self._set_line_mark_state(l,added[l])
    for l in changed.keys():
      self._set_line_mark_state(l,changed[l])
    completely_unmarked = LineMarkState()
    for l in removed:
      self._set_line_mark_state(l,completely_unmarked)

  def _set_line_mark_state(self,line,mark_state):
    line_begin_iter = self.buffer.get_iter_at_line(line-1)
    line_end_iter = self.buffer.get_iter_at_line(line)

    # remove any marks currently on this line...
    self.buffer.remove_source_marks(line_begin_iter,line_end_iter)

    # create source mark
    res = mark_state.get_mark_resource(self._editor._mc.resources)
    if res:
      self.buffer.create_source_mark(None,res.name,line_begin_iter)

    # set or remove the highlight
    if mark_state.current_line:
      self.buffer.apply_tag(self._current_line_tag, line_begin_iter, line_end_iter)
    else:
      self.buffer.remove_tag(self._current_line_tag, line_begin_iter, line_end_iter)

    # update the active_frame highlight
    if mark_state.active_frame:
      self.buffer.apply_tag(self._active_frame_tag, line_begin_iter, line_end_iter)
    else:
      self.buffer.remove_tag(self._active_frame_tag, line_begin_iter, line_end_iter)


  def _on_button_pressed(self, view, ev):
    buffer = self.buffer
    # check that the click was on the left gutter
    if ev.window == self._view.get_window(gtk.TEXT_WINDOW_LEFT):
      x_buf, y_buf = self._view.window_to_buffer_coords(gtk.TEXT_WINDOW_LEFT,
                                                  int(ev.x), int(ev.y))
      # get line bounds
      line_start = self._view.get_line_at_y(y_buf)[0].get_line()+1

      loc = self._file_handle.make_location(line_start)
      self._editor.toggle_breakpoint(loc)

    return False


if __name__ == "__main__":
  __import__('pygtk').require('2.0')
  w = gtk.Window()
  w.set_title("test")
  sv = SourceViewTab("./test/test1.c")
  sv.set_size_request(400,300)
  sv.set_current_breakpoints([1,3,5])
  sv.set_current_line(4)
  sv.show()
  w.add(sv)
  w.show()
  gtk.main()
