""" mcscript package -- scripting setup, utilities, and task control for cluster runs 

  Language: Python 3

  M. A. Caprio
  Department of Physics, University of Notre Dame

  6/5/13 (mac): Derived from earlier job.py, script.py, task.py complex (2/13).
  1/22/14 (mac): Python 3 update.
  5/13/15 (mac): Insert "future" statements for attempted Python 2 legacy support.
  6/13/16 (mac): Restructure submodules and generate __init__.py loader file.
  11/22/16 (mac): Continue restructuring submodules. 

"""

# To import submodule functions as package.submodule.foo:
#   import package.submodule
#   from . import submodule   # is this actually necessary?  must review...
#
# To import submodule functions package.submodule.foo at top module
# level, as package.foo:
#
#   import package.submodule
#   from package.submodule import *

# load parameters
import mcscript.parameters

# load local hooks
import mcscript.config

# load control functions
#   imported into global namespace
import mcscript.control
from mcscript.control import *

# load utilities submodule
import mcscript.utils
## from mcscript.utils import *

# load task machinery submodule
import mcscript.task
