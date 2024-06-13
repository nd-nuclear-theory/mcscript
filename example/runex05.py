""" runex05.py

  Simple example of providing stdin input to an executable.

  Language: Python 3

  M. A. Caprio
  Department of Physics
  University of Notre Dame

  6/28/17 (mac): Created.

"""

import mcscript
import mcscript.control
import mcscript.parameters

mcscript.control.init()

##################################################################
# main body
##################################################################

mcscript.control.call(
    ["cat"],
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


################################################################
# termination
################################################################

mcscript.control.termination()
