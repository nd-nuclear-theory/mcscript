""" runex01.py

  Language: Python 3

  M. A. Caprio
  Department of Physics
  University of Notre Dame

  6/13/16 (mac): Created (runex00.py).
  11/22/16 (mac): Update after restructuring mcscript.
  1/8/17 (mac): Rename to runex01.py.
  5/26/17 (mac): Update mcscript syntax.

"""

import mcscript
import mcscript.control
import mcscript.parameters
import mcscript.utils

mcscript.control.init()

##################################################################
# main body
##################################################################

# test utils submodule
print("Time stamp:",mcscript.utils.time_stamp())

# example of output from the script to stdout
print()
print("We have finished loading mcscript now and are")
print("in the body of the script...")
print()

# example of generating a text file
#
#   Typically this would be an "input" file for some code...
#
#   Note that mcscript.utils.write_input also generates logging output (to
#   standard output).
#
#   See the docstring for mcscript.utils.write_input for further information.

mcscript.utils.write_input(
    "hello.txt",
    input_lines=[
        "",
        "Dear World,",
        "",
        "   Hello!",
        "",
        "Your faithful script,",
        # note use of run parameters from mcscript.parameters.run
        mcscript.parameters.run.name
        ]
    )

# example of running an executable
#
#   Note that mcscript.control.call is a wrapper to the subprocess
#   package, but does a lot more...  It generates logging output, it
#   checks the return code and generates an exception on failure
#   (i.e., a nonzero return), it can provide input lines to the code
#   via standard input (optional parameter input_lines), and various
#   other possibilities depending on the optional parameters.
#
#   See the docstring for mcscript.utils.call for further information.

mcscript.control.call(["/bin/cat","hello.txt"])

################################################################
# termination
################################################################

mcscript.control.termination()
