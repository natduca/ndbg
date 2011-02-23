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
import exceptions
import os
import re
import traceback
import unittest

from util import *

_debug_mode = False

class DebuggerTestCase(unittest.TestCase):
  def __init__(self,progname):
    self._progname = progname

  def setUp(self):
    self._debugger = Debugger()
    self._proc = self._debugger.launch_suspended(self._progname)

  @property
  def debugger(self):
    return self._debugger

  @property
  def process(self):
    return self._progname

def test_is_selected(in_testnames, testname):
#  toks = test_name.split(".")
  for tn in in_testnames:
    if re.search(tn, testname):
      return True
  return False

###########################################################################

class NdbVerboseTestResult(unittest.TestResult):
  def addError(self,test,err):
    traceback.print_tb(err[2])
    unittest.TestResult.addError(self,test,err)
    print err[1]
    if _debug_mode:
      print "*** Halting test due to error. ***"
      os._exit(0) # do this so we truly exit... even if we have a lingering thread [eew]

  def addFailure(self,test,err):
    traceback.print_tb(err[2])
    unittest.TestResult.addFailure(self,test,err)
    print err[1]
    if _debug_mode:
      print "*** Halting test due to error. ***"
      os._exit(0) # do this so we truly exit... even if we have a lingering thread [eew]

def set_debug_mode(halt):
  if not isinstance(halt, bool):
    raise TypeError("Expected bool")
  global _debug_mode
  _debug_mode = halt

###########################################################################

def do_run(testnames = None):
  """
  Run a test given a list of test regexps to run, or all tests.
  """
  immediate = _debug_mode
  MessageLoop.set_in_test_mode(True)
  dirs = ["tests", "tests/util", "tests/debugger", "tests/ui", "tests/progdb"]
  v = 2
  r = unittest.TextTestRunner(verbosity=v)
  l = unittest.TestLoader()
  for dir in dirs:
    dirname = os.path.join(".", dir)
    files = os.listdir(dirname)
    pyfiles = [d for d in files if os.path.splitext(d)[1] == ".py"]
    if "__init__.py" in pyfiles:
      pyfiles.remove("__init__.py")
    suite = unittest.TestSuite()
    for pyfile in pyfiles:
      if pyfile.startswith("."):
        continue # dotfiles
      modbase = dir.replace("/",".")
      modname = os.path.splitext(pyfile)[0]
      pymodule = "%s.%s" % (modbase, modname)
      try:
        module = __import__(pymodule,fromlist=[True])
      except:
        print "While importing [%s]\n" % pymodule
        traceback.print_exc()
        continue
      try:
        if hasattr(module,"load_tests"):
          s = module.load_tests()
        else:
          s = unittest.TestLoader().loadTestsFromModule(module)
      except Exception, ex:
        raise Exception("Error loading test cases from %s: %s"% (pymodule, str(ex)))

      for t in s:
        if isinstance(t, unittest.TestSuite):
          for i in t:
            if testnames != None:
              if test_is_selected(testnames,i.id()):
                suite.addTest(i)
            else:
              suite.addTest(i)
        elif isinstance(t, unittest.TestCase):
          if testnames != None:
            if test_is_selected(testnames,t.id()):
              suite.addTest(t)
          else:
            suite.addTest(t)
        else:
          raise Exception("Wtf, expected TestSuite or TestCase, got %s" % t)

    if suite.countTestCases():
      if immediate == False:
        log0_raw("Test for %s", dir)
        log0_raw("----------------------------------------------------------------------")
        r.run(suite)
        log0_raw("\n")
        log0_raw("\n")
      else:
        for case in suite:
          tr = NdbVerboseTestResult()
          log0_raw("----------------------------------------------------------------------")
          log0_raw("%s", case.id())
          case.run(result=tr)
          if tr.wasSuccessful():
            log0("OK\n")
          elif len(tr.errors):
            log0("Error\n")
          else:
            log0("Fail\n")
    log2("TestSystem: done with module %s", dir)
  log2("TestSystem: done with all ymodules")

def run(testnames = None):
  try:
    do_run(testnames)
  finally:
    MessageLoop.quit(True)
    MessageLoop.set_in_test_mode(False)


# Stray code to load tests from a list of classes:
def _load_tests_from_class(cls):
  in_suite = unittest.TestLoader().loadTestsFromTestCase(case)
  assert(isinstance(suite,unittest.TestSuite))
  for test in in_suite:
    tests.addTest(test)
def _append_suite_to_suite(dst_suite,src_suite):
  for test in src_suite:
    dst_suite.append(test)

