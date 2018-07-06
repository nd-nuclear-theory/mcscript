"""runex03.py

  Example hybrid parallel hello world run.

  First compile hello-hybrid.cpp:

    mpicxx -fopenmp hello-hybrid.cpp -o hello-hybrid

  Here are some parallelization possibilities (depending on your
  mcscript local configuration, you might need to specify --nodes or
  --nodesize options, too):

  Pure OpenMP...

  % qsubm ex03 --threads=4

  Pure MPI...

  % qsubm ex03 --ranks=4

  Hybrid MPI/OpenMP (on single node)...

  % qsubm ex03 --ranks=2 --threads=4

  Language: Python 3

  M. A. Caprio
  University of Notre Dame

  11/22/16 (mac): Created (runex02.py).
  01/08/17 (mac): Rename to runex03.py.
  04/22/17 (mac): Update to use our test code hello-hybrid.cpp.
  07/06/18 (pjf): Dump CPU information using `lscpu`.

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
#   See the docstring for mcscript.call for further information.

# running an executable "unwrapped" -- no OpenMP/MPI setup
mcscript.call(["lscpu"])

# running a "hybrid" exectuable -- use both OpenMP and MPI
executable_filename = os.path.join(os.environ["MCSCRIPT_DIR"],"example","hello-hybrid")
mcscript.call([executable_filename],mode=mcscript.CallMode.kHybrid)

################################################################
# termination
################################################################

mcscript.termination()
