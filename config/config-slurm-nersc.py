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
    + 01/18/19 (pjf): Update deadline for AY19.
    + 04/07/19 (pjf):
        - Check SLURM_JOB_ID to determine whether or not to use `srun`.
        - Distribute executable via `sbcast` if using more than 128 nodes.
    + 06/04/19 (pjf): Add NERSC-specific command-line options.
    + 07/09/19 (mac): Change srun parameter from cpu_bind to cpu-bind.
    + 09/11/19 (pjf):
        - Add checks on submission parameters (nodes, ranks, threads, etc.);
          overrided in expert mode.
        - Add core specialization (--core-spec) on multi-node runs.
    + 01/07/20 (pjf): Update deadline for AY20.
    + 06/02/20 (pjf): Get wall_time_sec from Slurm on job launch.
    + 10/09/20 (pjf): Gracefully recover if unable to get wall time from Slurm.
    + 10/10/20 (pjf): Further improve Slurm wall time parsing.
    + 10/11/20 (pjf):
        - Rename `--num` to `--jobs`.
        - Add support for multiple workers per job.
    + 01/21/21 (mac): Update deadline for AY21.
    + 01/29/21 (pjf): Update deadline for AY21; remove AY19,AY20.
    + 01/10/22 (mac): Push back deadline for AY21.
    + 02/08/22 (pjf): Add signal handling for SIGUSR1.
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
import signal
import subprocess
import shutil

from . import control
from . import exception
from . import parameters
from . import utils


cluster_specs = {
    "cori": {
        "haswell": {
            "cores": 32,
            "threads_per_core": 2,
            "domains": 2,
            "cores_per_domain": 16,
        },
        "mic-knl": {
            "cores": 68,
            "threads_per_core": 4,
            "domains": 4,
            "cores_per_domain": 16,
        },
    },
}

# cache of broadcasted executables -- job local
broadcasted_executables = {}

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
    group = parser.add_argument_group("NERSC-specific options")
    group.add_argument(
        "--account", type=str,
        help="charge resources used by this job to specified account"
    )
    group.add_argument(
        "--bb", type=str,
        help="burst buffer specification"
    )
    group.add_argument(
        "--bbf", type=str,
        help="path of file containing burst buffer specification"
    )
    group.add_argument(
        "--dependency", type=str,
        help="defer the start of this job until the specified dependencies have been satisfied"
    )
    group.add_argument(
        "--mail-type", type=str,
        help="notify user by email when certain event types occur."
    )
    group.add_argument(
        "--switchwaittime", type=str, default="12:00:00",
        help="maximum time to wait for switch count"
    )


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

    #### check option sanity ####
    # convenience definitions
    nersc_host = os.environ["NERSC_HOST"]
    cpu_target = os.environ["CRAY_CPU_TARGET"]
    node_cores = cluster_specs[nersc_host][cpu_target]["cores"]
    threads_per_core = cluster_specs[nersc_host][cpu_target]["threads_per_core"]
    node_threads = node_cores*threads_per_core
    node_domains = cluster_specs[nersc_host][cpu_target]["domains"]
    domain_cores = cluster_specs[nersc_host][cpu_target]["cores_per_domain"]
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
    submission_invocation = [ "sbatch" ]

    # deadline (end of allocation year)
    ay21_end_date = datetime.datetime.fromisoformat("2022-01-19T00:06:59")
    if datetime.datetime.now() < ay21_end_date:
        submission_invocation += ["--deadline={}".format(ay21_end_date.isoformat())]

    # job name
    submission_invocation += ["--job-name={}".format(job_name)]

    # queue
    submission_invocation += ["--qos={}".format(args.queue)]

    # wall time
    submission_invocation += ["--time={}".format(args.wall)]

    # core specialization
    if args.nodes > 1:
        submission_invocation += ["--core-spec={}".format(node_cores-(domain_cores*node_domains))]

    # job array for repetitions
    if args.jobs > 1:
        submission_invocation += ["--array={:g}-{:g}".format(0, args.jobs-1)]

    if args.queue == "xfer":
        ## if os.environ["NERSC_HOST"] == "cori":
        ##     submission_invocation += ["--clusters=escori"]
        ## elif os.environ["NERSC_HOST"] == "edison":
        ##     submission_invocation += ["--clusters=esedison"]
        control.module(["load", "esslurm"])
    elif args.queue in ["debug", "regular", "premium", "shared", "low"]:
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
        submission_invocation += ["--nodes={}".format(args.nodes*args.workers)]

    # miscellaneous options
    license_list = ["SCRATCH", "cscratch1", "project"]
    submission_invocation += ["--licenses={}".format(",".join(license_list))]

    if args.account is not None:
        submission_invocation += ["--account={}".format(args.account)]
    if args.bb is not None:
        submission_invocation += ["--bb={}".format(args.bb)]
    if args.bbf is not None:
        submission_invocation += ["--bbf={}".format(args.bbf)]
    if args.dependency is not None:
        submission_invocation += ["--dependency={}".format(args.dependency)]
    if args.mail_type is not None:
        submission_invocation += ["--mail-type={}".format(args.mail_type)]

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
    ]

    # use GNU parallel to launch multiple workers per job
    if args.workers > 1:
        if not shutil.which("parallel"):
            raise exception.ScriptError("multiple workers per job requires GNU parallel")
        submission_invocation += [
            "parallel",
            "--verbose",
            "--jobs={:d}".format(args.workers),
            "--delay={:d}".format(5),
            "--line-buffer",
            "--tag",
            "{mcscript_python:s} {job_file:s}".format(
                mcscript_python=os.environ["MCSCRIPT_PYTHON"],
                job_file=job_file
            ),
            ":::",
            " ".join(map("worker{:02d}".format,range(args.workers))),
        ]
    else:
        submission_invocation += [
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

    if (not os.environ.get("SLURM_JOB_ID")):
        # run on front end
        invocation = base
    else:
        if (os.getenv("NERSC_HOST") == "cori") and (parameters.run.num_workers == 1):
            # run unwrapped on Cori
            invocation = base
        else:
            # run on compute node
            invocation = [
                "srun",
                "--ntasks={}".format(1),
                "--nodes={}".format(1),
                "--cpus-per-task={}".format(parameters.run.serial_threads),
                "--export=ALL"
            ]

            # 7/29/17 (mac): cpu-bind=cores is now recommended for edison as well
            # cpu-bind=cores is recommended for cori but degrades performance on edison (mac, 4/3/17)
            invocation += [
                "--cpu-bind=cores"
            ]

            invocation += base

    return invocation

def broadcast_executable(executable_path):
    """Broadcast executable to compute nodes for hybrid run.

    Uses module-local `broadcasted_executables` to cache what executables have
    been broadcast previously. Executable names have a hash of the original
    path appended to the executable filename to ensure that executables with
    the same name but different paths don't conflict.

    Arguments:
        executable_path (str): filesystem path for executable to be broadcast

    Returns:
        (str): node-local path where broadcast executable resides
    """
    if executable_path not in broadcasted_executables:
        executable_name = os.path.basename(executable_path)
        executable_hash = hash(executable_path) + sys.maxsize + 1
        local_path = (
            "/tmp/{:s}.{:X}".format(executable_name, executable_hash)
            )
        broadcasted_executables[executable_path] = local_path
        control.call(["sbcast", "--force", "--compress", executable_path, local_path])

    return broadcasted_executables[executable_path]

def hybrid_invocation(base):
    """ Generate subprocess invocation arguments for parallel run.

    Arguments:
        base (list of str): invocation of basic command to be executed

    Returns:
        (list of str): full invocation
    """
    # ensure that we're running inside a compute job
    if not os.environ.get("SLURM_JOB_ID"):
        raise exception.ScriptError("Hybrid mode only supported inside Slurm allocation!")

    # distribute executable to nodes
    executable_path = base[0]
    if (parameters.run.hybrid_nodes >= 128):
        executable_path = broadcast_executable(executable_path)

    # for ompi
    invocation = [
        "srun",
        ## "--cpu-bind=verbose",
        "--nodes={}".format(parameters.run.hybrid_nodes),
        "--ntasks={}".format(parameters.run.hybrid_ranks),
        "--cpus-per-task={}".format(parameters.run.hybrid_threads),
        "--export=ALL"
    ]
    # 4/3/17 (mac): cpu-bind=cores is recommended for cori but degrades performance on edison
    # 7/29/17 (mac): cpu-bind=cores is now recommended for edison as well
    invocation += [
        "--cpu-bind=cores"
    ]

    # use local path instead
    invocation += [executable_path]
    invocation += base[1:]

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

    # attach signal handler for USR1
    signal.signal(signal.SIGUSR1, utils.TaskTimer.handle_exit_signal)

    # set install prefix based on environment
    parameters.run.install_dir = os.path.join(
        parameters.run.install_dir, os.getenv("CRAY_CPU_TARGET")
        )

    # get wall time from Slurm
    if job_id() != "0":
        squeue_output = subprocess.run(
            ["squeue", "-h", "-j", job_id(), "-o", "%L"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True
            ).stdout.strip()
        try:
            squeue_time = list(map(int, squeue_output.replace("-", ":").split(":")))
        except ValueError as err:
            print(err)
            print("Remaining time from squeue: {:s}".format(squeue_output))
            print(
                "Unable to get remaining time from Slurm..."
                "using time given at submission."
            )
        else:
            # squeue drops leading zeros; pad for unpacking
            (days, hours, minutes, seconds) = [0]*(4-len(squeue_time)) + squeue_time
            parameters.run.wall_time_sec = days*86400 + hours*3600 + minutes*60 + seconds

def termination():
    """ Do any local termination tasks.
    """

    pass
