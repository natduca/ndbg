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
from . import *
from util.exponential_backoff import *
import multiprocessing
import traceback
import weakref

def _RemoteServer(cls, c2s, s2c):
  log2("RemoteServer for %s started", cls)
  inst = cls()
  exp = ExponentialBackoff()
  def remote_server_loop():
    found = False
    while True:
      try:
        cmd,args = c2s.get(block=False)
        found = True
        try:
          if cmd == 'quit':
            log2("RemoteServer for %s exiting", cls)
            MessageLoop.quit()
          elif cmd == 'call_async':
            fn_name = args[0]
            rest = args[1]
            fn = getattr(inst, fn_name)
            fn(*rest)
          elif cmd == 'call_async_waitable':
            resp_id = args[0]
            fn_name = args[1]
            rest = args[2]
            fn = getattr(inst, fn_name)
            try:
              ret = fn(*rest)
            except:
              exc = traceback.format_exc()
              s2c.put(('async_exception', (resp_id, exc)))
              continue
            s2c.put(('async_result', (resp_id, ret)))
          else:
            raise Exception("Unrecognized command: %s" % cmd)
        except:
          print "Exceeption during handling command %s(%s)" % (cmd, args)
          traceback.print_exc()
      except Queue.Empty:
        break
    if found:
#      print "Resetting"
      exp.reset()
    else:
#      print "Sleeping %s" % exp._ctr.val
      exp.sleep()

  MessageLoop.run_no_gtk(remote_server_loop)
  if hasattr(inst,'shutdown'):
    log2("Calling shutdown method on %s", cls)
    inst.shutdown()
  while True:
    try:
      c2s.get(block=False)
    except Queue.Empty:
      break
  log2("RemoteServer for %s exited", cls)
  os._exit(-1)


_active_clients = []

class RemoteClient():
  def __init__(self, cls):
    self._cls = cls
    self._c2s = multiprocessing.Queue()
    self._s2c = multiprocessing.Queue()

    args = (cls, self._c2s, self._s2c)
    self._process = multiprocessing.Process(target=_RemoteServer, args=args)
#    self._process.daemon = True
    self._process.start()
    self._resp_id = 0
    self._pending_waitables = { }

    self._process_server_replies_throttle = ThrottledCallback(self._process_server_replies)

    _active_clients.append(weakref.ref(self)) # add cleanup here because we have a thread

  def _c2s_put(self, cmd,*args): # uses message loop to try to push onto queue
    def try_put():
      try:
        self._c2s.put((cmd,args),timeout=0.05)
        return True
      except Queue.Full:
        return False
    MessageLoop.run_until(try_put)

  def _process_server_replies(self):
    if self._s2c == None:
      self._process_server_replies_throttle.stop()
      return False
    item_processed = False
    while self._s2c != None:
      try:
        cmd,args = self._s2c.get(timeout=0.05)
        item_processed = True
        try:
          if cmd == 'async_result':
            resp_id = args[0]
            ret = args[1]
            w = self._pending_waitables[resp_id]
            del self._pending_waitables[resp_id]
            w.set_done(ret)
          elif cmd == 'async_exception':
            resp_id = args[0]
            exc_fmt = args[1]
            w = self._pending_waitables[resp_id]
            del self._pending_waitables[resp_id]
            print "While processing server replies:"
            print exc_fmt
            w.abort(Exception(exc_fmt))
          else:
            raise Exception("Unrecognized command: %s" % cmd)
        except:
          print "Exceeption during handling command %s" % cmd
          traceback.print_exc()
      except Queue.Empty:
        break
    return item_processed

  def call_async(self, fn_name, *args):
    self._c2s_put('call_async', fn_name, args)

  def call_async_waitable(self, fn_name, *args):
    cur_id = self._resp_id
    self._resp_id += 1
    waitable = CallbackDrivenWaitable()
    self._c2s_put('call_async_waitable', cur_id, fn_name, args)
    self._pending_waitables[cur_id] = waitable
    return waitable

  def shutdown(self):
    log2("Shutting down remote class %s", self._cls)
    if self._c2s:
      try:
        self._c2s.put(('quit',tuple()))
      except Queue.Full:
        log2("c2s queue full. Force killing process")
        self._process.terminate()
        return
      self._c2s = None
      self._s2c = None
    if self._process:
      self._process.join(timeout=0.5)
      if self._process.is_alive():
        self._process.terminate()
      self._process = None
    log2("RemoteClass %s has shut down", self._cls)

  @staticmethod
  def _cleanup():
    global _active_clients
    new_active_clients = []
    for b_wr in _active_clients:
      b = b_wr()
      if b:
        new_active_clients.append(b_wr)
        log1("RemoteClient: Forcing shutdown of %s", b)
        try:
          b.shutdown()
        except:
          traceback.print_exc()
    _active_clients = []

# install the cleanup
MessageLoop.add_cleanup_hook(RemoteClient._cleanup)

class RemoteClassInner(object):
  def __init__(self,parent):
    self._parent = parent

  def __getattr__(self,k):
    return self._parent(k)

  def __setattr__(self,k,v):
    if k == '_parent':
      return object.__setattr__(self,k,v)
    else:
      raise Exception("Cannot proxy properties")


class RemoteClass(object):
  """This class wraps the provided class in a child process with Multiprocessing,
  then expoes its methods in three ways:
  - call : regular, blocking call to the remote method.
  - call_async: async call to the remote method. Ignores return value.
  - call_async_waitable: async call to the remote method. Returns a waitable, which
    will eventually provide the return value.

  For example:
    class A:
      def x(y):
        return 3*y

    # Calls x, waits on return value.
    a = RemoteClass(A)
    a.call.x(2)
    => 6

    # Calls x, but does not return any value. The return value is lost.
    a.call_async.x(2)
    => None

    # Calls x, returns a utils.Waitable. You can then handle that value as you wish.
    w = a.call_async_waitable.x(2)
    => <Waitable>
    w.when_done(lambda res: print("Done: ", res))
    w.wait()
    Done: 6
    => 6

  When exceptions occur on the remote method:
  - call will raise the exception
  - call_async will ignore the exception
  - call_async_waitable will:
     - wait() and get_return_value() will raise an exception [but not of the same Type!]
     - when_done callbcaks will not run

  """
  def __init__(self, cls):
    self._client = RemoteClient(cls)
    def make_call(k):
      def call(*args):
        w = self._client.call_async_waitable(k,*args)
        return w.wait()
      return call
    self.call = RemoteClassInner(lambda k: make_call(k))

    def make_call_async(k):
      def call_async(*args):
        self._client.call_async(k,*args)
      return call_async
    self.call_async = RemoteClassInner(lambda k: make_call_async(k))

    def make_call_async_waitable(k):
      def call_async_waitable(*args):
        return self._client.call_async_waitable(k,*args)
      return call_async_waitable
    self.call_async_waitable = RemoteClassInner(lambda k: make_call_async_waitable(k))

  def shutdown(self):
    self._client.shutdown()

  def __setattr__(self,k,v):
    if k in ('_client', 'call', 'call_async', 'call_async_waitable'):
      return object.__setattr__(self, k,v)
    else:
      raise Exception("Cannot assign to here.")
