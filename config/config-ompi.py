"""config-ompi.py

    mcscript definitions for local runs only (no batch) with Open MPI syntax.


    Language: Python 3
    Mark A. Caprio
    University of Notre Dame

    + 11/22/16 (mac): Created, based on qsubm_local_ndcrc.py and
      mcscript_local_ndcrc.py (originated ~7/13 and last modified
      ~12/14).

"""

import os
import sys

import mcscript.parameters

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
        (tuple): (submission_invocation,submission_string)

             submission_invocation: list of arguments for subprocess.call

             submission_string: string giving standard input for
             subprocess

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
        "--n","{:d}".format(mcscript.parameters.run.hybrid_ranks)
    ]
    invocation += base

    return invocation

################################################################
# local setup and termination hooks
################################################################

def init():
    """ Do any local setup tasks.

    Invoked after mcscript sets the various configuration variables
    and changed the cwd to the scratch directory.
    """

    pass

def termination():
    """ Do any local termination tasks.
    """
    
    pass