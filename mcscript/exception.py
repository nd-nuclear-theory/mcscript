""" exception.py -- define scripting exceptions

  Language: Python 3

  M. A. Caprio
  Department of Physics, University of Notre Dame

  - 3/18/17 (mac): Move in ScriptError from control.
  - 06/02/20 (pjf): Add InsufficientTime exception.
  - 08/11/20 (pjf): Add LockContention exception.

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

# exception class for signaling lock conflict
class LockContention(Exception):
    def __init__(self, index, phase):
        self.index = index
        self.phase = phase
    def __str__(self):
        return "lock contention on task {} phase {}".format(self.index, self.phase)
