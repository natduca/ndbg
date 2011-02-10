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
import dbus
import dbus.service

from message_loop import *
from base import *
class _RegisteredProcessSearch(dbus.service.Object):
  def __init__(self):
    self._busses = []

    log1("DBus search began on %s.", dbus.SessionBus().get_unique_name())
    dbus.service.Object.__init__(self, dbus.SessionBus(), "/Search")
    self.search() # fires a signal that will eventually lead to callbacks

  @dbus.service.signal('ndbg.util._RegisteredProcessSearch')
  def search(self):
    """Signal that gets broadcast to search for RegisteredProcess.
    DBusRegisteredProcess will call ."""
    pass

  @dbus.service.method(dbus_interface="ndbg.util._RegisteredProcessSearch")
  def add_search_result(self, bus_name):
    log2("Got bus at %s", bus_name)
    self._busses.append(bus_name)

  @property
  def busses(self):
    return self._busses

class RegisteredProcess(dbus.service.Object):
  def __init__(self):
    log1("DBus session %s was registered.", dbus.SessionBus().get_unique_name())

    def on_search_signal(sender):
      log2("Got RegisteredProcess.search from %s", sender)
      if sender == dbus.SessionBus().get_unique_name():
        return # dont include us!
      search = dbus.SessionBus().get_object(sender, "/Search")
      try:
        search.add_search_result(dbus.SessionBus().get_unique_name())
      except DBusException, ex:
        log1("Wasn't able to reply to search service: %s", str(ex))
        log1("This is probably because the search decided it was complete before we could reply.")

    dbus.SessionBus().add_signal_receiver(on_search_signal,
                                          dbus_interface="ndbg.util._RegisteredProcessSearch",
                                          signal_name="search",
                                          sender_keyword="sender")
    dbus.service.Object.__init__(self, dbus.SessionBus(), "/RegisteredProcess")

  @staticmethod
  def find_registered_dbus_names():
    result = BoxedObject()
    def begin_search():
      search = _RegisteredProcessSearch()
      def stop_search():
        result.set(search.busses)
        MessageLoop.quit()
      MessageLoop.add_delayed_message(stop_search,100) # 100ms
    MessageLoop.add_message(begin_search)
    MessageLoop.run()
    return result.get()
