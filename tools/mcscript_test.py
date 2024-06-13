""" mcscript_test.py -- testbed for loading mcscript

  Language: Python 3

  M. A. Caprio
  Department of Physics, University of Notre Dame

  6/13/16 (mac): Created.

"""

import os
os.environ["MCSCRIPT_RUN"] = "0000"
os.environ["MCSCRIPT_RUN_MODE"] = "local"
os.environ["MCSCRIPT_LAUNCH_DIR"] = ""
os.environ["MCSCRIPT_WORK_DIR"] = os.path.join(os.environ["MCSCRIPT_WORK_HOME"],"run0000")
os.environ["MCSCRIPT_JOB_FILE"] = "none.py"
os.environ["MCSCRIPT_WALL_SEC"] = "-1"
os.environ["MCSCRIPT_WIDTH"] = "-1"
os.environ["MCSCRIPT_DEPTH"] = "-1"
os.environ["MCSCRIPT_PERNODE"] = "-1"
os.environ["MCSCRIPT_NODESIZE"] = "-1"
os.environ["MCSCRIPT_EPAR"] = "-1"

import mcscript
import mcscript.control
import mcscript.utils

mcscript.control.init()


# test utils submodule
print("Time stamp:",mcscript.utils.time_stamp())  # long form
print("Time stamp:",mcscript.control.time_stamp())

