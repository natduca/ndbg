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
import math

class vec2(object):
  def __init__(self, opt_a=None,opt_b=None):
    if opt_a != None and opt_b != None:
      self.x = float(opt_a)
      self.y = float(opt_b)
    elif opt_a != None:
      self.x = float(opt_a.x)
      self.y = float(opt_a.y)
    else:
      self.x = 0
      self.y = 0
  def set(self,a,opt_b=None):
    if opt_b != None:
      self.x = float(a)
      self.y = float(opt_b)
    else:
      self.x = float(a.x)
      self.y = float(a.y)

  def __str__(self):
    return "(%f,%f)" % (self.x,self.y)

def vec2_add(a,b):
  dst = vec2()
  dst.x = a.x + b.x
  dst.y = a.y + b.y
  return dst


def vec2_accum(a,b):
    a.x += b.x
    a.y += b.y
    return a

def vec2_sub(a,b):
    dst = vec2()
    dst.x = a.x - b.x
    dst.y = a.y - b.y
    return dst


def vec2_neg_accum(a,b):
    a.x -= b.x
    a.y -= b.y
    return a


def vec2_scale(a,scale):
    dst = vec2()
    dst.x = a.x * scale
    dst.y = a.y * scale
    return dst


def vec2_scale_inplace(a,scale):
    a.x *= scale
    a.y *= scale
    return a


def vec2_piecewise_mul(a,b):
    dst = vec2()
    dst.x = a.x * b.x
    dst.y = a.y * b.y
    return dst

def vec2_piecewise_div(a,b):
    dst = vec2()
    dst.x = a.x / b.x
    dst.y = a.y / b.y
    return dst

def vec2_dot(a,b):
    return a.x * b.x + a.y * b.y


def vec2_length(a):
    return math.sqrt(vec2_dot(a,a))


def vec2_length_sqared(a):
    return vec2_dot(a,a)


def vec2_normalize(a):
    s = 1/vec2_length(a)
    return vec2_scale(a,s)


def vec2_normalize_inplace(dst):
    s = 1/vec2_length(dst)
    dst.x *= s
    dst.y *= s
    return dst


def vec2_interp(a,b,factor):
    delta = vec2_sub(b,a)
    vec2_scale_inplace(delta,factor)
    vec2_accum(delta,a)
    return delta


def vec2_distance(a,b):
    return vec2_length(vec2_sub(b,a))


class rect(object):
  def __init__(self,opt_a=None,opt_b=None,centered=False):
    if opt_a and opt_b:
      self.pos = vec2(opt_a)
      self.size = vec2(opt_b)
    elif opt_a == None and opt_b == None:
      self.pos = vec2(0,0)
      self.size = vec2(0,0)
    else:
      raise Exception("Need two args or none")
    if centered:
      hsize = vec2_scale(self.size,0.5)
      self.pos = vec2_sub(self.pos,hsize)

  def contains(self,v):
     return v.x >= self.pos.x and v.x < self.pos.x + self.size.x and v.y >= self.pos.y and v.y < self.pos.y + self.size.y


###########################################################################

class ivec2(object):
  def __init__(self, opt_a=None,opt_b=None):
    if opt_a != None and opt_b != None:
      self.x = int(opt_a)
      self.y = int(opt_b)
    elif opt_a != None:
      self.x = int(opt_a.x)
      self.y = int(opt_a.y)
    else:
      self.x = 0
      self.y = 0
  def set(self,a,opt_b=None):
    if opt_b != None:
      self.x = int(a)
      self.y = int(opt_b)
    else:
      self.x = int(a.x)
      self.y = int(a.y)

  def __str__(self):
    return "(%i,%i)" % (self.x,self.y)
  
