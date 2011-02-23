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

from util import *
from overlay import *
import ui
from butter_bar import *

class TabPanel(gtk.Notebook):
  def __init__(self, mw, id):
    gtk.Notebook.__init__(self)
    self._id = id
    self._mw = mw
    self.set_tab_pos(gtk.POS_BOTTOM)
    self.set_group_id(0x31415)
    self.connect("page-added", self._on_page_added)
    self.connect("page-removed", lambda *args: self.update_visibility())
    self.connect("create-window", self._on_create_window)
    self.set_name("TabPanel")
    self.set_property('tab-border', 0)
    self.set_property('show-border', False)

  @property
  def id(self):
    return self._id

  def _on_create_window(self,src_notebook, page, x, y):
    print "CreateWindow at %i,%i" % (x, y)
    w = gtk.Window()
    p = TabPanel(self._mw)
    psr = list(page.get_size_request())
    if psr[0] <= 0:
      psr[0] = 300
    if psr[1] <= 0:
      psr[1] = 200
    w.resize(psr[0],psr[1])
    w.move(x-5,y-5)
    w.add(p)
    w.show_all()

    i = src_notebook.get_page_index(page)
    l = src_notebook.get_tab_label(page)
    src_notebook.remove_page(i)
    p.append_page(page,l)
    p.set_tab_reorderable(page,True)
    p.set_tab_detachable(page,True)



  def _on_page_added(self, nb, page, pageNum, *args):
    # page's overlay needs to know that it changed panels
    overlay = self._mw._tab_owner_overlays[page]
    overlay.on_tab_panel_changed(page, self)
    self.update_visibility()

  def update_visibility(self):
    # are all our children hidden?
    one_visible = False
    for i in range(0,self.get_n_pages()):
      if self.get_nth_page(i).get_property('visible'):
        one_visible = True
    if one_visible:
      self.show()
    else:
      self.hide()
  def get_page_index(self,tab):
    for i in range(0,self.get_n_pages()):
      if self.get_nth_page(i) == tab:
        return i
    return -1

  def add_tab(self,tab,title,owner_overlay):
    if tab.get_parent():
      raise Exception("tab is already attached to something")

    self._mw._tab_owner_overlays[tab] = owner_overlay

    l = gtk.Label(title)
    self.append_page(tab,l)
    self.set_tab_reorderable(tab,True)
    self.set_tab_detachable(tab,True)
    self.update_visibility()

  def remove_tab(self,tab):
    if tab.get_parent() != this:
      raise Exception("Not my child")
    for i in range(0,self.get_n_pages()):
      if self.get_page(i) == tab:
        tab.remove_page(i)
        break
    del self._mw._tab_owner_overlays[tab]
    self.update_visibility()

def _is_child_of(w,parent):
  cur = w
  while cur:
    if cur == parent:
      return True
    cur = cur.get_property('parent')
  return False


class MainWindow(gtk.Window):
  def __init__(self, settings, resources):
    gtk.Window.__init__(self)
    self._settings = settings
    self._resources = resources
    self._layout = None
    self._layout_changing = False
    self._pending_stop_ignoring_changes_message = None
    self._init_window()
    self._overlays = []
    self._ids_in_use = set()
    self._tab_owner_overlays = {}


  @property
  def resources(self):
    return self._resources

  def _handle_escape_pressed(self):
    log3("Escape with %s focused: " % self.get_focus())
    if _is_child_of(self.get_focus(), self._cstage) == False:
      if len(self._butter_bar_collection):
        print("Closing first butter bar")
        self._butter_bar_collection.remove_bar(self._butter_bar_collection[0])
        return True


      children = self._cstage.get_children()
      if len(children):
        print("Focusing center stage")
        children[0].grab_focus()
        return True

  def _on_exit(self,u):
    ui.quit()

  def _on_destroy(self,*args):
    if ui.is_running():
      ui.quit()

  def destroy(self):
    for ovl in self._overlays:
      ovl.destroy()
    gtk.Window.destroy(self)

  def new_overlay(self,name):
    ovl = MainWindowOverlay(self,self._settings,name,self._layout)
    self._overlays.append(ovl)
    return ovl

  @property
  def overlays(self):
    return list(self._overlays) # copy so client can't mutate the overlay

  def _make_menu(self):
    menu_bar = gtk.MenuBar()

    def getM(t):
      return self._resources.get_resource_of_type(MenuResource,t)
    def getMI(t):
      return self._resources.get_resource_of_type(MenuItemResource,t)

    file_menu_item = gtk.MenuItem(getM('main_menu.file').text)
    file_menu = gtk.Menu()
    file_menu_item.set_submenu(file_menu)
    self.file_menu = file_menu; # remember it, let it be extended

    exit_item = gtk.MenuItem(getMI('main_menu.file.exit').text)
    exit_item.connect_object("activate", self._on_exit, None)
    file_menu.append(exit_item)


    menu_bar.append(file_menu_item)

    # debug menu
    debug_menu_item = gtk.MenuItem(getM("main_menu.debug").text)
    debug_menu = gtk.Menu()
    debug_menu_item.set_submenu(debug_menu)
    self.debug_menu = debug_menu
    menu_bar.append(debug_menu_item)

    # tools menu
    tools_menu_item = gtk.MenuItem(getM('main_menu.tools').text)
    tools_menu = gtk.Menu()
    tools_menu_item.set_submenu(tools_menu)
    self.tools_menu = tools_menu
    menu_bar.append(tools_menu_item)

    # tabs menu
    tabs_menu_item = gtk.MenuItem(getM('main_menu.tabs').text)
    tabs_menu = gtk.Menu()
    tabs_menu_item.set_submenu(tabs_menu)
    self.tabs_menu = tabs_menu
    menu_bar.append(tabs_menu_item)

    menu_bar.show_all()
    return menu_bar

  def _on_key_press_event(self,w,event):
#    log3("Processing %s", event)
    for ovl in self._overlays:
      if ovl._handle_key_press(event):
        return True
    keyname = gtk.gdk.keyval_name(event.keyval)
    if keyname == 'F10': # eat f10 in all cases...
      return True
    if keyname == 'Escape' and event.state == 0:
      if self._handle_escape_pressed():
        log3("Escape was handled by MainWindow.last_chance_escape_handler")
        return True

  def _on_delete_event(self,*args):
    return False # let the delete proceed

  def _init_window(self):
    self.set_title("Nicer Debugger")
    self.add_events(gtk.gdk.KEY_PRESS_MASK)

    self.connect_object("destroy", self._on_destroy, None)
    self.connect_object("delete_event", self._on_delete_event, None)

    # keypress hook for pesky keys
    self.connect('key_press_event', self._on_key_press_event)

    # primary objects
    menu_bar = self._make_menu()
    butter_bar_collection = ButterBarCollection()
    butter_bar_collection.show()
    cstage = gtk.VBox()
    cstage.show()
    panel1 = TabPanel(self,"panel1")
    panel2 = TabPanel(self,"panel2")

    # save the important ones
    self._menu_bar = menu_bar
    self._butter_bar_collection = butter_bar_collection
    self._cstage = cstage
    self._panels = {}
    for panel in [panel1, panel2]:
      self._panels[panel.id] = panel

    # layout objects
    vbox = gtk.VBox()
    vbox.show()

    vpane = BetterVPaned()
    vpane.id = "vpane1"
    vpane.position_gravity = BETTER_PANE_POSITION_GRAVITY_END
    vpane.show()

    hpane = BetterHPaned()
    hpane.id = "vpane2"
    hpane.position_gravity = BETTER_PANE_POSITION_GRAVITY_RELATIVE
    hpane.show()

    self._pending_save = None
    self._splitters = [vpane, hpane]
    self._init_sizes()

    # add them together
    self.add(vbox)

    vbox.pack_start(menu_bar, False,False, 0)
    vbox.pack_start(butter_bar_collection, False,False, 0)
    vbox.pack_start(vpane,True,True,0)
    vpane.pack1(cstage)
    vpane.pack2(hpane)
    hpane.pack1(panel1)
    hpane.pack2(panel2)

    self._pane_default_positions = {
      vpane.id :  150,
      hpane.id :  50,
      }

  @property
  def panels(self):
    return self._panels

  @property
  def butter_bar_collection(self):
    return self._butter_bar_collection

  @property
  def menu_bar(self):
    return self._menu_bar
  def add_center_stage(self,widget):
    if len(self._cstage.get_children()) != 0:
      raise Exception("Center stage full")

    self._cstage.add(widget) 
    widget.show()

  ###########################################################################
  def _init_sizes(self):
    self._settings.register("WindowSize", dict, {})
    try:
      self.set_size_request(self._settings.WindowSize["width"], self._settings.WindowSize["height"])
#      print "MainWindow: Using saved size"
    except KeyError:
#      print "MainWindow: Using default size"
      self.set_size_request(750,650)

      
    self._settings.register("SplitterSizes", dict, {})

    # add listeners
    self.connect('size-allocate', self._window_size_changed)
    for splitter in self._splitters:
      splitter.position_changed.add_listener(self._splitter_position_changed)

    # update pane sizes
    self._update_splitter_sizes()


  def _window_size_changed(self, *args):
    if self._layout_changing:
      return
    self._save_sizes()

  def _splitter_position_changed(self):
    assert self._layout_changing == False
    self._save_sizes()

  def _update_splitter_sizes(self):
    if self._layout == None:
      return
#    print "MW: Splitter layout updating"
    self._layout_changing = True
    splitter_sizes =  self._settings.SplitterSizes
    for splitter in self._splitters:
      assert hasattr(splitter,'id')
      if splitter_sizes.has_key(self._layout) == False:
        splitter_sizes[self._layout] = {}
      if splitter_sizes[self._layout].has_key(splitter.id):
        pos = splitter_sizes[self._layout][splitter.id]
#        print "%s: spos %s->%s"  % (self._layout, splitter.id,pos)
        splitter.set_position(pos)
      else:
        if self._pane_default_positions.has_key(splitter.id):
#          print "setting position %i" % self._pane_default_positions[splitter.id]
          splitter.set_position(self._pane_default_positions[splitter.id])

    def stop_ignoring_changes():
#      import pdb; pdb.set_trace()
      assert self._pending_stop_ignoring_changes_message
      self._pending_stop_ignoring_changes_message = None
      self._layout_changing = False
#      print "MW: Splitter layout completely done"
    if self._pending_stop_ignoring_changes_message:
      self._pending_stop_ignoring_changes_message.cancel()
    self._pending_stop_ignoring_changes_message = MessageLoop.add_cancellable_delayed_message(stop_ignoring_changes, 250)
    
  def _save_sizes(self):
#    import traceback
#    traceback.print_stack()

    if self._layout == None:
      return

    size = self.get_allocation()
    if self.get_window().get_state() & (gtk.gdk.WINDOW_STATE_MAXIMIZED | gtk.gdk.WINDOW_STATE_ICONIFIED) == 0:
      newSize = {"width" : size.width, "height" : size.height}
      if pson.dumps(newSize) != pson.dumps(self._settings.WindowSize):
#        print "window size changed"
        self._settings.WindowSize = newSize

    import copy
    splitter_sizes = copy.deepcopy(self._settings.SplitterSizes)
    needs_commit = False
    for splitter in self._splitters:
      if splitter_sizes.has_key(self._layout) == False:
        splitter_sizes[self._layout] = {}
      if splitter_sizes[self._layout].has_key(splitter.id) and splitter.get_position() != splitter_sizes[self._layout][splitter.id]:
 #       print "%s: save %s<-%s" % (self._layout, splitter.id, splitter.get_position())
        needs_commit = True
      elif not splitter_sizes[self._layout].has_key(splitter.id):
#        print "%s: save %s<-%s" % (self._layout, splitter.id, splitter.get_position())
        needs_commit = True
#      import pdb; pdb.set_trace()
      splitter_sizes[self._layout][splitter.id] = splitter.get_position()
    if needs_commit:
      self._settings.SplitterSizes = splitter_sizes

  @property
  def layout(self):
    return self._layout

  @layout.setter
  def layout(self,layout):
#    print "MW: Layout changing"
    self._layout = layout
    MainWindowOverlay.set_layout(self._settings, self, layout)
    self._update_splitter_sizes()
#    print "MW: Layout change done. Splitter change pending."
