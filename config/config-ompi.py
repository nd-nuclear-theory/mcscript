"""config-ompi.py

    mcscript definitions for local runs only (no batch) with Open MPI syntax.


    Language: Python 3
    Mark A. Caprio
    University of Notre Dame

    + 11/22/16 (mac): Created, based on qsubm_local_ndcrc.py and
      mcscript_local_ndcrc.py (originated ~7/13 and last modified
      ~12/14).
    + 02/08/22 (pjf): Add signal handling for SIGTERM.

"""

import os
import signal
import sys

from . import (
    parameters,
    utils,
)

################################################################
################################################################
# scripting submission (qsubm)
################################################################
################################################################


def submission(job_name,job_file,qsubm_path,environment_definitions,args):
    """Prepare submission command invocation.

    Arguments:

        job_name (str): job name string

        job_file (str): job script file

        qsubm_path (str): path to qsubm files (for locating wrapper script)

        environment_definitions (list of str): list of environment variable definitions
        to include in queue submission arguments

        args (...): qsub's argument parser return structure (contains
        lots of parameters)

    Returns:
        (tuple): (submission_invocation, submission_string, repetitions)

             submission_invocation: list of arguments for subprocess.call

             submission_string: string giving standard input for
             subprocess

             repetitions: number of times to call submission

    """

    raise(ScriptError("no batch submission"))


################################################################
################################################################
# scripting runtime (user script)
################################################################
################################################################

# serial jobs: nothing special
# MPI jobs: standard mpiexec, TODO OMP
# epar jobs: TODO

################################################################
# job identification
################################################################

def job_id():
    """ Retrieve job id.

    Returns job id (as string), or "0" if missing.
    """

    return os.environ.get("JOB_ID","0")

################################################################
# serial and parallel code launching definitions
################################################################

def serial_invocation(base):
    """ Generate subprocess invocation arguments for serial.

    May depend on run mode:
    local for invocation in local run (i.e., invocation on front end)
    batch for invocation in batch run
    epar for invocation in epar run

    Arguments:
        base (list of str): invocation of basic command to be executed

    Returns:
        (list of str): full invocation
    """

    invocation = base

    return base

def hybrid_invocation(base):
    """ Generate subprocess invocation arguments for parallel run.

    Arguments:
        base (list of str): invocation of basic command to be executed

    Returns:
        (list of str): full invocation
    """

    # TODO: may want to add some thread binding directives
    #
    # https://www.olcf.ornl.gov/kb_articles/task-core-affinity-on-commodity-clusters/
    # https://www.olcf.ornl.gov/kb_articles/parallel-job-execution-on-commodity-clusters/

    # for ompi
    invocation = [
        "mpiexec",
        "--n","{:d}".format(parameters.run.hybrid_ranks)
    ]
    invocation += base

    return invocation

################################################################
# OpenMP setup
################################################################

def openmp_setup(threads):
    """ Set OpenMP environment variables.

    Arguments:
        threads (int): number of threads
    """
    # TODO: wrap in special config command for offline support

    # set number of threads by global qsubm depth parameter
    print("Setting OMP_NUM_THREADS to {}.".format(threads))
    os.environ["OMP_NUM_THREADS"] = str(threads)
    print("Setting OMP_PROC_BIND to {}.".format("spread"))
    os.environ["OMP_PROC_BIND"] = "spread"
    print("Setting OMP_PLACES to {}.".format("threads"))
    os.environ["OMP_PLACES"] = "threads"


################################################################
# local setup and termination hooks
################################################################

def init():
    """ Do any local setup tasks.

    Invoked after mcscript sets the various configuration variables
    and changed the cwd to the scratch directory.
    """

    signal.signal(signal.SIGTERM, utils.TaskTimer.handle_exit_signal)

def termination():
    """ Do any local termination tasks.
    """

    pass
