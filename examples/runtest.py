#!/usr/bin/python3

""" runex00.py -- basic hello world example job

   Last modified 12/9/14.

   For simple test run on front end:
   
      qsubm ex00 
"""

# generic packages for use below
#
#   Actually, we do not need these in the present example, but this is
#   where you would load them...

import math
import sys

# import mcscript
#
# This accomplishes various initialization tasks:
# -- parse environment for various script parameters
#    (e.g., are we in batch mode? are we supposed to run certain tasks?)
# -- do basic run setup
#    (e.g., make working directory in scratch space)
# -- make available some functions for use in script
#    (including mcscript utility functions and mcscript.task task
#    management)
#
# See the docstrings in mcscript.py for further information.

import mcscript

##################################################################
# main body
##################################################################

# example of output from the script to stdout
print()
print("We have finished loading mcscript now and are")
print("in the body of the script...")
print()

# example of generating a text file
#
#   Typically this would be an "input" file for some code...
#
#   Note that mcscript.write_input also generates logging output (to
#   standard output).
#
#   See the docstring for mcscript.write_input for further information.

mcscript.write_input(
    "hello.txt",
    input_lines=[
        "",
        "Dear World,",
        "",
        "   Hello!",
        "",
        "Your faithful script,",
        # note use of run parameters from mcscript.run
        mcscript.run.name
        ]
    )

# example of running an executable
#
#   Note that mcscript.subprocess is a wrapper to the subprocess
#   package, but does a lot more...  It generates logging output, it
#   checks the return code and generates an exception on failure
#   (i.e., a nonzero return), it can provide input lines to the code
#   via standard input (optional parameter input_lines), and various
#   other possibilities depending on the optional parameters.
#
#   See the docstring for mcscript.call for further information.

mcscript.call(["/bin/cat","hello.txt"])

################################################################
# termination
################################################################

mcscript.termination()
