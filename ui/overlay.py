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


# An overlay is a set of additions to the debugger UI made by a specific module.
# This includes menus, hotkeys, and so on.
#
# Overlays can be enabled and disabled. When disabled, this causes menus specific
# to the overlay to disappear.
#
# Use of overlays ensures that individual tabs in the UI can contribute to the overall
# UI without having to in-turn centralize the UI in a single implementation import gtk

from util import *
from resources import *
from main_window import *

class MainWindowOverlay(object):
  @staticmethod
  def _register_tab_prefs(settings):
    settings.register("TabPanelAssignments", dict, {})

  @staticmethod
  def _update_tab_prefs(settings,mw,layout):
#    log1("Updating prefs for layout %s", layout)
    import copy
    tab_panels = copy.deepcopy(settings.TabPanelAssignments)
    needs_commit = False
    for ovl in mw.overlays:
      for tab in ovl._tabs:
        panel = tab.get_parent()
        if panel and panel.get_property('visible'):
          if not tab_panels.has_key(layout):
            tab_panels[layout] = {}
            needs_commit = True
          if not tab_panels[layout].has_key(tab.id):
            needs_commit = True
          else:
            if tab_panels[layout][tab.id] != panel.id:
              needs_commit = True
              
#          if needs_commit:
#            log2("%s: %s parent = %s",layout, tab.id, panel.id)
          tab_panels[layout][tab.id] = panel.id
    if needs_commit:
      settings.TabPanelAssignments = tab_panels

  @staticmethod
  def set_layout(settings, mw, layout):
    for ovl in mw.overlays:
      ovl.layout = layout

  def __init__(self,mw,settings,name,initial_layout):
    MainWindowOverlay._register_tab_prefs(settings)
    self._settings = settings
    self._mw = mw
    self._name = name
    self._items = []
    self._tab_items = []
    self._ag = gtk.AccelGroup()
    self._f10_item = None
    self._hotkeys = []
    self._attached = False
    self._visible = True
    self._enabled = True
    self._tabs = []
    self._layout = initial_layout
    self._layout_changing = False
    self.attached = True # trigger ag attachment

  def destroy(self):
    for i in self._items:
      i.destroy()

  def add_file_menu_item(self,resource_name,cb,userdata=None):
    return self._add_menu_item('file_menu',resource_name,cb,userdata)

  def add_debug_menu_item(self,resource_name,cb,userdata=None):
    return self._add_menu_item('debug_menu',resource_name,cb,userdata)

  def add_tabs_menu_item(self,resource_name,cb,userdata=None):
    return self._add_menu_item('tabs_menu',resource_name,cb,userdata)

  def add_tools_menu_item(self,resource_name,cb,userdata=None):
    return self._add_menu_item('tools_menu',resource_name,cb,userdata)

  def add_keyboard_action(self,resource_name,cb):
#    print "Add %s %x" % (keyname,modifiers)
    resource = self._mw.resources.get_resource_of_type(KeyboardActionResource,resource_name)
    a = DynObject()
    a.keyname = resource.keyname
    a.modifiers = resource.modifiers
    a.cb = cb
    self._hotkeys.append(a)

  def find_tab(self,tab_type):
    """
    Finds a tab of a given type.
    """
    for t in self._tabs:
      if type(t) == tab_type:
        return t

  def find_tab_by_id(self,id):
    """
    Finds a tab of a given type.
    """
    for t in self._tabs:
      if t.id == id:
        return t

  @property
  def name(self):
    return self._name
  @property
  def tabs(self):
    return list(self._tabs)
  @property
  def attached(self):
    return self._attached
  @attached.setter
  def attached(self,v):
    if type(v) != bool:
      raise TypeError("Expected bool")
    if self._attached == v:
      return
    if self._attached and v == False:
      for i in self._items:
        i.detach()
      self._mw.remove_accel_group(self._ag)
    elif self._attached == False and v == True:
      self._mw.add_accel_group(self._ag)
      for i in self._items:
        i.attach()
    self._attached = v

  @property
  def enabled(self):
    return self._enabled
  @enabled.setter
  def enabled(self,v):
    if type(v) != bool:
      raise TypeError("Expected bool")
    if self._enabled == v:
      return
    if v:
      for i in self._items:
        i.enable()
    else:
      for i in self._items:
        i.disable()
    self._enabled = v


  @property
  def visible(self):
    return self._visible
  @visible.setter
  def visible(self,v):
    if type(v) != bool:
      raise TypeError("Expected bool")
#    if self._visible == v:
#      return
    if v:
      for i in self._items:
        i.show()
    else:
      for i in self._items:
        i.hide()
    self._visible = v

  @property
  def layout(self):
    return self._layout
  @layout.setter
  def layout(self,layout):
    self._layout_changing = True
    self._layout = layout
    # change owners of all tabs
    for oitem in self._tab_items:
      oitem.detach()
      oitem.attach() # reattaches to new layout
    self._layout_changing = False
    MainWindowOverlay._update_tab_prefs(self._settings, self._mw, layout)

  def _add_menu_item(self,base_menu_name,resource_name,cb,userdata):
    resource = self._mw.resources.get_resource_of_type(MenuItemResource, resource_name)
    text = resource.text
    key = resource.keyname
    mod = resource.modifiers

    item = gtk.MenuItem(text)
    if key == 0 or key == None:
      kv = 0
    else:
      kv = gtk.accelerator_parse(key)[0]
    if kv != 0:
      item.add_accelerator("activate", self._ag, kv, mod, gtk.ACCEL_VISIBLE)
    if key == 'F10' and mod == 0:
      self._f10_item = item
    def dispatch(a,b):
      if item.get_sensitive():
        cb(a,b)
    item.connect("activate", dispatch,userdata)

#    def on_show(*args):
#      print "%s shown"% item.get_label()
#      import pdb; pdb.set_trace()
#    item.connect("show", on_show)

    def attach():
      m = getattr(self._mw, base_menu_name)
      m.append(item)
      if self._visible:
        item.show()
        m.show()
        
    def detach():
      m = getattr(self._mw, base_menu_name)
      m.remove(item)
      if len(m.get_children()) == 0:
        m.hide()
    def show():
      item.show()
    def hide():
      item.hide()
    def enable():
      item.set_sensitive(True)
    def disable():
      item.set_sensitive(False)

    oitem = _OverlayItem()
    oitem.attach = attach
    oitem.detach = detach
    oitem.show = show
    oitem.hide = hide
    oitem.enable = enable
    oitem.disable = disable
    self._items.append(oitem)
    self._tab_items.append(oitem)
    oitem.init(self) # make sure that the new item is sync'd with our attach/enable/visible state

  def add_tab(self,tab,tab_id):
    if tab_id in self._mw._ids_in_use:
      raise Exception("ID %s is already in use." % tab_id)
    self._mw._ids_in_use.add(tab_id)
    tab.id = tab_id

    resource = self._mw.resources.get_resource_of_type(TabPageResource,tab_id)

    self._tabs.append(tab)

    def attach():
      if self._mw.panels.has_key(resource.panel_id):
        panel = self._mw.panels[resource.panel_id]
      else:
        log0("Unrecognized panel %s in resource %s", resource.panel_id, tab_id)
        panel = self._mw.panels["panel1"]
        
      if self._settings.TabPanelAssignments.has_key(self._layout):
        if self._settings.TabPanelAssignments[self._layout].has_key(tab_id):
          panel_id = self._settings.TabPanelAssignments[self._layout][tab_id]
          if self._mw.panels.has_key(panel_id):
            panel = self._mw.panels[panel_id]
#            print "%s: tab %s using panel from settings %s" % (self._layout, tab_id, panel.id)          
          else:
            log0("Unrecognized panel in setting: %s" % panel_id)
        else:
#          print "%s: tab %s using default panel assignment %s (no specific assignment)" % (self._layout, tab_id, panel.id)          
          pass
      else:
#        print "%s: tab %s using default panel assignment %s (no layout)" % (self._layout, tab_id, panel.id)
        pass

      panel.add_tab(tab,resource.title, self)
    def detach():
      panel = tab.get_parent()
      assert isinstance(panel, TabPanel)
      panel.remove_tab(tab)
    def show():
      tab.show_all()
      tab.get_parent().update_visibility()
    def hide():
      tab.hide()
      visible = False
      p = tab.get_parent()
      p.update_visibility()
    def enable():
      tab.set_sensitive(True)
    def disable():
      tab.set_sensitive(False)
    def destroy():
      if tab.destroy:
        tab.destroy()
    oitem = _OverlayItem()
    oitem.attach = attach
    oitem.detach = detach
    oitem.show = show
    oitem.hide = hide
    oitem.enable = enable
    oitem.disable = disable
#    oitem.destroy = destroy

    if not tab.get_property('visible'):
      log0("Warning: tab %s was added but was not shown.", tab_id)
      tab.show()

    self._items.append(oitem)
    oitem.init(self) # make sure that the new item is sync'd with our attach/enable/visible state

  def on_tab_panel_changed(self, tab, panel):
    if self._layout_changing:
      return
    MainWindowOverlay._update_tab_prefs(self._settings, self._mw, self._layout)

  def _handle_key_press(self,event):
#    print "handle f10 and f10_teim is %s" % self._f10_item
    if self._attached == False or self._enabled == False or self._visible == False:
      return
    if event.is_modifier:
      return
    keyname = gtk.gdk.keyval_name(event.keyval)

#    log3("%s: Processsing key %s mod=0x%x", self.name, keyname,event.state)
    if keyname == 'F10':
      if self._mw and self._f10_item:
        self._f10_item.emit('activate')
        return True
    else:
      for a in self._hotkeys:
#        log3("%s: Considering %s %x", self.name, a.keyname, a.modifiers)
        if a.keyname == keyname and a.modifiers == (event.state):
          log3("%s: will handle %s %x", self.name, a.keyname, a.modifiers)
          a.cb()
          return True
    return False

class _OverlayItem(object):
  def __init__(self):
    self._attach = lambda : None
    self._detach = lambda : None
    self._show = lambda : None
    self._hide = lambda : None
    self._destroy = lambda: None
    self._enable = lambda : None
    self._disable = lambda : None


  @property
  def attach(self):
    return self._attach
  @attach.setter
  def attach(self,v):
    self._attach = v
  @property
  def detach(self):
    return self._detach
  @detach.setter
  def detach(self,v):
    self._detach = v


  @property
  def enable(self):
    return self._enable
  @enable.setter
  def enable(self,v):
    self._enable = v

  @property
  def disable(self):
    return self._disable
  @disable.setter
  def disable(self,v):
    self._disable = v

  @property
  def show(self):
    return self._show
  @show.setter
  def show(self,v):
    self._show = v

  @property
  def hide(self):
    return self._hide
  @hide.setter
  def hide(self,v):
    self._hide = v

  @property
  def destroy(self):
    return self._destroy
  @destroy.setter
  def destroy(self, v):
    self._destroy = v

  def init(self,ovl):
    if ovl.attached:
      self._attach()

    if ovl.visible == False:
      self._hide()

    if ovl.enabled == False:
      self._disable()

