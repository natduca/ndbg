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
from util.base import *
from util.logging import *
import util.pson as pson
from util.message_loop import *
import os

class SettingExistsException(Exception):
  def __init__(self,k):
    Exception.__init__(self,k)

class SettingDoesntExistException(Exception):
  def __init__(self,k):
    Exception.__init__(self,k)

def new_settings(): # TODO(nduca) remove me once we've renamed _Settings->Settings
  settings_file = os.path.expanduser("~/.ndbg")
  return _Settings(settings_file)

class _Settings(object):
  def __init__(self,settings_file):
    self._types = {}
    self._values = {}
    self._temp_values = {}
    self._used_default = set()
    self._unresolved_values = None
    self._settings_file = settings_file
    self._load(settings_file)
    self._delayed_save = False
    self._enqueued_save_abort_flag = None # is none if no save enqueued, BoxedObject(bool) if enqueued, see _save for details

    self._initialized = True # call this last, it prevents further attribute additions

  def set_delayed_save(self,v):
    assert type(v) == bool
    self._delayed_save = v

  def _load(self,settings_file=None):
    self._unresolved_values = {}
    if not os.path.exists(settings_file):
      log1("Note: Settings file does not exist")
      return

    # load settings...
    contents = open(settings_file, "r").read()
    if len(contents):
      try:
        something = pson.loads(contents)
      except Exception:
        log0("Note: Settings file (%s) is corrupt due to eval. Ignoring it.", settings_file)
        return
    else:
      log2("Settings file %s was empty", settings_file)
      return
    if type(something) != dict:
      log0("Note: Settings file (%s) is corrupt. Ignoring it.", settings_file)
      return
    self._unresolved_values = something
    log2("Loaded settings file %s with %i values", settings_file, len(self._unresolved_values))

  def _set_dirty(self):
    log2("Settings: changed.")
    if get_loglevel() >= 2:
# uncomment these to figure out who is changing settings
#      import traceback
#      fmt = traceback.format_stack()
#      log2("Stack: %s", "".join(fmt))
      pass

    if self._delayed_save:
      if self._enqueued_save_abort_flag:
        self._enqueued_save_abort_flag.set(True)
#        log2("Aborting previously enqueued save")
      def do_delayed_save(abort_flag):
        if abort_flag.get():
#          log3("do_delayed_save cb ran but abort flag was set.")
          return
        assert abort_flag == self._enqueued_save_abort_flag # asserting that the boxed object is the same, not the value
        self._enqueued_save_abort_flag = None
        self._do_save()

      flag = BoxedObject(False)
      self._enqueued_save_abort_flag = flag
      MessageLoop.add_delayed_message(do_delayed_save, 1000, flag)
    else:
      self._do_save()

  def _do_save(self):
    log2("Settings: saving to %s", self._settings_file)
    f = file(self._settings_file,"w")
    # only dump the ones that arent in used_default
    vals = {}
    for k in self._values.keys():
      if k not in self._used_default:
        vals[k] = self._values[k]
    s = pson.dumps(vals,pretty=True)
    f.write(s)
    f.close()

  def has_setting(self, k):
    return self._types.has_key(k)

  def register(self,k,type,default):
    if self._types.has_key(k):
      if self._types[k] != type:
        raise Exception("Setting %s is already registered as type %s" % (k, type))
      return
    self._types[k] = type
    assert(not self._values.has_key(k))
    if self._unresolved_values.has_key(k):
      v = self._unresolved_values[k]
      if isinstance(v,self._types[k]) == False:
        if MessageLoop.get_in_test_mode() == False:
          log0("Type mismatch on %s setting. Registered as %s but setting file contains %s", k, self._types[k], type(v))
        self._values[k] = default
        self._used_default.add(k)
      else:
        self._values[k] = v
      del self._unresolved_values[k]
    else:
      self._values[k] = default
      self._used_default.add(k)

  def is_manually_set(self, k):
    if self._temp_values.has_key(k):
      return True
    else:
      return (k in self._used_default) == False

  def has_unresolved_settings(self):
    return len(self._unresolved_values) != 0

  def __getattr__(self,k):
    if self.__dict__.has_key(k):
      return self.__dict__[k]
    elif self._temp_values.has_key(k):
      return self._temp_values[k]
    elif self._values.has_key(k):
      return self._values[k]
    raise SettingDoesntExistException(k)

  def __setattr__(self, k, v):
    if self.__dict__.has_key("_initialized") == False:
      return object.__setattr__(self,k,v)
    elif self.__dict__.has_key(k):
      return object.__setattr__(self,k,v)
    else:
      if self._types.has_key(k) == False:
        raise SettingDoesntExistException(k)
      if type(v) != self._types[k]:
        raise TypeError()
      self._values[k] = v
      if k in self._used_default:
        self._used_default.remove(k)
      self._set_dirty()

  def __getitem__(self,k):
    return self.__getattr__(k)

  def __setitem__(self,k,v):
    return self.__setitem__(k,v)

  def set(self,k,v):
    self.__setattr__(k,v)


  def set_temporarily(self,k,v):
    if self._types.has_key(k) == False:
      raise SettingDoesntExistException(k)
    if type(v) != self._types[k]:
      raise TypeError()
    self._temp_values[k] = v

  def unset_temporarily(self,k,v):
    if self._temp_values.has_key(k) == False:
      raise SettingDoesntExistException("%s is not temporarily set." % k)
    del self._temp_values[k]
