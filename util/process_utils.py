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
import os
import subprocess
import StringIO
import cStringIO as StringIO
import re
from util.base import *

class ProcessUtils(object):
  @staticmethod
  def is_proc_alive(pid):
    """Returns whether process pid is alive."""
    return os.path.isdir("/proc/%i" % pid)

  @staticmethod
  def kill_proc(pid):
    os.system("kill %s" % pid)

  @staticmethod
  def shlex_join(argv):
    """Joins an argv list into a single string, quoting args that need quoting."""
    def quote(arg):
      if arg.find(" ") >= 0:
        return '"%s"' % arg
      else:
        return arg
    return " ".join([quote(arg) for arg in argv])

  @staticmethod
  def get_pid_full_cmdline_as_array(pid):
    """Full cmdline is program AND command line arguments"""
    try:
      f = open("/proc/%i/cmdline" % pid,'r')
    except IOError:
      raise Exception("Could not open /proc/%i/cmdline, does not exist" % pid);
    try:
      tmp = f.read()
      f.close()
    except IOError, ex:
      print ex
      raise Exception("Could not read from process cmdline");
    assert tmp[-1] == '\x00'
    return tmp[:-1].split("\x00")

  @staticmethod
  def get_pid_full_cmdline(pid):
    return " ".join(ProcessUtils.get_pid_full_cmdline_as_array(pid))

  @staticmethod
  def get_pid_name(pid):
    return ProcessUtils.get_pid_full_cmdline_as_array(pid)[0]

  @staticmethod
  def get_process_list(all_users = False):
    args = ["/bin/ps","--no-headers"]
    if all_users:
      args += ["-A"]
    else:
      import getpass
      args += ["-u", getpass.getuser()]
    args += ["-o", "pid,user,args"]

    ps_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    resp = StringIO.StringIO(ps_proc.communicate()[0])
    procs = []
    for line in resp:
      line = line.strip()
      recs = re.split("\s+", line)
      assert(len(recs) >= 3)
      proc = DynObject()
      proc.pid = int(recs[0])
      proc.username = recs[1]
      proc.args = " ".join(recs[2:])
      procs.append(proc)
    return procs

