""" exception.py -- define scripting exceptions

  Language: Python 3

  M. A. Caprio
  Department of Physics, University of Notre Dame

  3/18/17 (mac): Move in ScriptError from control.

"""

# exception class for errors in script execution
class ScriptError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
