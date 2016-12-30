"""config-slurm-nersc.py

    mcscript definitions for SLURM at NERSC

    Language: Python 3
    Mark A. Caprio
    University of Notre Dame

    + 12/29/16 (mac): Created, based on config-uge-ndcrc.py.

"""


# Edison: 2 sockets * 12 cores * 2 hyperthreads; SLURM "CPU" is logical core (hyperthread)
#
#   When not hyperthreading, just take nodesize to be 24.
#
#   http://www.nersc.gov/users/computational-systems/edison/running-jobs/example-batch-scripts/

# Cori Haswell
#
# http://www.nersc.gov/users/computational-systems/cori/running-jobs/general-running-jobs-recommendations/

# Common options:
#
# --opt="--mail-type=ALL"

import os
import sys

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

    # assert not epar
    if (args.epar is not None):
        raise(ValueError("epar presently not supported by this scripting"))

    # start accumulating command line
    submission_invocation = [ "sbatch" ]

    # job name
    submission_invocation += ["--job-name={}".format(job_name)]

    # queue
    submission_invocation += ["--partition={}".format(args.queue)]

    # wall time
    submission_invocation += ["--time={}".format(args.wall)]

    # miscellaneous options
    license_list = ["SCRATCH","project"]
    submission_invocation += ["--licenses={}".format(",".join(license_list))]
                        
    # parallel environment
    ## looks_parallel = not ( (args.epar is None) and (args.width == 1) and (args.depth == 1) and (args.nodesize == None) )

    # calculate number of needed cores and nodes
    needed_cores = args.width * args.depth * args.spread
    needed_nodes = (needed_cores // args.nodesize) + int((needed_cores % args.nodesize) != 0)

    # generate parallel environment specifier
    submission_invocation += ["--nodes={}".format(needed_nodes)]

    # append user-specified arguments
    if (args.opt is not None):
        submission_invocation += args.opt

    # environment definitions
    submission_invocation += ["--export={}".format(",".join(environment_definitions))]

    # wrapper call
    #
    # calls interpreter explicitly, so do not have to rely upon default python
    #   version or shebang line in script
    submission_invocation += [
        os.path.join(qsubm_path,"csh_job_wrapper.csh"),
        os.environ["MCSCRIPT_PYTHON"],
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
#
# Provides access to parameters in mcscript.run.
import mcscript

################################################################
# job identification
################################################################

def job_id():
    """ Retrieve job id.

    Returns job id (as string), or "0" if missing.
    """

    return os.environ.get("SLURM_JOB_ID","0")

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

    if (not mcscript.run.batch_mode):
        # run on front end (though might sometimes want to run on compute
        # node if have interactive allocation)
        invocation = base
    else:
        # run on compute node (for Edison)
        #
        # Perhaps could run unwrapped on Cori?
        invocation = [
            "srun",
            "--ntasks={}".format(1),
            "--nodes={}".format(1),
            "--cpus-per-task={}".format(mcscript.run.node_size)
        ]

        invocation += base

    return invocation

def parallel_invocation(base):
    """ Generate subprocess invocation arguments for parallel run.

    Arguments:
        base (list of str): invocation of basic command to be executed

    Returns:
        (list of str): full invocation
    """

    # calculate number of needed cores and nodes
    needed_cores = mcscript.run.parallel_width * mcscript.run.parallel_depth * mcscript.run.parallel_spread
    needed_nodes = (needed_cores // mcscript.run.parallel_nodesize) + int((needed_cores % mcscript.run.parallel_nodesize) != 0)

    # note: may need to be revised to enable hyperthreading, i.e.,
    # to provide different depth in OMP_NUM_THREADS and in srun

    # for ompi
    invocation = [
        "srun",
        "--cpu_bind=verbose",
        "--ntasks={}".format(mcscript.run.parallel_width),
        "--nodes={}".format(needed_nodes),  # supposedly extraneous in Edison example scripts
        "--cpu_bind=cores",  # recommended for Cori Haswell, if MPI tasks per node do not divide 64, not exceeding physical CPUs (32/node)
        "--cpus-per-task={}".format(mcscript.run.parallel_depth*mcscript.run.parallel_spread)  # basic Edison approach; needs modification on Cori if not "packed"
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

    # Cori recommended thread affinity settings
    os.environ["OMP_PROC_BIND"] = "spread"
    os.environ["OMP_PLACES"] = "threads"


def termination():
    """ Do any local termination tasks.
    """
    
    pass
