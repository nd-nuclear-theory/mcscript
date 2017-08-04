"""config-slurm-nersc.py

    mcscript definitions for SLURM at NERSC

    Language: Python 3

    Mark A. Caprio
    University of Notre Dame

    + 12/29/16 (mac): Created, based on config-uge-ndcrc.py.
    + 3/18/17 (mac):
      - Update use of mcscript configuration variables.
      - Fix pass-through of environment variables.
      - Switch to node-based allocation.
    + 4/3/17 (mac): Disable cpu binding for edison.
    + 6/14/17 (pjf):
      - Add "--constraint" to select node type on cori.
      - Disable cpu binding for serial jobs on edison.
    + 7/29/17 (mac): cpu_bind=cores is now recommended for edison as well
    + 8/01/17 (pjf): Add basic config for knl,quad,cache.
"""

# Notes:
#
# Edison: 2 sockets * 12 cores * 2 hyperthreads; SLURM "CPU" is logical core (hyperthread)
#
#   http://www.nersc.gov/users/computational-systems/edison/running-jobs/example-batch-scripts/
#
# Cori Haswell
#
# http://www.nersc.gov/users/computational-systems/cori/running-jobs/general-running-jobs-recommendations/
#
# Common options:
#
# --opt="--mail-type=ALL"

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

    # start accumulating command line
    submission_invocation = [ "sbatch" ]

    # job name
    submission_invocation += ["--job-name={}".format(job_name)]

    # queue
    submission_invocation += ["--partition={}".format(args.queue)]

    # target cpu
    if os.environ["NERSC_HOST"] == "cori":
        if os.environ["CRAY_CPU_TARGET"] == "haswell":
            submission_invocation += ["--constraint=haswell"]
        elif os.environ["CRAY_CPU_TARGET"] == "mic-knl":
            submission_invocation += ["--constraint=knl,quad,cache"]

    # wall time
    submission_invocation += ["--time={}".format(args.wall)]

    # miscellaneous options
    license_list = ["SCRATCH","cscratch1","project"]
    submission_invocation += ["--licenses={}".format(",".join(license_list))]

    # calculate number of needed cores and nodes
    ## needed_cores = args.width * args.depth * args.spread
    ## needed_nodes = (needed_cores // args.nodesize) + int((needed_cores % args.nodesize) != 0)

    # generate parallel environment specifier
    submission_invocation += ["--nodes={}".format(args.nodes)]

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
        os.path.join(qsubm_path,"bash_job_wrapper.sh"),
        os.environ["MCSCRIPT_PYTHON"],
        job_file
    ]

    # standard input for submission
    submission_string = ""

    return (submission_invocation,submission_string)


################################################################
################################################################
# scripting runtime (user script)
################################################################
################################################################

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

    # Debugging at NERSC (mac/pjf,3/17/17,Edison): Undocumented
    # behavior of srun...  When srun is invoked under sbatch, and
    # sbatch has been given an --environment argument, srun does *not*
    # behave as advertised:
    #
    # --export=<environment variables | NONE>
    #   ... By default all environment variables are propagated. ...
    #
    # Instead, only environment variables which were explicitly passed
    # to sbatch, plus the SLURM_* environment variables, are
    # propagated by srun.
    #
    # The solution is to invoke srun with the --export option, given
    # the undocumented value "ALL".  (This value was documented for
    # sbatch but not for srun.):
    #
    #   srun --export=ALL ...

    if (not mcscript.parameters.run.batch_mode):
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
            "--cpus-per-task={}".format(mcscript.parameters.run.hybrid_nodesize),
            "--export=ALL"
        ]

        # 7/29/17 (mac): cpu_bind=cores is now recommended for edison as well
        # cpu_bind=cores is recommended for cori but degrades performance on edison (mac, 4/3/17)
        invocation += [
            "--cpu_bind=cores"
        ]

        invocation += base

    return invocation

def hybrid_invocation(base):
    """ Generate subprocess invocation arguments for parallel run.

    Arguments:
        base (list of str): invocation of basic command to be executed

    Returns:
        (list of str): full invocation
    """

    # calculate number of needed cores and nodes
    undersubscription_factor = 1
    needed_threads = mcscript.parameters.run.hybrid_ranks * mcscript.parameters.run.hybrid_threads * undersubscription_factor
    print("nodesize",mcscript.parameters.run.hybrid_nodesize)
    needed_nodes = (needed_threads // mcscript.parameters.run.hybrid_nodesize) + int((needed_threads % mcscript.parameters.run.hybrid_nodesize) != 0)

    # note: may need to be revised to enable hyperthreading, i.e.,
    # to provide different depth in OMP_NUM_THREADS and in srun

    # for ompi
    requested_threads_per_rank = mcscript.parameters.run.hybrid_threads*undersubscription_factor
    invocation = [
        "srun",
        ## "--cpu_bind=verbose",
        "--ntasks={}".format(mcscript.parameters.run.hybrid_ranks),
        "--cpus-per-task={}".format(requested_threads_per_rank),
        "--export=ALL"
    ]
    # 4/3/17 (mac): cpu_bind=cores is recommended for cori but degrades performance on edison
    # 7/29/17 (mac): cpu_bind=cores is now recommended for edison as well
    invocation += [
        "--cpu_bind=cores"
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

    # set node size based on environment
    mcscript.parameters.run.hybrid_nodesize = None
    if (os.getenv("NERSC_HOST")=="edison"):
        mcscript.parameters.run.hybrid_nodesize = 24*2
    elif (os.getenv("NERSC_HOST")=="cori"):
        if (os.getenv("CRAY_CPU_TARGET")=="haswell"):
            mcscript.parameters.run.hybrid_nodesize = 32*2
        elif (os.getenv("CRAY_CPU_TARGET")=="mic-knl"):
            mcscript.parameters.run.hybrid_nodesize = 64*4

    # set install prefix based on environment
    mcscript.parameters.run.install_dir = os.path.join(
        mcscript.parameters.run.install_dir, os.getenv("CRAY_CPU_TARGET")
        )

    # Cori recommended thread affinity settings

    # TODO: wrap in special config command for offline support
    os.environ["OMP_PROC_BIND"] = "spread"
    os.environ["OMP_PLACES"] = "threads"

def termination():
    """ Do any local termination tasks.
    """

    pass
