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
def argn(*args):
  """Returs the last argument. Helpful in making lambdas do more than one thing."""
  return args[-1]

def arg1(*args):
  """Returs args[0]. Helpful in making lambdas do more than one thing."""
  return args[0]

def argif(cond,if_true_value,else_value):
  """
  If cond is true, returns the if_true_value, otherwise else_value.
  Roughly equilvanet to a lisp (if cond true false)
  """
  if(cond):
    return if_true_value
  else:
    return else_value

def argsel(key, default, **kwargs):
  """
  Looks in kwargs for provided key. If found, returns the value provided.
  Else, returns the default argument
  """
  if kwargs.has_key(key):
    return kwargs[key]
  return default
