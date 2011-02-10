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
import unittest
from util import InterfaceValidator,ValidationException

class Example1:
  def __init__(self, a, b):
    pass

  def m1(self):
    pass
  def m2(self, a):
    pass
  def m3(self, a, b=True):
    pass
  def m4(self, *args):
    pass
  def m5(self, bar, *args, **kwargs):
    pass
  def m6(self, bar, baz=True, *args, **kwargs):
    pass

  @property
  def get(self):
    return 1


  @property
  def getset(self):
    return 1

  @getset.setter
  def getset(self,v):
    pass


  @property
  def getsetdel(self):
    return 1

  @getset.setter
  def getsetdel(self,v):
    pass

  @getset.deleter
  def getsetdel(self):
    pass


  @staticmethod
  def s1():
    pass

class InterfaceValidatorArgumentTest(unittest.TestCase):
  def test_constructor(self):
    iv = InterfaceValidator(Example1)
    iv.ensure_method("m1(self)")
    InterfaceValidator(Example1(1,2))
    iv.ensure_method("m1(self)")

  def test_args(self):
    e1 = Example1(1,2)
    iv = InterfaceValidator(e1)
    self.assertRaises(Exception, iv.ensure_method("foo"))
    self.assertRaises(Exception, iv.ensure_method("foo (bar)"))
    self.assertRaises(Exception, iv.ensure_method("foo( bar)"))
    self.assertRaises(Exception, iv.ensure_method("foo(bar )"))
    self.assertRaises(Exception, iv.ensure_method("foo( bar )"))
    self.assertRaises(Exception, iv.ensure_method("foo(bar,baz)"))
    self.assertRaises(Exception, iv.ensure_method("foo(bar, baz)"))

    iv.ensure_method("foo()") # should not raise exception
    iv.ensure_method("foo (bar)") # should not raise exception

class InterfaceValidatorArgumentTest(unittest.TestCase):
  def setUp(self):
    self.iv = InterfaceValidator( Example1(1,2), defer_validation=False )
  def tearDown(self):
    pass

  def test_methods_we_have(self):
    self.iv.expect_method("__init__(self, a, b)")
    self.iv.expect_method("m1(self)")
    self.iv.expect_method("m2(self, a)")
    self.iv.expect_method("m3(self, a, b=True)")
    self.iv.expect_method("m4(self, *args)")
    self.iv.expect_method("m5(self, bar, *args, **kwargs)")
    self.iv.expect_method("m6(self, bar, baz=True, *args, **kwargs)")

  def test_missing_methods(self):
    self.assertRaises(ValidationException, lambda: self.iv.expect_method("__len__(self)"))
    self.assertRaises(ValidationException, lambda: self.iv.expect_method("foo()"))

  def test_methods_with_bad_signature(self):
    self.assertRaises(ValidationException, lambda: self.iv.expect_method("__init__(self)"))

    self.assertRaises(ValidationException, lambda: self.iv.expect_method("m3(a, b=True)"))

    self.assertRaises(ValidationException, lambda: self.iv.expect_method("s1()")) # staticmethod
    self.assertRaises(ValidationException, lambda: self.iv.expect_method("s1(a)")) # staticmethod and arg mismatch

  def test_staticmethods_we_have(self):
    self.iv.expect_staticmethod("s1()")

  def test_staticmethods_with_issues(self):
    self.assertRaises(ValidationException, lambda: self.iv.expect_staticmethod("s1(a)"))
    self.assertRaises(ValidationException, lambda: self.iv.expect_staticmethod("get()"))
    self.assertRaises(ValidationException, lambda: self.iv.expect_staticmethod("m3(a, b=True)"))

  def test_properties_we_have(self):
    self.iv.expect_get_property("get")
    self.iv.expect_get_set_property("getset")
    self.iv.expect_get_set_del_property("getsetdel")


  def test_missing_properties(self):
    self.assertRaises(ValidationException, lambda: self.iv.expect_get_property("not_a_property"))

    self.assertRaises(ValidationException, lambda: self.iv.expect_get_set_property("not_a_property"))

    self.assertRaises(ValidationException, lambda: self.iv.expect_get_set_del_property("not_a_property"))

  def test_wrong_properties(self):
    self.assertRaises(ValidationException, lambda: self.iv.expect_get_property("getset"))

    self.assertRaises(ValidationException, lambda: self.iv.expect_get_property("getsetdel"))

    self.assertRaises(ValidationException, lambda: self.iv.expect_get_set_property("get"))

    self.assertRaises(ValidationException, lambda: self.iv.expect_get_set_property("getsetdel"))


    self.assertRaises(ValidationException, lambda: self.iv.expect_get_set_del_property("get"))

    self.assertRaises(ValidationException, lambda: self.iv.expect_get_set_del_property("getset"))

