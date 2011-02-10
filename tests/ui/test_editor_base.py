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
from tests.ui import *
import unittest

# Note that this module overrides test loading behavior:
# GenericEditorTests code is not run directly. Rather,
# in another file, subclass this test 

# Tests in here will be applied to all editor configurations
############################################################################
class EditorBaseTestCase(UITestCaseSingle):
  def setUp(self,options):
    UITestCaseSingle.setUp(self, "tests/apps/test2", options)

  def test_alive_safely(self):
    self.assertNoUnhandledExceptions()

#  def test_missing_file(self):
#    def step1(mc):
#      editor = mc.editor
#      editor.open_requested_filename("this_file_cannot_possibly_exist")
#    self.run_on_ui(step1)

#  def test_valid_file(self):
#    def step1(mc):
#      editor = mc.editor
#      tab = editor.open_requested_filename("test2.c")
#      tabs = editor.get_tabs()
#      self.assertEqual(tabs, [tab])
#    self.run_on_ui(step1)

# make sure killing an app removes the current marker entirely
# make sure we only have one tab


# Tests specific to the sourceview editor
############################################################################
#class SourceViewEditorTests(EditorBaseTestCase):
#  def setUp(self):
#    options = DynObject()
#    options.sourceview = True
#    EditorBaseTestCase.setUp(self, options)

def load_tests():
  return unittest.TestSuite() # omit all classes in this file from testing
