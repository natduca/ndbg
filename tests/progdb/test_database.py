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
import time
import unittest

import progdb
from util import *
import os

class TestDatabase(unittest.TestCase):
  def test_basic(self):
    db = progdb.Database()
    db.add_search_path("./tests")

    sleep_start = time.time()
    MessageLoop.run_while(lambda: time.time() < sleep_start + 1.0) # sleep for a bit so the db can find things

    self.assertTrue(db.get_num_files() != 0)

    goal = os.path.abspath("./tests/apps/test1.c")
    log1("Searching...")
    matching = db.find_files_matching("test1.c")
    self.assertTrue(goal in matching)

    db.shutdown()

  def test_ignores(self):
    db = progdb.Database()
    db.add_ignore("Makefile")
    db.add_search_path("./tests")

    sleep_start = time.time()
    MessageLoop.run_while(lambda: time.time() < sleep_start + 1.0) # sleep for a bit so the db can find things

    self.assertTrue(db.get_num_files() != 0)

    log1("Searching...")
    matching = db.find_files_matching("Makefile")
    self.assertEqual(len(matching), 0)

    goal = os.path.abspath("./tests/apps/test1.c")
    matching = db.find_files_matching("test1.c")
    self.assertTrue(goal in matching)

    db.shutdown()

  def test_remoted_basic(self):
    db = RemoteClass(progdb.Database)
    db.call_async.add_search_path("./tests")

    sleep_start = time.time()
    MessageLoop.run_while(lambda: time.time() < sleep_start + 1.0) # sleep for a bit so the db can find things


    self.assertTrue(db.call.get_num_files() != 0)

    goal = os.path.abspath("./tests/apps/test1.c")
    log1("Searching...")
    matching = db.call.find_files_matching("test1.c")
    self.assertTrue(goal in matching)

    db.shutdown()
