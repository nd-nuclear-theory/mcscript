#!/usr/bin/python3

""" runex02.py

  Example hybrid parallel hello world run.

  Language: Python 3

  M. A. Caprio
  University of Notre Dame

  11/22/16 (mac): Created.

"""

import os

import mcscript

mcscript.init()

##################################################################
# main body
##################################################################


# example of running an executable
#
#   Note that mcscript.utils.subprocess is a wrapper to the subprocess
#   package, but does a lot more...  It generates logging output, it
#   checks the return code and generates an exception on failure
#   (i.e., a nonzero return), it can provide input lines to the code
#   via standard input (optional parameter input_lines), and various
#   other possibilities depending on the optional parameters.
#
#   See the docstring for mcscript.utils.call for further information.

filename = os.path.join(os.environ["MCSCRIPT_DIR"],"example","hello_hybrid")
mcscript.call([filename],mode="parallel")

################################################################
# termination
################################################################

mcscript.termination()
