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
    + 10/11/17 (pjf): Add switch constraint.
    + 02/11/18 (pjf): Pass entire environment.
    + 07/06/18 (pjf): Remove use of hybrid_nodesize.
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
import math

from . import parameters


# cluster_specs[NERSC_HOST][CRAY_CPU_TARGET] = (cores, threads/core)
cluster_specs = {
    "edison": {
        "sandybridge": (16, 2),
        "ivybridge": (24, 2),
    },
    "cori": {
        "haswell": (32, 2),
        "knl": (68, 4),
    },
}

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

    # start accumulating command line
    submission_invocation = [ "sbatch" ]

    # deadline (end of allocation year)
    submission_invocation += ["--deadline=2020-01-13T23:59:59"]

    # job name
    submission_invocation += ["--job-name={}".format(job_name)]

    # queue
    submission_invocation += ["--qos={}".format(args.queue)]

    # wall time
    submission_invocation += ["--time={}".format(args.wall)]

    # job array for repetitions
    if args.num > 1:
        submission_invocation += ["--array={:g}-{:g}".format(0, args.num-1)]

    if args.queue == "xfer":
        if os.environ["NERSC_HOST"] == "cori":
            submission_invocation += ["--clusters=escori"]
        elif os.environ["NERSC_HOST"] == "edison":
            submission_invocation += ["--clusters=esedison"]
    elif args.queue in ["debug", "regular", "premium", "shared"]:
        if os.environ["NERSC_HOST"] == "cori":
            # target cpu
            if os.environ["CRAY_CPU_TARGET"] == "haswell":
                submission_invocation += ["--constraint=haswell"]
            elif os.environ["CRAY_CPU_TARGET"] == "mic-knl":
                submission_invocation += ["--constraint=knl,quad,cache"]

            # ask for compactness (correct number of switches)
            nodes_per_switch = 384
            needed_switches = math.ceil(args.nodes/nodes_per_switch)
            submission_invocation += ["--switches={:d}@{:s}".format(needed_switches, args.switchwaittime)]

        # generate parallel environment specifier
        submission_invocation += ["--nodes={}".format(args.nodes)]

    # miscellaneous options
    license_list = ["SCRATCH", "cscratch1", "project"]
    submission_invocation += ["--licenses={}".format(",".join(license_list))]

    # append user-specified arguments
    if (args.opt is not None):
        submission_invocation += args.opt

    # environment definitions
    submission_invocation += ["--export=ALL"]

    # wrapper call
    #
    # calls interpreter explicitly, so do not have to rely upon default python
    #   version or shebang line in script
    if "csh" in os.environ.get("SHELL"):
        job_wrapper = os.path.join(qsubm_path, "csh_job_wrapper.csh")
    elif "bash" in os.environ.get("SHELL"):
        job_wrapper = os.path.join(qsubm_path, "bash_job_wrapper.sh")
    submission_invocation += [
        job_wrapper,
        os.environ["MCSCRIPT_PYTHON"],
        job_file
    ]

    # standard input for submission
    submission_string = ""
    # use job arrays for repetition
    repetitions = 1

    return (submission_invocation, submission_string, repetitions)


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

    if (not parameters.run.batch_mode):
        # run on front end (though might sometimes want to run on compute
        # node if have interactive allocation)
        invocation = base
    else:
        if os.getenv("NERSC_HOST") == "cori":
            # run unwrapped on Cori
            invocation = base
        else:
            # run on compute node on Edison
            invocation = [
                "srun",
                "--ntasks={}".format(1),
                "--nodes={}".format(1),
                "--cpus-per-task={}".format(parameters.run.serial_threads),
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

    # for ompi
    invocation = [
        "srun",
        ## "--cpu_bind=verbose",
        "--ntasks={}".format(parameters.run.hybrid_ranks),
        "--cpus-per-task={}".format(parameters.run.hybrid_threads),
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
    # Cori recommended thread affinity settings
    print("Setting OMP_PROC_BIND to {}.".format("spread"))
    os.environ["OMP_PROC_BIND"] = "spread"
    print("Setting OMP_PLACES to {}.".format("cores"))
    os.environ["OMP_PLACES"] = "cores"


################################################################
# local setup and termination hooks
################################################################

def init():
    """ Do any local setup tasks.

    Invoked after mcscript sets the various configuration variables
    and changed the cwd to the scratch directory.
    """

    # set install prefix based on environment
    parameters.run.install_dir = os.path.join(
        parameters.run.install_dir, os.getenv("CRAY_CPU_TARGET")
        )

def termination():
    """ Do any local termination tasks.
    """

    pass
