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
import re

def liststore_get_children(ls):
  res = []
  for i in range(0,ls.iter_n_children(None)):
    iter = ls.iter_nth_child(None,i)
    res.append(iter)
  return res

class _PListIter(object):
  def __init__(self,pls,iter):
    self._pls = pls
    self._iter = iter
    self._initialized = True
    
  def __getattr__(self,k):
    if self.__dict__.has_key(k):
      return self.__dict__[k]
    else:
      i = self._pls._name_to_index[k]
      return self._pls.get_value(self._iter,i)
    
  def __setattr__(self,k,v):
    if self.__dict__.has_key("_initialized"):
      i = self._pls._name_to_index[k]
      self._pls.set(self._iter,i,v)
      return v
    else:
      return object.__setattr__(self,k,v)

class PListStore(gtk.ListStore):
  def __init__(self, **kwargs):
    keys = list(range(len(kwargs)))
    types = list(range(len(kwargs)))
    has_pos = False
    has_nonpos = False
    i = 0
    for k in kwargs.keys():
      m = re.match("(.+)_(\d+)",k)
      if m:
        if has_nonpos:
          raise Exception("Cant mix _n arguments with implicitly positioned arguments")
        pos = int(m.group(2))
        types[pos] = kwargs[k]
        keys[pos] = m.group(1)
        has_pos = True
      else:
        if has_pos:
          raise Exception("Cant mix _n arguments with implicit positioned")
        pos = i
        i += 1
        keys[pos] = k
        types[pos] = kwargs[k]
        has_nonpos = True        

    self._is_nonpos = has_nonpos

    gtk.ListStore.__init__(self, *types)
    self._types = types
    self._num_columns = len(keys)
    self._column_names = keys
    self._name_to_index = {}
    self._is_nonpos = has_nonpos
    
    for i in range(0,self._num_columns):
      self._name_to_index[self._column_names[i]] = i

    self._initialized = True
      
  def append(self,*args,**kwargs):
    if len(args) == 0 and len(kwargs) == 0:
      iter = gtk.ListStore.append(self)
      return _PListIter(self,iter)
    elif len(args) == self._num_columns:
      if self._is_nonpos:
        raise Exception("Must use kwargs for append.")
      iter = gtk.ListStore.append(self)
      for i in range(0,self._num_columns):
        self.set(iter,i,args[i])
      return _PListIter(self,iter)
    elif len(kwargs) == self._num_columns:
      iter = gtk.ListStore.append(self)
      for k in kwargs:
        i = self._name_to_index[k]
        self.set(iter,i,kwargs[k])
      return _PListIter(self,iter)

  def __len__(self):
    return self.iter_n_children(None)

  def __getitem__(self,idx):
    if type(idx) == int:
      return _PListIter(self,self.iter_nth_child(None,idx))
    elif type(idx) == gtk.TreeIter:
      return _PListIter(self,idx)
    else:
      raise Exception("Must be int or iter, got %s" % type(idx))

  def __iter__(self):
    for i in range(len(self)):
      yield self[i]
    
  def __getattr__(self,k):
    if self.__dict__.has_key(k):
      return self.__dict__[k]
    else:
      i = self._name_to_index[k]
      return i

  def find(self,pred):
    for i in range(len(self)):
      d = self[i]
      if pred(d):
        return d
             
  def remove(self,iter):
    if type(iter) != _PListIter:
      raise Exception("Expected plistiter")
    gtk.ListStore.remove(self,iter._iter)

class PListView(gtk.TreeView):
  def __init__(self, pls, **kwargs):
    self._pls = pls
    gtk.TreeView.__init__(self, pls)
    
    poslogic = False
    neglogic = False
    for k in kwargs:
      if kwargs[k] == True:
        poslogic = True
      elif kwargs[k] == False:
        neglogic = True
      else:
        raise Exception("Values must be true or false")

    if poslogic and neglogic:
      raise Exception("Make the args true or false but dont mix them")
    if not poslogic and not neglogic:
      raise Exception("Must pass one column to enable or disable")
    
    cols = []
    if poslogic:
      cols=kwargs.keys
    else: # neglogic
      cols=list(pls._name_to_index.keys())
      for k in kwargs.keys():
        cols.remove(k)

    # create views
    txtCell = gtk.CellRendererText()
    pixCell = gtk.CellRendererPixbuf()
    for c in cols:
      i = pls._name_to_index[c]
      t = pls._types[i]
      if t == str:
        col = gtk.TreeViewColumn(c, txtCell, text=i)
      elif t == gtk.gdk.Pixbuf:
        col = gtk.TreeViewColumn(c, pixCell, pixbuf=i)
      else:
        raise Exception("Dont understand waht to do with %s" % t)
      self.append_column(col)

  def get_selected(self):
    sel = self.get_selection()
    m,iter = sel.get_selected()
    if iter:
      return _PListIter(self._pls,iter)
    else:
      return None
  def set_selected(self,iter):
    if iter == None:
      self.get_selection.set_selected(None)
      return
    if type(iter) != _PListIter:
      raise Exception("Expected plistiter")
    sel = self.get_selection()
    sel.set_selected(iter._iter)

if __name__ == "__main__":
  w = gtk.Window()
  ls = PListStore(Name_0 = str, Description_1  = str, Key_2 = object)
  print "expect 0 got %s" % ls.Name
  print "expect 1 got %s" % ls.Description
  print "expect 2 got %s" % ls.Key

  ls.append("1", "2", "3")
  ls.append("4", "5", "6")
  r = ls.append()
  r.Name = "7"
  r.Description = "8"
  r.Key = "9"
  print "expect 3 got %s" % len(ls)  
  
  print "expect 1 got %s" % ls[0].Name
  print "expect 2 got %s" % ls[0].Description
  print "expect 3 got %s" % ls[0].Key

  print "expect 5 got %s" % ls[1].Description

  ls[0].Key = "**3**"
  print "expect **3** got %s" % ls[0].Key
  
  tv = PListView(ls, Key = False)
  
  w.add(tv)
  w.show_all()
  gtk.main()
