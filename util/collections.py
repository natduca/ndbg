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
from base import *
from event import *

def find(seq,pred):
  for c in seq:
    if pred(c):
      return c
  return None

def find_first(seq,pred):
  return find(seq,pred)

def remove_first(seq,pred):
  for i in range(len(seq)):
    if pred(seq[i]):
      c = seq[i]
      del seq[i]
      return c
  return None

def diff(iter1,iter2):
  """
  Returns an object with three fields:
    added, removed, unchanged
  """

  s1 = set(iter1)
  s2 = set(iter2)
  
  res = DynObject()
  res.removed = s1.difference(s2)
  res.added = s2.difference(s1)
  res.unchanged = s1.intersection(s2)
  return res

class BindingList(object):
  def __init__(self):
    object.__init__(self)
    self.changed = Event()
    self.item_added = Event()
    self.item_deleted = Event()
    self._array = []

  def __getitem__(self,idx):
    return self._array[idx]

  def __setitem__(self,idx,val):
    oldval = self._array[idx]
    self._array[idx] = val
    self.item_deleted.fire(idx,oldval)
    self.item_added.fire(idx,val)
    self.changed.fire()

  def __delitem__(self,idx):
    oldval = self._array[idx]
    del self._array[idx]
    self.item_deleted.fire(idx,oldval)
    self.changed.fire()

  def append(self,val):
    self._array.append(val)
    self.item_added.fire(len(self._array)-1,val)
    self.changed.fire()

  def append_with_notify_as_closure(self,val):
    self._array.append(val)
    def clos():
      self.item_added.fire(len(self._array)-1,val)
      self.changed.fire()
    return clos


  def remove(self,val):
    for i in range(0,len(self._array)):
      if self._array[i] == val:
        del self[i] # routes to __delitem__
        return
    raise Exception("Element not found")
  def remove_with_notify_as_closure(self,val):
    for i in range(0,len(self._array)):
      if self._array[i] == val:
        oldval = self._array[i]
        del self._array[i]
        def clos():
          self.item_deleted.fire(i,oldval)
          self.changed.fire()
        return clos
    raise Exception("Element not found")

  def __iter__(self):
    for x in self._array:
      yield x

  def __len__(self):
    return len(self._array)

def _test_binding_list():
  b = BindingList()
  def onChanged():
    print "Changed"
  b.changed.add_listener(onChanged)
  print "Append"
  b.append(1)
  print "Append"
  b.append(2)
  print "Access"
  print b[1]
  print "Iter"
  for x in b:
    print x
  print "Del"
  del b[1]



class BindingDict(object):
  def __init__(self):
    object.__init__(self)
    self.changed = Event()
    self.item_added = Event()
    self.item_deleted = Event()
    self._dict = {}

  def __getitem__(self,key):
    return self._dict[key]

  def __setitem__(self,key,val):
    oldval = self._dict[key]
    self._dict[key] = val
    self.item_deleted.fire(key,oldval)
    self.item_added.fire(key,val)
    self.changed.fire()

  def __delitem__(self,key):
    oldval = self._dict[key]
    del self._dict[key]
    self.item_deleted.fire(key,oldval)
    self.changed.fire()

  def add(self,key,val):
    self._dict[key]=val
    self.item_added.fire(key,val)
    self.changed.fire()

  def remove(self,key):
    del self[key] # goes to __delitem__

  def keys(self):
    return self._dict.keys()

  def values(self):
    return self._dict.values()

  def __iter__(self):
    for key in self._dict.keys():
      yield key


# Looks like a list
# But stores things in a dict
# Uses a specified callback fn to generate a key
class IdentifiedItemListBase(object):
  def __init__(self,get_id_fn):
    self._get_id = get_id_fn
    self._changed = Event()
    self._item_added = Event()
    self._item_deleted = Event()
    self._dict = {}

  changed = property(lambda self: self._changed)
  item_added = property(lambda self: self._item_added)
  item_deleted = property(lambda self: self._item_deleted)

  def add(self,i):
    if self._dict.has_key(self._get_id(i)):
      raise Exception("Item exists")
    self._dict[self._get_id(i)] = i
    self._item_added.fire(i)
    self._changed.fire()

  def add_with_notify_as_closure(self,i):
    id = self._get_id(i)
    if self._dict.has_key(id):
      raise Exception("Item exists")
    self._dict[id] = i
    def clos():
      self._item_added.fire(i)
      self._changed.fire()
    return clos

  def contains(self,i):
    return self._dict.has_key(self._get_id(i))

  def has_key(self,k):
    return self._dict.has_key(k)

  def try_get_value(self,k):
    if self._dict.has_key(k):
      return self._dict[k]
    else:
      return None

  @property
  def first(self):
    if len(self._dict) == 0:
      raise IndexError()
    return self._dict[self._dict.iterkeys().next()]

  def remove(self,i):
    id = self._get_id(i)
    i = self._dict[id]
    del self._dict[id]
    self._item_deleted.fire(i)
    self._changed.fire()

  def remove_key(self,id):
    i = self._dict[id]
    del self._dict[id]
    self._item_deleted.fire(i)
    self._changed.fire()


  def remove_with_notify_as_closure(self,i):
    id = self._get_id(i)
    i = self._dict[id]
    del self._dict[id]
    def clos():
      self._item_deleted.fire(i)
      self._changed.fire()
    return clos

  def __getitem__(self,k):
    return self._dict[k]

  def __len__(self):
    return len(self._dict)

  def __iter__(self):
    return self._dict.values().__iter__()

  def values(self):
    return self._dict.values()

def dict_invert(i):
  o = {}
  for k in i.keys():
    v = i[k]
    if o.has_key(v):
      raise Exception("Not invertible")
    o[v] = k
  return o


"""
An identified item list that behaves like a list,
with which stores its items in a dictionary based on
the "id" field of the passed-in item.
Eg.
  class MyItem(
"""
class IdentifiedItemList(IdentifiedItemListBase):
  def __init__(self):
    IdentifiedItemListBase.__init__(self,lambda x: x.id)


class NamedItemList(IdentifiedItemListBase):
  def __init__(self):
    IdentifiedItemListBase.__init__(self,lambda x: x.name)

