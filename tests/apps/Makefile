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
CFLAGS += -g -O0
CXXFLAGS += -g -O0
LDFLAGS += -lpthread

APPS = \
	test1 test2 \
	test_threads \
	test_multiproc \
	libtest_shared.so test_shared \
	test_exit \
	test_template \
	test_fw

all: $(APPS)

test_shared: test_shared.o
	g++ -o $@ $^ -ltest_shared -L.

libtest_shared.o: CXXFLAGS+=-fPIC
libtest_shared.so: libtest_shared.o
	g++ -shared -o $@ $^

clean:
	rm -f *.o
	rm -f *.so
	rm -f $(APPS)
