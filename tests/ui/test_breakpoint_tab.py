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
from debugger import *
from ui.breakpoint_tab import *
class TestBreakpointTabUsingTest1(UITestCaseSingle):
  def setUp(self):
    UITestCaseSingle.setUp(self, "tests/apps/test1")

  def test_breakpoint_new_and_delete(self):
    btab = self.run_on_ui(lambda mc: mc.find_tab(BreakpointTab))

    def make_bkpt(mc): # TODO directly call the new_breakpoint method on the breakpoint_tab...
      return btab.new_breakpoint("test1.c:13")
    bp = self.run_on_ui(make_bkpt)

    # make sure the bp made it into the tab liststore
    self.assertEqual( self.run_on_ui(lambda mc: len(btab._ls)), 1)

    # remove it
    self.run_on_ui(lambda mc: mc.debugger.breakpoints.remove(bp))

    # make sure the bp left the tab liststore
    self.assertEqual( self.run_on_ui(lambda mc: len(btab._ls)), 0)
