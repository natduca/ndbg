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
import types
import pickle
try:
  import gtk
except:
  gtk = None

class DynObject(object):
  def __init__(self,dict=None):
    if dict:
      for k in dict.keys():
        setattr(self,k,dict[k])

  def __str__(self):
    d = {}
    for x in dir(self):
      if not x.startswith("_"):
        d[x] = getattr(self,x)
    return str(d)

  def __repr__(self):
    return self.__str__()

  def __getattr__(self,name):
    raise AttributeError("Object has no attribute %s" % name)

  def __setattr(self,name,val):
    setattr(self,name,val)
    return val

def show_recursive(w):
  w.show()
  if isinstance(w, gtk.Container):
    for c in w.get_children():
      show_recursive(c)
  if isinstance(w, gtk.MenuItem):
    if w.get_submenu():
      show_recursive(w.get_submenu())


def dict_filter(dict,pred):
  d = {}
  for k in dict.keys():
    if pred(k):
      d[k] = dict[k]
  return d

def add_to_menu(menu,title,cb,userdata=None):
  mi = gtk.MenuItem(title)
  mi.connect_object("activate", cb, userdata)
  mi.show()
  menu.append(mi)
  return mi

###########################################################################
import sys
def Property(function):
    keys = 'fget', 'fset', 'fdel'
    func_locals = {'doc':function.__doc__}
    def probe_func(frame, event, arg):
        if event == 'return':
            locals = frame.f_locals
            func_locals.update(dict((k, locals.get(k)) for k in keys))
            sys.settrace(None)
        return probe_func
    sys.settrace(probe_func)
    function()
    print "Property made: %s" % func_locals
    return property(**func_locals)

def Xroperty(fn):
  res = fn()
  if res.has_key('get') and res.has_key('set') and res.has_key('del'):
    return property(res['get'], res['set'], res['del'])
  elif res.has_key('get') and res.has_key('set'):
    return property(res['get'], res['set'])
  elif res.has_key('get'):
    return property(res['get'], res['set'])
  raise Exception("Function must return at least get,set,del or get,set or get");


def auto_getstate(obj):
  fields = [x for x in obj.__class__.__dict__.keys() if not x.startswith("_")]
  d = {}
  for k in fields:
    v = obj.__class__.__dict__[k]
    if isinstance(v,collections.Callable):
      continue
    elif isinstance(v,Event):
      continue
    elif isinstance(v,property):
      val = v.__get__(obj)
      if not isinstance(val,Event):
        d[k] = val
    else:
      raise Exception("Wtf is this")
#      pickle.dumps(v)
#      d[k] = v
  return d

def auto_setstate(obj,d):
  cd = obj.__class__.__dict__
  for k in d:
    v = cd[k]
    if isinstance(v,property):
      v.__set__(obj,d[k])
    else:
      raise Exception("wtf")

def AutoClass(cls):
#  cls.__getstate__ = auto_getstate
#  cls.__setstate__ = auto_setstate
  return cls

#@AutoClass
class _AutoTest():
#  @Property
  def baz():
    """Baz property"""
    def fget(self):
      print "fget"
      return 1
    def fset(self,value):
      print "setting baz to %s" % value
    def fdel(self):
      pass
#      val = v

  

def _test_auto():
  x = _AutoTest()
  print x.baz
  print x.__class__.__dict__
  x.baz = 42
  d = pickle.dumps(x)
  x_ = pickle.loads(d)
  print x_.baz


if __name__ == "__main__":
  _test_binding_list()
#  _test_auto()


class BoxedObject():
  """Simple wrapper for boxing an object. This is useful when you need
  to push a value from an inner function outward."""
  def __init__(self, val = None):
    self._val = val

  def set(self, val):
    self._val = val

  def get(self):
    return self._val

def argn(*args):
  """Returs the last argument. Helpful in making lambdas do more than one thing."""
  return args[-1]

def arg1(*args):
  """Returs args[0]. Helpful in making lambdas do more than one thing."""
  return args[0]

def argif(cond,if_true_value,else_value):
  if(cond):
    return if_true_value
  else:
    return else_value

def argsel(key, default, **kwargs):
  if kwargs.has_key(key):
    return kwargs[key]
  return default
