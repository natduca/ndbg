import unittest
import os

class TestImportable(unittest.TestCase):
  def _get_module_names_in_package(self, modbase):
    dir = modbase.replace(".", "/")
    dirname = os.path.join(".", dir)
    files = os.listdir(dirname)
    pyfiles = [d for d in files if os.path.splitext(d)[1] == ".py"]
    if "__init__.py" in pyfiles:
      pyfiles.remove("__init__.py")
    res = []
    for pyfile in pyfiles:
      if pyfile.startswith("."):
        continue # dotfiles
      modname = os.path.splitext(pyfile)[0]
      pymodule = "%s.%s" % (modbase, modname)
      res.append(pymodule)
    return res

  def _test_module_importable(self,modname):
    dir = modname.replace(".", "/")
    dirname = os.path.join(".", dir)
    if os.path.isdir(dirname):
      __import__(modname) # base
      for submodname in self._get_module_names_in_package(modname):
        self._test_module_importable(submodname)
    else:
      module = __import__(modname,fromlist=[True])

  def test_importable(self):
    self._test_module_importable("util")
    self._test_module_importable("debugger")
    self._test_module_importable("ui")
