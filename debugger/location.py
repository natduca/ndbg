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
import re
from util import *

# Locations have various forms. Ranked from most to least precision:
#  has_pc                  prog_ctr
#  has_file_location       filename   line_num
#  has_identifier          identifier
# They may have multiple forms.

class Location:
  def __init__( self,text=None,id=None,filename=None,line_num=None,prog_ctr=None):
    # process text if any
    if text:
      while True: # trick so we can use break to sequence the following test...
        # file:line notation
        m = re.match("^(.+):(\d+)$",text)
        if m:
          filename = m.group(1)
          line_num = int(m.group(2))
          break

        m = re.match("^(0x[0-9a-fA-F]+)$",text)
        if m:
          prog_ctr = text
          break

        # 0xf00bar notation
        m = re.match("^(0x[0-9a-fA-F]+)$",text)
        if m:
          prog_ctr = text
          break

        # ns::class::method notation
        m = re.match("^(\S+)::(\S+)::(\S+)$",text)
        if m:
          id = text
          break

        # class::method notation
        m = re.match("^(\S+)::(\S+)$",text)
        if m:
          id = text
          break

        # assume it is a function, as long as its free of spaces
        m = re.match("^(\S+)$",text)
        if m:
          id = text
          break

        raise Exception("Not a recognized location")

    # sanity check the arguments
#    log3("Location.__init__(prog_ctr=%s, id=%s, filename=%s, line_num=%s)", prog_ctr,id,filename,line_num)
    if prog_ctr == None and id == None and (filename == None or line_num == None):
      raise Exception("Identifiers must have either a prog_ctr, identifier, or filename & line")
    if filename != None or line_num != None:
      if filename == None or line_num == None:
        raise Exception("Must have both filename and line number")
    if line_num != None:
      if type(line_num) != int:
        raise Exception("Line numbers must be an int")
    if prog_ctr != None:
      if type(prog_ctr) != int and type(prog_ctr) != long:
        raise Exception("Program counter must be an int or long")

    self.has_pc = prog_ctr != None
    self.prog_ctr = prog_ctr

    self.has_identifier = id != None
    self.identifier = id

    self.has_file_location = filename != None
    self.filename = filename
    self.line_num = line_num

  def __eq__(self,that):
    if that == None:
      return False
    if not isinstance(that,Location):
      raise Exception("Can only compare locations to locations")

    if self.has_pc == that.has_pc == True:
      return self.prog_ctr == that.prog_ctr

    if self.has_file_location == that.has_file_location == True:
      return self.filename == that.filename and self.line_num == that.line_num

    if self.has_identifier == that.has_identifier == True:
      return self.identifier == that.identifier

    raise "Cannot compare locations, not enough information available"

  def __hash__(self):
    return str(self).__hash__()

  def soft_eq(self,that):
    if that == None:
      return False
    if not isinstance(that,Location):
      raise Exception("Can only compare locations to locations")

    if self.has_file_location == that.has_file_location == True:
      return self.filename == that.filename and self.line_num == that.line_num

    if self.has_pc == that.has_pc == True:
      return self.prog_ctr == that.prog_ctr

    if self.has_identifier == that.has_identifier == True:
      return self.identifier == that.identifier

    raise "Cannot compare locations, not enough information available"


  def __str__(self):
    if self.has_pc:
      if self.has_file_location:
        if self.has_identifier:
          return "(0x%x) %s at %s:%i" % (self.prog_ctr, self.identifier,self.filename,self.line_num)
        else:
          return "(0x%x) at %s:%i" % (self.prog_ctr, self.filename,self.line_num)
      else:
        if self.has_identifier:
          return "(0x%x) %s" % (self.prog_ctr, self.identifier)
        else:
          return "(0x%x)" % (self.prog_ctr)
    else:
      if self.has_file_location:
        if self.has_identifier:
          return "%s at %s:%i" % (self.identifier,self.filename,self.line_num)
        else:
          return "%s:%i" % (self.filename,self.line_num)
      else:
        if self.has_identifier:
          return "%s" % (self.identifier)
        else:
          raise "Malformed location"

  def __repr__(self):
    return "Location(text=\'%s\')" % self.shorthand()

  @property
  def has_repr(self):
    try:
      self.shorthand()
    except:
      return False
    else:
      return True

  def shorthand(self):
    if self.has_identifier:
      return self.identifier
    elif self.has_file_location:
      return "%s:%s" % (self.filename, self.line_num)
    elif self.has_pc:
      return "0x%x" % self.prog_ctr
    else:
      raise Exception("This doesn't have a shorthand.")
