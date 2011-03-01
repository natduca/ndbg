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
import sys
import random
import cPickle as pickle
import StringIO

from base import *
from collections import *
from vec2 import *
import math

# Node
###########################################################################
class Node(object):
  def __init__(self,name):
    self.__init_common__()
    self._name = name
    self._label = "%s" % name
    self._position = vec2(0,0)
    self._border_color = "black"
    self._background_color = "white"
    self._text_color = "black"
    
  def __init_common__(self):
    # innards
    self._graph = None
    self._cur_force = vec2(0,0)
    self._last_drawn_size = vec2(0,0)
    self._mouse_enter = Event()
    self._mouse_leave = Event()
    self._clicked = Event()

  # name
  name = property(lambda self: self._name)

  def __getinitargs__(self):
    return (self.name,)

  # label
  def set_label(self,val):
    print "setlabel called"
    self._label = val
    self._on_changed(needsLayout=True)
  label = property(lambda self: self._label, set_label)

  # text_color
  def set_text_color(self,val):
    self._text_color = val
    self._on_changed()
  text_color = property(lambda self: self._text_color, set_text_color)

  # border_color
  def set_border_color(self,val):
    self._border_color = val
    self._on_changed()
  border_color = property(lambda self: self._border_color, set_border_color)

  # background_color
  def set_background_color(self,val):
    self._background_color = val
    self._on_changed()
  background_color = property(lambda self: self._background_color, set_background_color)

  # position
  def set_position(self,val):
    self._position = val
    self._on_changed(needsLayout=True)
  position = property(lambda self: self._position, set_position)

  # events
  mouse_enter = property(lambda self: self._mouse_enter)
  mouse_leave = property(lambda self: self._mouse_leave)
  clicked = property(lambda self: self._clicked)


  # Innards
  def _set_graph(self,g):
    self._graph = g

  def _on_changed(self,needsLayout=False):
    if self._graph:
      self._graph._on_changed(needsLayout)


# Edge
###########################################################################
_DEFAULT_EDGE_LENGTH = 0.01
class Edge(object):
  def __init_common__(self):
    self._graph = None
    self._length = _DEFAULT_EDGE_LENGTH
    self._color = "#404040"
    self._weight = 2
    
  def __init__(self,node1,node2):
    self.__init_common__()
    if node2.name < node1.name:
      node1,node2=node2,node1
    self._node1 = node1
    self._node2 = node2

  def __getinitargs__(self):
    return (self.node1,self.node2)

  # nodes
  node1 = property(lambda self: self._node1)
  node2 = property(lambda self: self._node2)

  # name
  name = property(lambda self: "%s--%s" % (self._node1.name,self.node2.name))

  # color
  def set_color(self,val):
    self._color = val
    self._on_changed()
  color = property(lambda self: self._color, set_color)

  # weight
  def set_weight(self,val):
    self._weight = val
    self._on_changed()
  weight = property(lambda self: self._weight, set_weight)
  
  # innards
  def _set_graph(self,g):
    self._graph = g

  def _on_changed(self,needsLayout=False):
    if self._graph:
      self._graph._on_changed(needsLayout)

# Graph
###########################################################################
_KK = 0.1
_INIT_ITER = 0
_INITIAL_TEMPERATURE = 0.05
_TEMP_CURVE = [ vec2(_INIT_ITER,    _INITIAL_TEMPERATURE),
                vec2(_INIT_ITER+100, _INITIAL_TEMPERATURE * 0.5),
                vec2(_INIT_ITER+125,_INITIAL_TEMPERATURE * 0.00),
                vec2(_INIT_ITER+1000000,0.0)
                ]

class Graph(object):
  def __init__(self):
    self._nodes = NamedItemList()
    self._nodes.changed.add_listener(self._on_changed)
    self._nodes.item_added.add_listener(self._on_node_added)
    self._edges = NamedItemList()
    self._edges.changed.add_listener(self._on_changed)
    self._edges.item_added.add_listener(self._on_edge_added)
    self._init_layout()
    self._bounds = None
    self._bounds_dirty = True
    self._needs_layout = False
    self._changed = Event()

  # save/load
  def __getstate__(self):
    n = list(self._nodes)
    e = list(self._edges)
    return {"nodes" : n,
     "edges" : e }
  
  def __setstate__(self,d):
    self.__init__()
    nn = d["nodes"]
    ee = d["edges"]
    for n in nn:
      self._nodes.add(n)
    for e in ee:
      self._edges.add(e)
    self._needs_layout = False

  changed = property(lambda self: self._changed)

  def get_nodes(self):
    return self._nodes
  nodes = property(get_nodes)

  def get_edges(self):
    return self._edges
  edges = property(get_edges)

  def make_edge(self,node1,node2):
    e = Edge(node1,node2)
    self.edges.add(e)

  needs_layout = property(lambda self: self._needs_layout)

  def get_bounds(self):
    if self._bounds_dirty:
      b = DynObject()
      b.lo = vec2()
      b.hi = vec2()
      if len(self._nodes):
        b.lo.x = min([n._position.x for n in self._nodes])
        b.lo.y = min([n._position.y for n in self._nodes])
        b.hi.x = max([n._position.x for n in self._nodes])
        b.hi.y = max([n._position.y for n in self._nodes])
      self._bounds = b
      self._bounds_dirty = False
#      print "Computed bounds: %s - %s" % (str(b.lo),str(b.hi))
    return self._bounds
  bounds = property(get_bounds)

  # dot conversion
  def write_dot(self,f):
    f.write("graph G {\n");
    for n in self.nodes:
      f.write("  \"%s\" [label=\"%s\"];\n" % (n.name, n.label))
    for e in self.edges:
      f.write("  \"%s\" -- \"%s\";\n" % (e.node1.name, e.node2.name))
    f.write("}\n");
  def to_dot(self):
    f = StringIO.StringIO()
    self.write_dot(f)
    return f.getvalue()

  # innards
  def _on_changed(self,needsLayout=False):
    if needsLayout:
      self._needs_layout = True
      self._bounds_dirty = True
    self._changed.fire()

  def _on_node_added(self,node):
    node._set_graph(self)
    node.position.set(random.random(),random.random())
    node._cur_force.set(0,0)
    self._bounds_dirty = True
    self._needs_layout = True

  def _on_edge_added(self,edge):
    edge._set_graph(self)
    self._needs_layout = True

  # spring simulation
  def _init_layout(self):
    self._iter = _INIT_ITER
    self._update_temperature()

  def _update_temperature(self):
    for i in range(1, len(_TEMP_CURVE)):
      if self._iter >= _TEMP_CURVE[i-1].x and self._iter < _TEMP_CURVE[i].x:
        s0 = _TEMP_CURVE[i-1]
        s1 = _TEMP_CURVE[i]
        perc_to_s1x = (self._iter - s0.x) / (s1.x - s0.x)
        self._temperature = ((s1.y - s0.y)* perc_to_s1x) + s0.y
        break
    if self._temperature == 0.0:
      self._iter = _INIT_ITER
      self._update_temperature();
      self._needs_layout = False
    else:
      self._iter += 1
      self._needs_layout = True


  def layout(self):
#    print "Layout: iter=%i temp=%f" % (self._iter, self._temperature)
    for e in self._edges:
      l_ideal = e._length
      f_to_t = vec2_sub(e.node2.position,e.node1.position)
      l_now = vec2_length(f_to_t)
      f_to_t_norm = vec2_scale(f_to_t, 1/l_now)
      disp = (l_ideal - l_now)
      disp_vec = vec2_scale(f_to_t_norm,(disp*disp)/_KK)
      vec2_accum(e._node1._cur_force,disp_vec)
      vec2_neg_accum(e._node2._cur_force,disp_vec)

    for n1 in self._nodes:
      for n2 in self._nodes:
        if n1 == n2:
          continue
        n1_to_n2 = vec2_sub(n2._position,n1._position)
        l_sqr = vec2_length_sqared(n1_to_n2)
        if l_sqr == 0:
          print "%s at %s and %s at %s are co-incident" % (n1.name,n1.position,n2.name,n2.position)
          continue
        l = math.sqrt(l_sqr)
        n1_to_n2_norm = vec2_scale(n1_to_n2,1/l)
        rep = (_KK*_KK) / l
        rep_vec = vec2_scale(n1_to_n2_norm,rep)
        vec2_neg_accum(n1._cur_force,rep_vec)

    # ove nodes
    for n in self._nodes:
      if n._cur_force.x == 0 and n._cur_force.y == 0:
        continue
      f = vec2_normalize(n._cur_force)
      ff= vec2_scale(f,self._temperature)
      n._position = vec2_add(n.position, ff)
      n._cur_force.set(0,0) # zero it out again

    # anneal the system... helps get past local minima
    # find new temperature based on _iter
    self._update_temperature()

    self._bounds_dirty = True

def testGraph():
  graph = Graph()
  n = []
  for i in range(0,8):
    node = Node("n%i"%i)
    n.append(node)
    graph.nodes.add(node)
  n[0].background_color = "blue"
  n[0].foreground_color = "yellow"
  graph.make_edge(n[0],n[1])
  graph.make_edge(n[1],n[2])
  graph.make_edge(n[2],n[3])
  graph.make_edge(n[2],n[4])
  graph.make_edge(n[3],n[4])
  graph.make_edge(n[4],n[5])
  graph.make_edge(n[0],n[6])
  graph.make_edge(n[0],n[7])

  return graph

if __name__ == "__main__":
  g = testGraph()
  data= pickle.dumps(g)
  g_ = pickle.loads(data)
  StringIO.StringIO()
  print g_.to_dot()
