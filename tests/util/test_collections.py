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
from __future__ import absolute_import
from util import *
import unittest

class TestItem:
  def __init__(self, id, val):
    self.id = id
    self.val = val

class IdentifiedItemListTest(unittest.TestCase):
  def test_basics(self):
    l = IdentifiedItemList()
    i1 = TestItem("Item1",31415)
    l.add(i1)
    self.assertEqual(l["Item1"].val, 31415)
    self.assertTrue(i1 in l)
    self.assertTrue(l.has_key("Item1"))
    self.assertEqual(len(l), 1)
    self.assertEqual(l.values(), [i1])

    l.remove(i1)
    self.assertEqual(l.values(), [])

  def test_try_get_value(self):
    l = IdentifiedItemList()
    i1 = TestItem("Item1",1)
    i2 = TestItem("Item2",2)
    l.add(i1)
    l.add(i2)
    self.assertEqual(l.try_get_value("Item1"),i1)
    self.assertEqual(l.try_get_value("Item3"),None)

  def test_first(self):
    l = IdentifiedItemList()
    i1 = TestItem("Item1",1)
    i2 = TestItem("Item2",2)
    self.assertRaises(IndexError,lambda: l.first)
    l.add(i1)
    self.assertEqual(l.first, i1)
    l.add(i2)
    self.assertTrue(l.first != None)

  def test_events(self):
    l = IdentifiedItemList()
    i1 = TestItem("i1",1)
    i2 = TestItem("i2",1)
    trace = []
    def item_added(item):
      trace.append( "add(%s)" % item.id )
    def changed():
      trace.append( "changed" )
    def item_deleted(item):
      trace.append( "deleted(%s)" % item.id )
    def curtrace():
      v= " ".join(trace)
      del trace[:]
      return v
    l.item_added.add_listener(item_added)
    l.item_deleted.add_listener(item_deleted)
    l.changed.add_listener(changed)
    self.assertEqual(curtrace(),"")
    l.add(i1)
    self.assertEqual(curtrace(),"add(i1) changed")
    l.add(i2)
    self.assertEqual(curtrace(),"add(i2) changed")
    l.remove(i1)
    self.assertEqual(curtrace(),"deleted(i1) changed")

  def test_closures(self):
    pass
