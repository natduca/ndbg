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
import cPickle as pickle

from debugger import *
from ui import *
from util import *

from tab_interface import *

###########################################################################
_MAX_DEPTH = 9
class StackExplorer(gtk.VBox):
  def __init__(self,mc):
    TabInterface.validate_implementation(self)
    gtk.VBox.__init__(self)


    self._mc = mc

    # 'toolbar'
    self._tb = gtk.HBox()
    
    explore_button = gtk.Button("Explore")
    explore_button.connect('clicked', self._on_explore_clicked)
    self._tb.pack_start(explore_button,False,False,0)

    # max depth comboboxf
    md_label = gtk.Label("Max depth: ");
    md_combo = gtk.combo_box_new_text()
    for i in range(1,_MAX_DEPTH+1):
      md_combo.append_text("%s" % i)
    md_combo.append_text("No limit");
    md_combo.set_active(_MAX_DEPTH) # "no limit"
    self._maxdepth_combo = md_combo
    self._tb.pack_start(md_label,False,False,4)
    self._tb.pack_start(md_combo,False,False,0)

    # the graph
    self._graph = Graph()
    self._gw = GraphWidget(self._graph)

    self._init_popup()

    # final layout
    self.pack_start(self._tb,False,False,2)
    self.pack_start(gtk.HSeparator(),False,False,2)
    self.pack_start(self._gw,True,True,0)
    self.show_all()

    self._mc.debugger.active_frame_changed.add_listener(self._on_active_frame_changed)

  def _get_maxdepth(self):
    model = self._maxdepth_combo.get_model()
    active = self._maxdepth_combo.get_active()
    if active < 0 or active == _MAX_DEPTH:
      return 100000;
    else:
      return active+1;

  def _init_popup(self):
    popup = gtk.Menu()
    popup.show()
    def on_save(x):
      dlg = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                  buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
      flt = gtk.FileFilter()
      flt.set_name("Graph")
      flt.add_pattern("*.ng");
      dlg.add_filer(flt)
      resp = dlg.run()
      if resp == gtk.RESPONSE_CANCEL:
        return
      filename = dlg.get_filename()
      dlg.destroy()
      
      file = open(filename, 'w')
      pickle.dump(self._graph, file)
      file.close()

    def on_save_as_dot(x):
      dlg = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                  buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
      flt = gtk.FileFilter()
      flt.set_name("Dot file")
      flt.add_pattern("*.dot");
      dlg.add_filter(flt)
      resp = dlg.run()
      if resp == gtk.RESPONSE_CANCEL:
        return
      filename = dlg.get_filename()
      dlg.destroy()
      
      file = open(filename, 'w')
      self._graph.write_dot(file)
      file.close()


    self.popup_save = add_to_menu(popup, "Save", on_save, None)
    self.popup_save = add_to_menu(popup, "Save as dot", on_save_as_dot, None)
    self._popup = popup
    
    def on_button_press(w,event):
      if event.button != 3:
        return
      if self._gw.pick_node_at(event.x,event.y):
        return
      popup.popup(None,None,None,event.button, event.time)
      return True # eat the event
    self._gw.connect("button-press-event", on_button_press)
    
  # tabbase interface
  @property
  def title(self):
    return "Stack Explorer"

  # Highlighting/etc of the current graph
  def _on_active_frame_changed(self):
    if self._mc.debugger.status == STATUS_BREAK:
      self._update_graph_colors_based_on_callstack()

  # highlights 
  def _update_graph_colors_based_on_callstack(self):
    # don' do anything if the layout is off
    if self._gw.layout_enabled == False:
      return
    
    # reset colors of all the graph nodes and edges
    for n in self._graph.nodes:
      if n.background_color != "#b0b0b0":
        n.background_color = "#b0b0b0"
    for e in self._graph.edges:
      if e.color != "#b0b0b0":
        e.color = "#b0b0b0"
      if e.weight != 1:
        e.weight = 1

    if self._mc.debugger.active_thread == None:
      return

    cs = self._mc.debugger.active_thread.call_stack
    active_frame_num = self._mc.debugger.active_thread.active_frame_number
    for frameNum in range(0,len(cs)):
      frame = cs[frameNum]
      if frame.location.has_identifier:
        n = self._graph.nodes.try_get_value(frame.location.identifier)
        if n and frameNum == 0:
          n.background_color = self._mc.resources.COLOR_CURRENT_LINE
        elif n and frameNum == active_frame_num:
          n.background_color = self._mc.resources.COLOR_ACTIVE_FRAME
        elif n:
          n.background_color = "white"

    for frameNum in range(1,len(cs)):
      l0 = cs[frameNum-1].location
      l1 = cs[frameNum-0].location
      if l0.has_identifier==False or l1.has_identifier == False:
        break
      if not self._graph.nodes.has_key(l0.identifier) or not self._graph.nodes.has_key(l1.identifier):
        continue
      n0 = self._graph.nodes[l0.identifier]
      n1 = self._graph.nodes[l1.identifier]
      e = Edge(n0,n1)
      if self._graph.edges.contains(e):
        e = self._graph.edges[e.name]
        e.color = "black"
        e.weight = 4

    

  # explore workflow --- steps down through the graph
  def _on_explore_clicked(self,b):
    self._gw.layout_enabled = False
    
    d = self._mc.debugger
    dlg = gtk.Dialog("Exploring",
                     None,
                     gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                     (gtk.STOCK_OK, gtk.RESPONSE_OK))

    start_stack = d.active_thread.call_stack
    def still_inside(cs):
#      print "Checking insideness."
      for i in range(1, len(start_stack)+1):
#        print "comp %s to %s" % (cs[-i].location, start_stack[-i].location)
        if cs[-i].location.soft_eq(start_stack[-i].location) == False: # use soft eq so we don't fall onto line-numbers
          return False
      return True
    def get_inside_portion(cs):
      dropAmt = len(start_stack)-1
      if dropAmt > 0:
        return cs[:-dropAmt]
      else:
        return cs[:]

    delay = 0.001
    def status_changed():
      if d.status == STATUS_BREAK:
        cs = d.active_thread.call_stack
        if not still_inside(cs):
          print "Done"
          dlg.response(gtk.RESPONSE_OK)
          return
        print "Currently at %s" % cs[0]
        inside_cs = get_inside_portion(cs)
        print "inside cs: %s" % (inside_cs)
        self._add_callstack_to_graph(inside_cs)

        if inside_cs[0].location.has_identifier:
          # see if filemgr recognizes it
          confirm = False
          if inside_cs[0].location.has_file_location:
            resolved_filename = self._mc.filemanager.find_file(inside_cs[0].location.filename)
            confirm = resolved_filename != None
          else:
            confirm = False
            
          # have we exceeded maxdepth?
          if confirm and len(inside_cs) > self._get_maxdepth():
            confirm = False

          if confirm:
            print "step in"
            time.sleep(delay)
            d.active_thread.begin_step_into()
          else:
            print "uninteresting, stepping out"
            time.sleep(delay)
            d.active_thread.begin_step_out()
        else:
          print "step out"
          time.sleep(delay)
          d.active_thread.begin_step_out()
    d.status_changed.add_listener(status_changed)
    d.active_thread.begin_step_into()
    dlg.run()
    dlg.hide()
    d.status_changed.remove_listener(status_changed)

    self._gw.layout_enabled = True
    self._update_graph_colors_based_on_callstack()
    
  # adds  call stack to the graph
  def _add_callstack_to_graph(self, cs):
    g = self._graph

    # make the nodes from the functions in the call stack... stop if we see a non-function
    for frame in cs:
      l = frame.location
      if l.has_identifier == False:
        break
      if not g.nodes.has_key(l.identifier):
        n = Node(l.identifier)
        print "new node: %s" % n.name
        g.nodes.add(n)
    for i in range(1,len(cs)):
      l0 = cs[i-1].location
      l1 = cs[i-0].location
      if l0.has_identifier==False or l1.has_identifier == False:
        break
      n0 = g.nodes[l0.identifier]
      n1 = g.nodes[l1.identifier]
      e = Edge(n0,n1)
      if g.edges.contains(e) == False:
        print "connect: %s - %s" % (n0.name, n1.name)
        g.edges.add(e)


