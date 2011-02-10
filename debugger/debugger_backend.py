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
import inspect
from util import InterfaceValidator
class DebuggerBackend(object):
  def __init__(self):
    iv = InterfaceValidator(self);
    iv.expect_staticmethod("supports_multiple_processes()")
    iv.expect_method("shutdown(self, force=False)")
    iv.expect_get_property("debugger_pid") # the pid of the gdb/etc process or none
    iv.expect_get_property("status")
    iv.expect_get_property("status_changed")
    iv.expect_get_property("ptys")
    iv.expect_get_property("processes")
    iv.expect_get_property("threads")
    iv.expect_get_property("main_thread")
    iv.expect_get_property("thread_that_stopped")

    iv.expect_method("begin_launch_suspended(self, cmdline)")
    iv.expect_method("begin_attach_to_pid(self, pid, was_launched_hint)")

    iv.expect_method("kill_process(self, proc)")
    iv.expect_method("detach_process(self, proc)")

    iv.expect_method("begin_resume(self, thr)")
    iv.expect_method("begin_interrupt(self)")
    iv.expect_method("begin_step_over(self, thread)")
    iv.expect_method("begin_step_into(self, thread)")
    iv.expect_method("begin_step_out(self, thread)")

    iv.expect_method("new_breakpoint(self, location, hit_cb)")
    iv.expect_method("enable_breakpoint(self, id)")
    iv.expect_method("disable_breakpoint(self, id)")
    iv.expect_method("delete_breakpoint(self, id)")

    iv.expect_method("get_call_stack(self, thr)")
    iv.expect_method("get_frame(self, thr, frame)")

    iv.expect_method("get_expr_value_async(self, thr, expr, cb)")
