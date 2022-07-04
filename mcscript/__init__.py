""" mcscript package -- scripting setup, utilities, and task control for cluster runs

  Language: Python 3

  M. A. Caprio
  Department of Physics, University of Notre Dame

  + 06/05/13 (mac): Derived from earlier job.py, script.py, task.py complex (2/13).
  + 01/22/14 (mac): Python 3 update.
  + 05/13/15 (mac): Insert "future" statements for attempted Python 2 legacy support.
  + 06/13/16 (mac): Restructure submodules and generate __init__.py loader file.
  + 11/22/16 (mac): Continue restructuring submodules.

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

# load local hooks
from . import config

# load parameters
from . import parameters

# load control functions
#   imported into global namespace
from . import control
from .control import *

# load utilities submodule
from . import utils
## from mcscript.utils import *

# load task machinery submodule
from . import task
