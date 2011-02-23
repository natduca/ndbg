import unittest
from util import *
import time

class TestWellBehavedThread(unittest.TestCase):
  def test_startstop(self):
    def thr_idle():
      return False
    thr = WellBehavedThread("test", thr_idle)
    thr.start()
    time.sleep(0.1)
    thr.stop()

  def test_leave_running(self):
    def thr_idle():
      time.sleep(0.1)
    thr = WellBehavedThread("test", thr_idle)
    thr.start()
