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
#define MY_DEFINE x

int globalVariable; // dont move this, tests want this to be on line 3

void someFunction(int x) {
}

extern void externFunction(int y);

typedef unsigned int UIntType;


class Bar {
 public:
  int field;
  void MemberFunction();
  ~Bar();
};

template <class T>
class TplClass {
  T templateField;
  void TemplateFunction(const T& cons);
};

namespace {
  int anon_namespaced_variable;
}


namespace X {
  int regular_namespaced_variable;
}
