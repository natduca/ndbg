// Copyright 2011 Google Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
#include <stdio.h>
// Hard Dependency: if you change this file update the test
//     test_breakpoint.py puts breakpoint at test_template.cc:19
template <class T>
void increment(T foo) {
  ++foo;
}


int main() {
  int a = 0;
  double b = 0;
  increment(a);
  increment(b);
  printf("a=%i", a);
  printf("b=%f", b);
}
