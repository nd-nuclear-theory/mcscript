"""config-uge-ndcrc.py

    mcscript definitions for Univa Grid Engine at the Notre Dame CRC


    Example:

        # environment configuration -- put this in your .cshrc
        setenv MCSCRIPT_DIR ${HOME}/projects/mcscript
        setenv MCSCRIPT_RUN_HOME ${HOME}/runs
        setenv MCSCRIPT_WORK_HOME ${SCRATCH}/runs
        setenv MCSCRIPT_RUN_PREFIX run
        setenv MCSCRIPT_PYTHON python3
        setenv PATH ${MCSCRIPT_DIR}/tools:${PATH}
        setenv PYTHONPATH ${MCSCRIPT_DIR}/..:${PYTHONPATH}

        # link to local config
        cd projects/mcscript
        ln -s config/config-uge-ndcrc.py config.py
 
        # build hybrid test program
        cd example
        module load ompi/1.10.2-gcc-4.9.2
        mpicc -fopenmp hello_hybrid.c -o hello_hybrid
        cd ..

        # load python3
        #   must do *after* loading gcc 4.9.2 due to version conflict
        module load python/3.4.0
        
        qsubm ex00
        qsubm ex01 --toc
        qsubm ex01 --pool="greet"
        qsubm ex02 --width=4
        qsubm ex02 --width=4 --depth=2


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

    # assert not epar
    if (args.epar is not None):
        raise(ValueError("epar presently not supported by this scripting"))

    # start accumulating command line
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
    if (  not ( (args.epar is None) and (args.hybrid_ranks == 1) and (args.hybrid_threads == 1) and (args.hybrid_nodesize == None) ) ):

        # check that nodesize was specified
        if (args.hybrid_nodesize is None):
            print ("Please specify --nodesize for parallel run on NDCRC.")
            sys.exit(1)

        # calculate number of needed cores
        needed_cores = args.hybrid_ranks * args.hybrid_threads
        rounded_cores = args.hybrid_nodesize * (needed_cores // args.hybrid_nodesize)
        if ((needed_cores % args.hybrid_nodesize) != 0):
            rounded_cores += args.hybrid_nodesize

        # generate parallel environment specifier
        if (args.hybrid_ranks != 1):
            # handle mpi run
            submission_invocation += [
                "-pe",
                "mpi-{nodesize:d} {rounded_cores:d}".format(nodesize=args.hybrid_nodesize,rounded_cores=rounded_cores)
            ]
        elif (args.hybrid_threads != 1):
            # handle smp run
            submission_invocation += [
                "-pe",
                "smp {nodesize:d}".format(nodesize=args.hybrid_nodesize)
            ]

    # append user-specified arguments
    if (args.opt is not None):
        submission_invocation += args.opt

    # environment definitions
    submission_invocation += [
        "-v",
        ",".join(environment_definitions)
    ]

    submission_invocation += [
        os.path.join(qsubm_path,"csh_job_wrapper.csh"),  # csh wrapper required at NDCRC
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

def hybrid_invocation(base):
    """ Generate subprocess invocation arguments for parallel run.

    Arguments:
        base (list of str): invocation of basic command to be executed

    Returns:
        (list of str): full invocation
    """

    # for ompi
    invocation = [
        "mpiexec",
        "--report-bindings",
        "--n","{:d}".format(mcscript.run.hybrid_ranks),
        "--map-by","node:PE={:d}:NOOVERSUBSCRIBE".format(mcscript.run.hybrid_ranks)  # TODO fix up use of new binding syntax
    ]
    ##print("WARNING: TODO still need to fix binding syntax for parallel depth in config-uge-ndcrc")
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
