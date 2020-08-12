"""config-cobalt-alcf.py

    mcscript definitions for Cobalt at ALCF (ANL)

    Language: Python 3

    Patrick J. Fasano
    University of Notre Dame

    + 05/06/20 (pjf): Created, based on config-slurm-nersc.py.
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

import datetime
import os
import sys
import math

from . import control
from . import exception
from . import parameters


cluster_specs = {
    "theta": {
        "mic-knl": {
            "cores": 64,
            "threads_per_core": 4,
            "domains": 4,
            "cores_per_domain": 16,
        },
    },
}

################################################################
################################################################
# scripting submission (qsubm)
################################################################
################################################################


def qsubm_arguments(parser):
    """Add site-specific arguments to qsubm.

    Arguments:
        parser (argparse.ArgumentParser): qsubm argument parser context
    """
    group = parser.add_argument_group("ALCF-specific options")
    group.add_argument(
        "--attrs", type=str,
        help="list of attributes for a job that must be fulfilled for a job to run"
    )
    group.add_argument(
        "--project", type=str,
        help="charge resources used by this job to specified project"
    )
    group.add_argument(
        "--dependency", type=str,
        help="defer the start of this job until the specified dependencies have been satisfied"
    )


def submission(job_name, job_file, qsubm_path, environment_definitions, args):
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

    #### check option sanity ####
    # convenience definitions
    alcf_host = "theta"  ## hard-coded for lack of relevant environment variable
    cpu_target = os.environ["CRAY_CPU_TARGET"]
    node_cores = cluster_specs[alcf_host][cpu_target]["cores"]
    threads_per_core = cluster_specs[alcf_host][cpu_target]["threads_per_core"]
    node_threads = node_cores*threads_per_core
    node_domains = cluster_specs[alcf_host][cpu_target]["domains"]
    domain_cores = cluster_specs[alcf_host][cpu_target]["cores_per_domain"]
    domain_threads = domain_cores*threads_per_core

    try:
        # check for oversubscription
        if args.threads > node_threads:
            raise exception.ScriptError(
                "--threads={:d} greater than threads on single node ({:d})".format(
                    args.threads, node_threads
                )
            )
        if args.serialthreads > node_threads:
            raise exception.ScriptError(
                "--serialthreads={:d} greater than threads on single node ({:d})".format(
                    args.serialthreads, node_threads
                )
            )
        aggregate_threads = args.nodes*node_threads
        if args.ranks*args.threads > aggregate_threads:
            raise exception.ScriptError(
                "total threads ({:d}) greater than total available threads ({:d})".format(
                    args.ranks*args.threads, aggregate_threads
                )
            )

        # check for undersubscription
        if args.nodes > args.ranks:
            raise exception.ScriptError(
                "--nodes={:d} greater than --ranks={:d}".format(args.nodes, args.ranks)
            )

        # check for inefficient run on multiple nodes
        if args.nodes > 1:
            if math.log2(args.threads/domain_threads)%1 != 0:
                raise exception.ScriptError(
                    "--threads={:d} is not a power of two times threads per domain ({:d})".format(
                        args.threads, domain_threads
                    )
                )
            if math.ceil(args.ranks/args.nodes) > node_cores:
                raise exception.ScriptError(
                    "ranks per node ({:d}) greater than cores per node ({:d})".format(
                        math.ceil(args.ranks/args.nodes), args.cores
                    )
                )
    except exception.ScriptError as err:
        if args.expert:
            print(str(err))
        else:
            raise err

    # start accumulating command line
    submission_invocation = [ "qsub" ]

    # job name
    submission_invocation += ["--jobname={}".format(job_name)]

    # queue
    submission_invocation += ["--queue={}".format(args.queue)]

    # wall time
    submission_invocation += ["--time={}".format(args.wall)]

    # node count
    submission_invocation += ["--nodecount={}".format(args.nodes)]

    # # core specialization
    # if args.nodes > 1:
    #     submission_invocation += ["--core-spec={}".format(node_cores-(domain_cores*node_domains))]

    if args.attrs is not None:
        submission_invocation += ["--attrs={}".format(args.attrs)]
    if args.project is not None:
        submission_invocation += ["--project={}".format(args.project)]
    if args.dependency is not None:
        submission_invocation += ["--dependencies={}".format(args.dependencies)]

    # append user-specified arguments
    if (args.opt is not None):
        submission_invocation += args.opt

    # environment definitions
    if environment_definitions:
        submission_invocation += ["--env", ":".join(environment_definitions)]

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
    repetitions = args.num

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

    if (not os.environ.get("COBALT_JOBID")):
        # run on front end
        invocation = base
    else:
        # run on compute node on Edison
        invocation = [
            "aprun",
            "-n", "1",  # ranks
            "--cpus-per-pe={}".format(parameters.run.serial_threads),
            "--cpu-binding=depth"
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
    # ensure that we're running inside a compute job
    if not os.environ.get("COBALT_JOBID"):
        raise exception.ScriptError("Hybrid mode only supported inside Cobalt allocation!")

    # for ompi
    invocation = [
        "aprun",
        "-n", "{}".format(parameters.run.hybrid_ranks),
        "--cpus-per-pe={}".format(parameters.run.hybrid_threads),
        "--cpu-binding=depth"
    ]

    # use local path instead
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
    os.environ["OMP_PLACES"] = "threads"


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
