""" mcscript_local_ndcrc.py -- local definitions for mcscript

    Version for NDCRC.

    serial jobs: nothing special
    MPI jobs: standard mpiexec, TODO OMP
    epar jobs: TODO

    Language: Python 3
    Mark A. Caprio
    University of Notre Dame
    Written ~7/13 (mac).
    Last modified 6/11/14 (mac).

"""

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

    return os.environ.get("JOB_ID","0")

################################################################
# module system
################################################################

def module_command():
    """ Determine module command path on cluster.

    Returns:
        (string) : Fully qualified module command name.
    """

    return "/opt/crc/Modules/current/bin/modulecmd"

################################################################
# serial and parallel code launching definitions
################################################################

def serial_prefix(mode):
    """ Generate serial run prefix arguments for given moded.

    mode: run mode

    "local" for invocation in local run (i.e., invocation on front end)
    
    "batch" for invocation in batch run
    
    "epar" for invocation in epar run
    
    """
    
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

    # for mpich2
    ## parallel_config = [
    ##     "mpiexec",
    ##     "-n", "%d" % run.parallel_width,
    ##     "-ranks-per-proc", "%d" % run.parallel_depth
    ##     ]

    # for mpich -- haven't yet checked how to do depth

    args = [
    "mpiexec",
    "-n", "%d" % run.parallel_width
    ]

    return args

################################################################
# embarassingly-parallel job-script relaunching definitions
################################################################

def epar_relaunch_args():
    """ Generate arguments for relaunching script file in epar run.
    """

    ## # embarassingly parallel launch arguments
    ## epar_args = [
    ##         "mpiexec",
    ##         "-n%d" % mcscript.parallel_width,
    ##         "-b", "/usr/bin/env",
    ##         "python",  # call interpreter, so py file does not need to be executable
    ##         mcscript.job_file
    ##         ]

    # TODO for ND
    return []

################################################################
# local setup and termination hooks
################################################################

def init():
    """ Does local setup tasks.

    Invoked after mcscript sets the various configuration variables
    and changed the cwd to the scratch directory.
    """

    pass

def termination():
    """ Does local termination tasks.
    """
    
    pass
