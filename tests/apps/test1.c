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

void doSleep(int c) {
  c = c & 0x1;
  sleep(c);
}








/* intentional space so we can test scrolling */

















int get_a(int argc) {
  return argc+1;
}

int main(int argc,char** argv) {
  int a = get_a(argc);
  printf("%i\n", a);
  while(1) {
    printf("%i\n", a);
    doSleep(1);
    a+=1;
  }
}
