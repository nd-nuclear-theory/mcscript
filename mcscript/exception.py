""" exception.py -- define scripting exceptions

  Language: Python 3

  M. A. Caprio
  Department of Physics, University of Notre Dame

  - 3/18/17 (mac): Move in ScriptError from control.
  - 06/02/20 (pjf): Add InsufficientTime exception.

"""

# exception class for errors in script execution
class ScriptError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

# exception class for signaling insufficient time remaining
class InsufficientTime(Exception):
    def __init__(self, required_time):
        self.required_time = required_time
    def __str__(self):
        return "required time: {:g}".format(self.required_time)
