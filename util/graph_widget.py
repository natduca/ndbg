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
import glib
import gtk
import pango
import sys
import random
import pickle

from base import *
from vec2 import *
from graph import *
import math

# Graph widget
###########################################################################
class GraphWidget(gtk.DrawingArea):
  def __init__(self,graph):
    gtk.Widget.__init__(self)
    self._graph = graph
    self._graph.changed.add_listener(self._on_changed)
    self.connect("expose-event", self._on_expose)
    self._timer_running = False
    self._timer = Timer(0.033,self._on_timer_tick)
    if self._graph.needs_layout:
      self._timer.enabled = True
    self.connect('size-allocate', self._on_resize)
    self.set_events(gtk.gdk.POINTER_MOTION_MASK  | gtk.gdk.POINTER_MOTION_HINT_MASK| gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK)
    self.connect("motion_notify_event", self._on_mouse_moved)
    self.connect("button-press-event", self._on_mouse_down)
    self.connect("button-release-event", self._on_mouse_up)
    self.connect("leave-notify-event", self._on_mouse_leave)
    self._node_at_mouse_down = None
    self._hovered_node = None
    self._layout_enabled = True

  def set_layout_enabled(self,en):
    self._layout_enabled = en
    if self._layout_enabled == True:
      self._on_changed()
  layout_enabled = property(lambda self: self._layout_enabled, set_layout_enabled)

  def pick_node_at(self,x,y):
    return self._pick_node(ivec2(x,y))
  
  def _pick_node(self,v):
    for n in self._graph.nodes:
      np = n._position
      nr = rect(n._position,n._last_drawn_size,centered=True)
      if nr.contains(v):
        return n
    return None

  def _on_mouse_down(self,w,event):
    if event.button == 1:
      mpos = self._from_screen(ivec2(event.x,event.y))
      n = self._pick_node(mpos)
      self._node_at_mouse_down = n


  def _on_mouse_moved(self,w,event):
    mpos = self._from_screen(ivec2(event.x,event.y))
    n = self._pick_node(mpos)
    old_hover = self._hovered_node
    if self._hovered_node and self._hovered_node != n:
      self._hovered_node.mouse_leave.fire()
    self._hovered_node = n
    if self._hovered_node and self._hovered_node != old_hover:
      self._hovered_node.mouse_enter.fire()

  def _on_mouse_up(self,w,event):
    if self._node_at_mouse_down:
      mpos = self._from_screen(ivec2(event.x,event.y))
      ncur = self._pick_node(mpos)
      if ncur == self._node_at_mouse_down:
        print "Clicked"
        self._node_at_mouse_down.clicked.fire()
      self._node_at_mouse_down = None

  def _on_mouse_leave(self,w,event):
    if self._hovered_node:
      self._hovered_node.leave.fire()
      self._hovered_node = None

  def _on_changed(self):
    if self._layout_enabled == False:
      return
    size = self.get_allocation()
    self._graph.layout()
    self._update_transform()
    self.queue_draw_area(0,0,size[0],size[1])
    self._timer.enabled = True # keep doing layout

  def _on_timer_tick(self):
#    print "tick"
    for i in range(0,10):
      self._graph.layout()
      if self._graph.needs_layout == False:
        break
      
    # redraw
    self._update_transform()
    self.queue_draw_area(0,0,self.allocation.width,self.allocation.height)
    if self._graph.needs_layout:
      return
#    print "Stopping layout."
    self._timer.enabled = False

  def _on_resize(self,w,event):
    self._update_transform()

  def _update_transform(self):
    bounds = self._graph.bounds
    range = vec2_sub(bounds.hi, bounds.lo)
    pad = vec2(range.x * 0.2, range.x * 0.1) # pad more on x because of labels
    lo = vec2_sub(bounds.lo,pad) # move lo down by pad
    range = vec2_add(range,pad) #increase range by 2*pad
    range = vec2_add(range,pad) # hehe laziness
    size = vec2(self.allocation.width,self.allocation.height)
    if range.x == 0 or range.y == 0:
      scale= vec2(1,1)
    else:
      scale = vec2_piecewise_div(size,range)
    def to_screen(v):
      return ivec2(vec2_piecewise_mul(vec2_sub(v,lo),scale))
    def from_screen(in_s):
      s = vec2(in_s)
      return vec2_add(vec2_piecewise_div(s,scale),lo)
    def from_screen_size(in_s):
      s = vec2(in_s)
      return vec2_piecewise_div(s,scale)
    self._to_screen = to_screen
    self._from_screen = from_screen
    self._from_screen_size = from_screen_size

  def _on_expose(self,a,b):
    style = self.get_style()
    gdk = gtk.gdk

    black = gdk.color_parse("black")
    yellow = gdk.color_parse("yellow")
    white = gdk.color_parse("white")

    g = self.window
    gc = g.new_gc()
    colormap = self.get_colormap()
    colors = {}
    def get_color(c):
      if colors.has_key(c) == False:
        colors[c] = colormap.alloc_color(c, False,False)
      return colors[c]

    # draw edges
    gc.foreground = yellow
    for e in self._graph.edges:
      n1p = self._to_screen(e.node1._position)
      n2p = self._to_screen(e.node2._position)
      gc.line_width = e._weight
      gc.foreground = get_color(e._color)
      g.draw_line(gc, n1p.x, n1p.y, n2p.x, n2p.y)

    # now draw nodes... :( i'm tired!
    max_w = 100
    layout = self.create_pango_layout("")
    gc.line_width = 1
    for n in self._graph.nodes:
      np = self._to_screen(n._position)

      layout.set_width(max_w)
      layout.set_alignment(pango.ALIGN_LEFT);
      layout.set_text(n._label)
      layout_size = layout.get_pixel_size()

      w = layout_size[0] + 4
      lo_x = int(np.x - w/2)
      h = layout_size[1]
      lo_y = np.y - h/2
      n._last_drawn_size = self._from_screen_size(vec2(w,h))

      gc.foreground = get_color(n._background_color)
      g.draw_rectangle(gc, True, lo_x, lo_y, w, h)

      gc.foreground = get_color(n._border_color)
      g.draw_rectangle(gc, False, lo_x, lo_y, w, h)

      x = np.x - layout_size[0] / 2
      y = np.y - layout_size[1] / 2
      gc.foreground = get_color(n._text_color)
      g.draw_layout(gc, x, y, layout)



###########################################################################

if __name__ == "__main__":
  if len(sys.argv) > 1:
    try:
      f = open(sys.argv[1])
    except:
      print "Could not open %s" % sys.argv[1]
      exit()
    graph = pickle.load(f)
  else:
    graph = testGraph()

  w = gtk.Window()
  w.set_title("GraphWidget Test")
  gw = GraphWidget(graph)
  w.add(gw)
  w.set_size_request(400,300)
  w.show_all()
  gtk.main()
