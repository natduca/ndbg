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
from tests import *
import unittest
from debugger.gdb_parsers import *

class ParseTest(unittest.TestCase):
  def test_parse_response(self):
    t = []
    t.append('thread-id="1"')
    t.append('')
    t.append('a={}')
    t.append('a=[]')
    t.append('a={x="1"}')
    t.append("x=\"hello \\\"world\\\"\"")
    t.append('a=[x="1"]')
    t.append('a={x="1",y="2"}')
    t.append('a=[x="1",x="2"]')
    t.append('a={x="1",x={z="2"}}')
    t.append('a="1",b="2",c=[x="1",x="2"]')
    t.append('id="/lib64/ld-linux-x86-64.so.2",target-name="/lib64/ld-linux-x86-64.so.2",host-name="/lib64/ld-linux-x86-64.so.2",symbols-loaded="0"')
    t.append('reason="breakpoint-hit",disp="keep",bkptno="1",frame={addr="0x08048434",func="main",args=[{name="argc",value="2"},{name="argvf",value="0xbffff454"}],file="test1.c",fullname="/home/nduca/Local/experiments/ndbg/test/test1.c",line="9"},thread-id="1",stopped-threads="all",core="0"')
    t.append('reason="breakpoint-hit",disp="keep",bkptno="1",frame={addr="0x000000000040056f",func="doSleep",args=[{name="c",value="1"}],file="test1.c",fullname="/usr/local/google/nduca/experiments/ndbg/test/test1.c",line="4"},thread-id="1",stopped-threads="all",core="13"')
    t.append('stack=[frame={level="0",addr="0x000000000040056f",func="doSleep",file="test1.c",fullname="/usr/local/google/nduca/experiments/ndbg/test/test1.c",line="4"},frame={level="1",addr="0x00000000004005d4",func="main",file="test1.c",fullname="/usr/local/google/nduca/experiments/ndbg/test/test1.c",line="13"}]')
    t.append('hdr=[z={x="1"},z={x="2"}]')
    t.append('hdr=[{x="1"},{x="2"}]')
    for c in t:
      r = GdbMiResponse('done',c)
#      print "In:\n%s\nOut:\n%s\n\n" % (c,r)

  def test_breakpoint_parser(self):
    hresp = GdbMiResponse("done", 'BreakpointTable={nr_rows="1",nr_cols="6",hdr=[{width="7",alignment="-1",col_name="number",colhdr="Num"},{width="14",alignment="-1",col_name="type",colhdr="Type"},{width="4",alignment="-1",col_name="disp",colhdr="Disp"},{width="3",alignment="-1",col_name="enabled",colhdr="Enb"},{width="18",alignment="-1",col_name="addr",colhdr="Address"},{width="40",alignment="2",col_name="what",colhdr="What"}],body=[bkpt={number="2",type="breakpoint",disp="keep",enabled="y",addr="<MULTIPLE>",times="0",original-location="WebKit::WebViewImpl::composite"}]}')
#                     1         2         3         4         5
#           0123456789|123456789|123456789|123456789|123456789|123456789|123456789|123456789
    lines = ["Num     Type           Disp Enb Address            What\n",
             "2       breakpoint     keep y   <MULTIPLE>         \n",
             "2.1                         y     0x00007ffff26fe37d in WebKit::WebViewImpl::composite(bool) at third_party/WebKit/WebKit/chromium/src/WebViewImpl.cpp:1033\n",
             "2.2                         y     0x00007fffef3adfbd in WebKit::WebViewImpl::composite(bool) at third_party/WebKit/WebKit/chromium/src/WebViewImpl.cpp:1033\n"]
    bs = parse_multiple_breakpoint_info(hresp,lines)
    l1 = parse_console_style_location(bs[1].addr)
    l2 = parse_console_style_location(bs[2].addr)


class GdbMatcherTest(unittest.TestCase):
  def test_word_matcher(self):
    m = GdbWordMatcher()
    m.add("run",1)
    m.add("return",2)
    self.assertEqual(m.fuzzy_get(""), None)
    self.assertEqual(m.fuzzy_get("r"), None) # ambiguous
    self.assertEqual(m.fuzzy_get("ru"), 1)
    self.assertEqual(m.fuzzy_get("run"), 1)
    self.assertEqual(m.fuzzy_get("runx"), None)
    m.add("r",3)
    self.assertEqual(m.fuzzy_get("r"), 3) # precise hit
    self.assertEqual(m.fuzzy_get("re"), 2)
  def test_phrase_matcher(self):
    m = GdbPhraseMatcher()
    m.add("run", 1)
    m.add("return", 2)
    m.add("r", 3)
    m.add("info threads", 4)
    m.add("info breakpoints", 5)
    m.add("thread", 6)

    self.assertEqual(m.fuzzy_get("x"), [None])
    self.assertEqual(m.fuzzy_get("x"), [None])
    self.assertEqual(m.fuzzy_get("run"), [1])
    self.assertEqual(m.fuzzy_get("run 3"),[1, "3"])
    self.assertEqual(m.fuzzy_get("r 3"),[3, "3"])
    self.assertEqual(m.fuzzy_get("i th 3"),[4, "3"])
    self.assertEqual(m.fuzzy_get("i thx 3"),[None])
    self.assertEqual(m.fuzzy_get("i th"),[4])
    self.assertEqual(m.fuzzy_get("i b"),[5])
    self.assertEqual(m.fuzzy_get("info"),[None])
