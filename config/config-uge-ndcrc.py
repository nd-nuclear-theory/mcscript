"""config-uge-ndcrc.py

    mcscript definitions for Univa Grid Engine at the Notre Dame CRC

    Language: Python 3
    Mark A. Caprio
    University of Notre Dame

    + 11/22/16 (mac): Created, based on qsubm_local_ndcrc.py and
      mcscript_local_ndcrc.py (originated ~7/13 and last modified
      ~12/14).

"""

import os
import sys

################################################################
################################################################
# scripting submission (qsubm)
################################################################
################################################################

#  NDCRC: To select hardware via pe request, set nodesize.  Then,
#  optionally, specify width/depth.  These determine node reservation
#  via pe request, plus they are passed to run script via environment
#  to allow determination of MPI/OMP parameters.
#
#  Wall time is not communicated in queue request but is passed on to script.
#
#  Note: Currently only support mpi environment, not smp environment.
#
#  EX: MPI on HPC cluster (8-core)
#
#      qsubm 0290 long 1440 --width=231 --nodesize=8 --pool=Nmax06
#
#  EX: OpenMP on any available 12-core cluster (12-core)
#
#      qsubm 0298 long --depth=12 --nodesize=12 --pool=Nmax06 
#
#  EX: default single core request on long cluster (12-core),
#  script MPI call uses default width 1
#
#      qsubm 0291 long 30 --pool=Nmax04

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

    submission_invocation = [ "qsub" ]

    # job name
    submission_invocation += ["-N", "%s" % job_name]

    # queue
    submission_invocation += ["-q", "%s" % args.queue]

    # wall time
    pass  # enforced by queue

    # miscellaneous options
    submission_invocation += ["-j","y"]  # merge standard error
    submission_invocation += ["-r","n"]  # job not restartable
                        
    # parallel environment
    if (  not ( (args.epar is None) and (args.width == 1) and (args.depth == 1) and (args.nodesize == None) ) ):

        # check that nodesize was specified
        if (args.nodesize is None):
            print ("Please specify --nodesize for parallel run on NDCRC.")
            sys.exit(1)

        # calculate number of needed cores
        if (args.epar is not None):
            # epar -- serial or smp
            needed_cores = args.epar * args.depth
        else:
            # standars -- smp/mpi
            needed_cores = args.width * args.depth
        rounded_cores = args.nodesize * (needed_cores // args.nodesize)
        if ((needed_cores % args.nodesize) != 0):
            rounded_cores += args.nodesize

        # generate parallel environment specifier
        if (args.width != 1):
            # handle mpi run
            submission_invocation += ["-pe", "mpi-%d %d" % (args.nodesize, rounded_cores) ]
        elif (args.depth != 1):
            # handle smp run
            submission_invocation += ["-pe", "smp %d" % (args.nodesize) ]

    # append user-specified arguments
    if (args.opt is not None):
        submission_invocation += args.opt.split(",")

    # environment definitions
    submission_invocation += ["-v", "%s" % ",".join(environment_definitions)]

    # job command
    if (args.epar is not None):
        raise(ValueError("epar presently not supported"))

    submission_invocation += [
        os.path.join(qsubm_path,"wrapper.csh"),  # csh wrapper required at NDCRC
        os.environ["MCSCRIPT_PYTHON"], # call interpreter, so py file does not need to be executable
        job_file
    ]

    # stdin to qsubm
    submission_string = ""

    return (submission_invocation,submission_string)


################################################################
################################################################
# scripting runtime (user script)
################################################################
################################################################

# serial jobs: nothing special
# MPI jobs: standard mpiexec, TODO OMP
# epar jobs: TODO


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

def parallel_invocation(base):
    """ Generate subprocess invocation arguments for parallel runq.

    Arguments:
        base (list of str): invocation of basic command to be executed

    Returns:
        (list of str): full invocation
    """

    # for mpich2
    ## parallel_config = [
    ##     "mpiexec",
    ##     "-n", "%d" % run.parallel_width,
    ##     "-ranks-per-proc", "%d" % run.parallel_depth
    ##     ]

    # for mpich -- haven't yet checked how to do depth

    invocation = [
        "mpiexec",
        "--n={}".format(mcscript.run.parallel_width),
        "--map-by=core:PE={}:NOOVERSUBSCRIBE".format(mcscript.run.parallel_depth),
        "--preload-binary"
    ]
    invocation += base

    return invocation

## ################################################################
## # embarassingly-parallel job-script relaunching definitions
## ################################################################
## 
## def epar_relaunch_args():
##     """ Generate arguments for relaunching script file in epar run.
##     """
## 
##     ## # embarassingly parallel launch arguments
##     ## epar_args = [
##     ##         "mpiexec",
##     ##         "-n%d" % mcscript.parallel_width,
##     ##         "-b", "/usr/bin/env",
##     ##         "python",  # call interpreter, so py file does not need to be executable
##     ##         mcscript.job_file
##     ##         ]
## 
##     # TODO for ND
##     return []
## 

################################################################
# local setup and termination hooks
################################################################

def init():
    """ Does any local setup tasks.

    Invoked after mcscript sets the various configuration variables
    and changed the cwd to the scratch directory.
    """

    pass

def termination():
    """ Does any local termination tasks.
    """
    
    pass
