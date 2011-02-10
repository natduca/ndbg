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
import re
import inspect
class ValidationException(Exception):
  def __init__(self,msg):
    Exception.__init__(self,msg)
    self.message = msg

class InterfaceValidator(object):
  def __init__(self, that, defer_validation=False):
    """If defer_validation is true, then we will not raise exceptions until validate is called"""
    self._defer_validation = defer_validation
    if inspect.isclass(that):
      self._class = that
    else:
      if not that.__class__:
        raise Exception("omg wtf did you pass me?")
      self._class = that.__class__
    self._errors = []

  def expect_method(self,namesig):
    m = re.match("(\S+)(\(.*\))", namesig)
    if not m:
      raise Exception("namesig must be of form foo(args)")
    name = m.group(1)
    sig = m.group(2)
    if re.search(",\S+", sig):
      raise Exception("arguments must be separated by spaces")
    if re.search("\(\s+", sig):
      raise Exception("no space between opening paren and first argument")
    if re.search("\s+\)", sig):
      raise Exception("no space between last argument and closing paren")

    try:
      method = getattr(self._class, name)
    except AttributeError:
      method = None
    if not method:
      self._error("%s%s: Missing method" % (name, sig))
      return

    if not inspect.ismethod(method):
      self._error("%s%s: Not a method. (got %s)" % (name, sig, type(method)))
      return
    cur_sig = inspect.formatargspec(*inspect.getargspec(method))
    if cur_sig != sig:
      self._error("%s%s: wrong signature (got %s)" % (name, sig, cur_sig))
      return

  def expect_staticmethod(self,namesig):
    m = re.match("(\S+)(\(.*\))", namesig)
    if not m:
      raise Exception("namesig must be of form foo(args)")
    name = m.group(1)
    sig = m.group(2)
    if re.search(",\S+", sig):
      raise Exception("arguments must be separated by spaces")
    if re.search("\(\s+", sig):
      raise Exception("no space between opening paren and first argument")
    if re.search("\s+\)", sig):
      raise Exception("no space between last argument and closing paren")

    try:
      method = getattr(self._class, name)
    except AttributeError:
      method = None
    if not method:
      self._error("%s%s: Missing static method" % (name, sig))
      return

    if not inspect.isfunction(method):
      self._error("%s%s: Not a static method. (got %s)" % (name, sig, type(method)))
      return
    cur_sig = inspect.formatargspec(*inspect.getargspec(method))
    if cur_sig != sig:
      self._error("%s%s: wrong signature (got %s)" % (name, sig, cur_sig))
      return

  def expect_get_property(self,name):
    if not self._class.__dict__.has_key(name):
      self._error("%s: Missing property" % (name))
      return
    prop = self._class.__dict__[name]
    if not type(prop) == property:
      self._error("%s: Not a property" % (name))
      return
    if not prop.fget:
      self._error("%s: Missing getter" % (name))
    if prop.fset:
      self._error("%s: Should not have setter" % (name))
    if prop.fdel:
      self._error("%s: Should not have deleter" % (name))

  def expect_get_set_property(self, name):
    if not self._class.__dict__.has_key(name):
      self._error("%s: Missing property" % (name))
      return
    prop = self._class.__dict__[name]
    if not type(prop) == property:
      self._error("%s: Not a property" % (name))
      return
    if not prop.fget:
      self._error("%s: Missing getter" % (name))
    if not prop.fset:
      self._error("%s: Missing setter" % (name))
    if prop.fdel:
      self._error("%s: Should not have deleter" % (name))

  def expect_get_set_del_property(self, name):
    if not self._class.__dict__.has_key(name):
      self._error("%s: Missing property" % (name))
      return
    prop = self._class.__dict__[name]
    if not type(prop) == property:
      self._error("%s: Not a property" % (name))
      return
    if not prop.fget:
      self._error("%s: Missing getter" % (name))
    if not prop.fset:
      self._error("%s: Missing setter" % (name))
    if not prop.fdel:
      self._error("%s: Missing deleter" % (name))

  def _error(self,msg):
    if self._defer_validation:
      self._errors.append(msg)
    else:
      raise ValidationException(msg)
  def validate(self):
    if self._errors:
      raise ValidationException("\n".join(self._errors))
    self._errors = []
