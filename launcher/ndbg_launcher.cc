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
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int __is_ndbg_launcher_waiting = 1;

void wait_for_debugger() {
  fprintf(stderr, "ndbg_launcher: pid %i is waiting for ndbg's arrival\n", getpid());

  while(__is_ndbg_launcher_waiting) {
    usleep(1000*30);
  }
}

int main(int argc, char** argv) {
  if(argc < 2) {
    fprintf(stderr, "ndbg_launcher requires at least one argument.");
    return EXIT_FAILURE;
  }

   // wait for ndbg to attach
  wait_for_debugger();

  // build execv argument
  fprintf(stderr, "ndbg_launcher args: \n");
  char** new_argv = new char*[argc];
  for(int i = 1; i < argc; ++i) {
    fprintf(stderr, "  arg%2i: %s\n", i, argv[i]);
    new_argv[i-1] = argv[i];
  }
  new_argv[argc-1] = NULL;

  // do execv
  fprintf(stderr, "ndbg_launcher: execvp(%s)\n", argv[1]);
  int ret = execvp(argv[1], new_argv);
  delete [] new_argv;
  if(ret == -1)
    return EXIT_FAILURE;
  return EXIT_SUCCESS;
}
