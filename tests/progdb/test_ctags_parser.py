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
from progdb.ctags_parser import *
class TestCTagsParser(unittest.TestCase):
  def test_parse_from_lines(self):
    def doFile(filename):
      f = open(filename,"r")
      tags  = parse_ctags_from_ctags_output(f.readlines())
      for t in tags:
        if t.needs_determining:
          t.determine_line_number(filename)

    doFile("tests/resources/ctags_output_1")
    doFile("tests/resources/ctags_output_2")
    doFile("tests/resources/ctags_output_3")


  def test_parse_from_source(self):
    tags = parse_ctags_from_source("tests/resources/ctags_test1.cpp")
