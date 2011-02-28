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
  import gtk
except:
  gtk = None

from util import *

BETTER_PANE_POSITION_GRAVITY_START = "PosGravity0"  # means position is relative to the 
BETTER_PANE_POSITION_GRAVITY_END = "PosGravity1"
BETTER_PANE_POSITION_GRAVITY_RELATIVE = "PosGravityRelative"

if gtk:
  class _BetterPaned():
    def __init__(self):
      self.add_events(gtk.gdk.ALL_EVENTS_MASK)
      self.connect('button-press-event', self._on_button_press)
      self.connect('button-release-event', self._on_button_release)
      self.connect('notify::position', self._on_raw_position_changed)
      self.connect('size-allocate', self._on_size_allocate)

      self._position_gravity = BETTER_PANE_POSITION_GRAVITY_START
      self._pending_position = None
      self._user_is_dragging = False
      self._has_been_allocated = False
      self._position_changed = Event()

    def pack1(self,w):
      if self._position_gravity == BETTER_PANE_POSITION_GRAVITY_START:
        gtk.Paned.pack1(self,w,False,True)
      elif self._position_gravity == BETTER_PANE_POSITION_GRAVITY_END:
        gtk.Paned.pack1(self,w,True,True)
      elif self._position_gravity == BETTER_PANE_POSITION_GRAVITY_RELATIVE:
        gtk.Paned.pack1(self,w,True,True)
      else:
        assert False
    def pack2(self,w):
      if self._position_gravity == BETTER_PANE_POSITION_GRAVITY_START:
        gtk.Paned.pack2(self,w,True,True)
      elif self._position_gravity == BETTER_PANE_POSITION_GRAVITY_END:
        gtk.Paned.pack2(self,w,False,True)
      elif self._position_gravity == BETTER_PANE_POSITION_GRAVITY_RELATIVE:
        gtk.Paned.pack2(self,w,True,True)
      else:
        assert False

    @property
    def position_gravity(self):
      return self._position_gravity
    @position_gravity.setter
    def position_gravity(self,g):
      if self._has_been_allocated:
        raise Except("changing gravity on the fly not supported yet.")
      self._position_gravity = g

    @property
    def position(self):
      return self.get_position()
    @position.setter
    def position(self,p):
      self.set_position(p)

    def get_position(self):
      if self._pending_position:
        return self._pending_position
      else:
        assert self._has_been_allocated
        rawpos = gtk.Paned.get_position(self)
        if isinstance(self,gtk.HPaned):
          primary_dimension = self.get_allocation().width
        else:
          primary_dimension = self.get_allocation().height

        if self._position_gravity == BETTER_PANE_POSITION_GRAVITY_START:
          return rawpos
        elif self._position_gravity == BETTER_PANE_POSITION_GRAVITY_END:
          return primary_dimension - rawpos
        elif self._position_gravity == BETTER_PANE_POSITION_GRAVITY_RELATIVE:
          return int((float(rawpos) / float(primary_dimension)) * 100)
        else:
          assert False

    def set_position(self,p):
      if not self._has_been_allocated:
        self._pending_position = p
      else:
        assert self._has_been_allocated
        self._manually_changing_position = True
        if isinstance(self,gtk.HPaned):
          primary_dimension = self.get_allocation().width
        else:
          primary_dimension = self.get_allocation().height

        if self._position_gravity == BETTER_PANE_POSITION_GRAVITY_START:
          gtk.Paned.set_position(self,p)
        elif self._position_gravity == BETTER_PANE_POSITION_GRAVITY_END:
          gtk.Paned.set_position(self,primary_dimension - p)
        elif self._position_gravity == BETTER_PANE_POSITION_GRAVITY_RELATIVE:
          perc = (p / 100.0)
          rawpos = int(primary_dimension * perc)
          gtk.Paned.set_position(self,rawpos)
        else:
          assert False
        self._manually_changing_position = False

    def _on_size_allocate(self,*args):
      had_been_allocated = self._has_been_allocated
      self._has_been_allocated = True
      if not had_been_allocated and self._pending_position:
        p = self._pending_position
        self._pending_position = None
        self.set_position(p)

    @property
    def position_changed(self):
      return self._position_changed

    def _on_raw_position_changed(self,*args):
      if self._user_is_dragging:
        self.position_changed.fire()

    def _on_button_press(self,w,e,*args):
      if e.button == 1:
        self._user_is_dragging = True

    def _on_button_release(self,w,e,*args):
      self._user_is_dragging = False



  class BetterHPaned(_BetterPaned,gtk.HPaned):
    def __init__(self):
      gtk.HPaned.__init__(self)
      _BetterPaned.__init__(self)

  class BetterVPaned(_BetterPaned,gtk.VPaned):
    def __init__(self):
      gtk.VPaned.__init__(self)
      _BetterPaned.__init__(self)

if __name__ == "__main__":
  w = gtk.Window()
  p = BetterHPaned()
  p.position_gravity = BETTER_PANE_POSITION_GRAVITY_RELATIVE
  p.position = 50
  b1 = gtk.Button("foo")
  b2 = gtk.Button("bar")
  def on_click(x):
    b2.set_size_request(300,-1)
  b1.connect('clicked', on_click)
  p.pack1(b1)
  p.pack2(b2)
  def on_changed():
    print "pos changed to %i" % p.position
  p.position_changed.add_listener(on_changed)

  w.set_size_request(300,400)
  w.add(p)
  w.show_all()
  gtk.main()
