""" mcscript_local_nersc.py -- local definitions for mcscript

    Version for NERSC hopper/edison.

    Language: Python 3
    Mark A. Caprio
    University of Notre Dame
    Written ~7/13 (mac).
    5/13/15 (mac): Insert "future" statements for Python 2 legacy support.
    Last modified 6/13/15 (mac).

"""

from __future__ import print_function, division

import os

# circular import of mcscript
import mcscript

################################################################
# job identification
################################################################

def job_id():
    """ Retrieve job id.

    Returns job id (as string), or "0" if missing.
    """

    return os.environ.get("PBS_JOBID","0")

################################################################
# serial and parallel code launching definitions
################################################################

def serial_prefix(mode):
    """ Generate serial run prefix arguments for given moded.

    mode: run mode

    "local" for invocation in local run (i.e., invocation on front end)
    
    "batch" for invocation in batch run
    
    "epar" for invocation in epar run

    TODO: to add "serial" mode for special run on serial queue
    
    """

    if (mode == "batch"):
        args = ["aprun", "-n1"] # to force run on compute node rather than job script MoM node
    else:
        args = []
        
    return args

def parallel_prefix(run):
    """ Generate parallel run prefix arguments.

    run : RunParameters object with attributes specifying parallel
    execution parameters

    Note: We use argument for run rather than a global reference to
    mcscript.run, since present function is invoked in initializer for
    mcscript.run, before it has entered the namespace.

    """

    # for hopper: https://www.nersc.gov/users/computational-systems/hopper/running-jobs/using-openmp-with-mpi/

    
    args = [
        "aprun",
        "-n%d" % run.parallel_width,
        "-d%d" % run.parallel_depth
    ]
    if (run.parallel_depth != 1):
        args +=[
            "-N%d" % (run.parallel_nodesize // run.parallel_depth),
            "-S%d" % 1,  # ad hoc for hopper
            "-ss"
            ##"--cc numa_node" # for intel compiler
            ]

    return args

################################################################
# embarassingly-parallel job-script relaunching definitions
################################################################

def epar_relaunch_args():
    """ Generate arguments for relaunching script file in epar run.
    """

    # NOTE: hopper-specific environment dependencies:
    #   module load python
    #   module load mpi4py
    #   CRAY_ROOTFS=DSL
    #
    # Also requires symlink python3 to be in path, although could just
    # call python, if module ensures that python3 sits first in the
    # path.
    
    args = [
        "aprun",
        "-axt",  # "-a xt" fails, try w/o space; really useful?
        "-n%d" % mcscript.run.parallel_width,
        "-b", "/usr/bin/env",
        "python3",  # call interpreter, so py file does not need to be executable
        mcscript.run.job_file
        ]

################################################################
# local setup and termination hooks
################################################################

def init():
    """ Does local setup tasks.

    Invoked after mcscript sets the various configuration variables
    and changed the cwd to the scratch directory.
    """

    # suppress FORTRAN STOP message for PGI compiler
    os.putenv("NO_STOP_MESSAGE","")

    # diagnostic... verify that CRAY_ROOTFS has been set and that /dsl is readable
    ## print "CRAY_ROOTFS found to be %s" % os.environ.get("CRAY_ROOTFS","(missing)")

def termination():
    """ Does local termination tasks.
    """
    
    pass
