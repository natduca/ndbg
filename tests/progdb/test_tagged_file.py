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
import os.path
from progdb.tagged_file import *
from progdb.ctags_parser import *

class TestTaggedFile(unittest.TestCase):
  def test_tagged_file(self):
    tf = TaggedFile(os.path.abspath("tests/resources/ctags_test1.cpp"))
    self.assertTrue(tf.get_tags() == None)
    tf.update()
    self.assertTrue(tf.get_tags() != None)

    tf_tags = tf.get_tags()
    op = find(tf_tags, lambda t: t[1] == "globalVariable")
    self.assertTrue(op != None)
    tag = tf.get_tag(op[0])
    self.assertEqual(tag.type, CTAG_TYPE_VARIABLE)
    tag.determine_line_number(tf.filename)
    self.assertEqual(tag.line_number, 3)
