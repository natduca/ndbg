import gtk
from util import *
class _BetterPaned():
  def __init__(self):
    self.add_events(gtk.gdk.ALL_EVENTS_MASK)
    self.connect('button-press-event', self._on_button_press)
    self.connect('button-release-event', self._on_button_release)
    self.connect('notify::position', self._on_raw_position_changed)

    self._user_is_dragging = False
    self._position_changed = Event()

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



class BetterHPaned(gtk.HPaned,_BetterPaned):
  def __init__(self):
    gtk.HPaned.__init__(self)
    _BetterPaned.__init__(self)

class BetterVPaned(gtk.VPaned,_BetterPaned):
  def __init__(self):
    gtk.VPaned.__init__(self)
    _BetterPaned.__init__(self)

if __name__ == "__main__":
  w = gtk.Window()
  p = BetterHPaned()
  b1 = gtk.Button("foo")
  b2 = gtk.Button("bar")
  def on_click(x):
    b2.set_size_request(300,-1)
  b1.connect('clicked', on_click)
  p.pack1(b1,True,True)
  p.pack2(b2,True,True)
  def on_changed():
    print "pos changed"
  p.position_changed.add_listener(on_changed)

  w.set_size_request(300,400)
  w.add(p)
  w.show_all()
  gtk.main()
