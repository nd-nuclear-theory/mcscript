""" runex03.py

  Example hybrid parallel hello world run.

  Retrieve code from:

    http://www.slac.stanford.edu/comp/unix/farm/mpi_and_openmp.html

    mpicc -fopenmp hello_hybrid.c -o hello_hybrid
    setenv OMP_NUM_THREADS 2
    mpirun -n 2 -x OMP_NUM_THREADS ./hello_hybrid

  Language: Python 3

  M. A. Caprio
  University of Notre Dame

  11/22/16 (mac): Created (runex02.py).
  1/8/07 (mac): Rename to runex03.py.

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

filename = os.path.join(os.environ["MCSCRIPT_DIR"],"example","hello_hybrid")
mcscript.call([filename],mode="parallel")

################################################################
# termination
################################################################

mcscript.termination()
