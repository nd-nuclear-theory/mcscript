"""config-uge-ndcrc.py

    mcscript definitions for Univa Grid Engine at the Notre Dame CRC

    Language: Python 3

    Mark A. Caprio
    University of Notre Dame

    + 11/22/16 (mac): Created, based on qsubm_local_ndcrc.py and
      mcscript_local_ndcrc.py (originated ~7/13 and last modified
      ~12/14).
    + 4/22/17 (mac):
      - Update use of mcscript configuration variables.
      - Add automatic queue sensing and revise calculation of run size parameters.
      - Try out binding.
    + 07/06/18 (pjf):
      - Pass entire environment.
      - Completely rewrite mapping and binding logic.

"""

# Notes:
#
# Node size is calculated based on queue:
#
#   long/debug: 2x12=24
#   infiniband: 2x4=8
#
# Wall time is not communicated in queue request but is passed on to script.
#
# We currently grab an integer number of nodes.  This doesn't support
# cluster-style sharing of nodes by serial jobs.

# Queues as of 07/02/18:
#
#   http://wiki.crc.nd.edu/wiki/index.php/Available_Hardware
#

#   General Access Compute Clusters
#
#   d12chas351-d12chas387.crc.nd.edu & d12chas400-d12chas531.crc.nd.edu
#
#    169 Lenovo NeXtScale nx360 M5 Servers
#    Dual 12 core Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz Haswell processors
#    256 GB RAM  -  1.4TB Solid State Disk - SSD
#    Usage:  Queue syntax for job submission script:
#       #$ -q long
#       or
#       #$ -q *@@general_access
#
#   d12chas532-d12chas543.crc.nd.edu
#
#    12 Lenovo NeXtScale nx360 M5 Servers
#    Dual 12 core Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz Haswell processors
#    64 GB RAM  -  1.4TB Solid State Disk - SSD
#    Usage:  Queue syntax for job submission script:
#       #$ -q debug
#
#   dqcneh075-104.crc.nd.edu CRC General Access (with Infiniband interconnection network, available upon request)
#
#    30 IBM I-dataplex
#    Dual Quad-core 2.53 GHz Intel Nehalem processors
#    Qlogic QDR Infiniband Non-Blocking  HBA
#    12 GB RAM
#    Usage:  Queue syntax for job submission script:
#       #$ -q *@@dqcneh_253GHZ

import math
import os

from . import parameters


queues = {
    # queue, nodesize, socketsize, numasize
    "local":      ("local", 24, 12, 6),
    "long":       ("*@@general_access", 24, 12, 6),
    "long-48":    ("long", 48, 24, 6),
    "debug":      ("debug", 24, 12, 6),
    "hpc":        ("hpc", 48, 24, 6),
    "hpc-debug":  ("hpc-debug", 48, 24, 6),
    "infiniband": ("*@@dqcneh_253GHZ", 8, 4, 2)
}


################################################################
################################################################
# scripting submission (qsubm)
################################################################
################################################################

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

    # deduce queue properties
    if (args.queue not in queues):
        raise(ValueError("unrecognized queue name"))
    (queue_identifier, nodesize, socketsize, numasize) = queues[args.queue]
    print("Deduced queue properties: "
          "identifier {:s}, "
          "nodesize {:d}, "
          "socketsize {:d}, "
          "numasize {:d}".format(*queues[args.queue])
          )

    # start accumulating command line
    submission_invocation = [ "qsub" ]

    # job name
    submission_invocation += ["-N {}".format(job_name)]

    # queue
    submission_invocation += ["-q {}".format(queue_identifier)]

    # wall time
    pass  # enforced by queue

    # array job for repetitions
    if args.num > 1:
        submission_invocation += ["-t", "{:g}-{:g}".format(1, args.num)]

    # miscellaneous options
    submission_invocation += ["-j", "y"]  # merge standard error
    submission_invocation += ["-r", "n"]  # job not restartable

    # check thread counts -- hyperthreading is disabled at the BIOS-level for
    # all CRC nodes (email to pjf from Paul Brenner, 06/26/18)
    max_threads_per_process = max(args.threads, args.serialthreads)
    if max_threads_per_process > nodesize:
        raise ValueError("More threads requested than available on single node! "
              "Hyperthreading is NOT supported."
              )
    total_threads = args.threads * args.ranks
    total_cores = args.nodes * nodesize
    print("total_threads: {}, total_cores: {}".format(total_threads, total_cores))
    if total_threads > total_cores:
        raise ValueError(
              "More threads requested than available! "
              "Hyperthreading is NOT supported."
             )
    ranks_per_node = nodesize // args.threads
    if ranks_per_node*args.nodes < args.ranks:
        raise ValueError("Insufficient nodes for requested for threads.")

    # generate parallel environment specifier
    submission_invocation += [
        "-pe",
        "mpi-{nodesize:d} {total_cores:d}".format(nodesize=nodesize, total_cores=total_cores)
    ]

    # append user-specified arguments
    if (args.opt is not None):
        submission_invocation += args.opt

    # environment definitions
    submission_invocation += [
        "-V",
    ]

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
    # use array jobs for repetition
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

    return os.environ.get("JOB_ID", "0")


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

    return invocation


def hybrid_invocation(base):
    """ Generate subprocess invocation arguments for parallel run.

    Arguments:
        base (list of str): invocation of basic command to be executed

    Returns:
        (list of str): full invocation
    """

    (queue_identifier, nodesize, socketsize, numasize) = queues[parameters.run.run_queue]
    threads = parameters.run.hybrid_threads
    ranks = parameters.run.hybrid_ranks
    nodes = parameters.run.hybrid_nodes

    # determine thread binding mode
    total_threads = threads * ranks
    total_cores = nodes * nodesize
    print("total_threads: {}, total_cores: {}".format(total_threads, total_cores))

    # minimum number of cores available to each rank
    cores_per_rank = total_cores // ranks
    if threads > cores_per_rank:
        raise ValueError("more threads requested than available: {:d}/{:d}".format(threads, cores_per_rank))

    # number of ranks on each subdivision of allocation
    ranks_per_node = math.ceil(ranks/nodes)
    ranks_per_socket = math.ceil(ranks_per_node / (nodesize // socketsize))
    ranks_per_numa = math.ceil(ranks_per_socket / (socketsize // numasize))

    # distribute among largest possible units, to ensure spread
    # if number of cores available to a rank is larger than a unit (e.g. socket)
    # then allocate at least an integer number of those units to each rank
    if socketsize < cores_per_rank <= nodesize:
        allocated_cores = cores_per_rank - (cores_per_rank % socketsize)
        allocated_cores = max(allocated_cores, threads)
        map_by = "ppr:{:d}:node:PE={:d},SPAN".format(ranks_per_node, allocated_cores)
    elif numasize < cores_per_rank <= socketsize:
        allocated_cores = cores_per_rank - (cores_per_rank % numasize)
        allocated_cores = max(allocated_cores, threads)
        map_by = "ppr:{:d}:socket:PE={:d},SPAN".format(ranks_per_socket, allocated_cores)
    else:  # cores_per_rank <= numasize
        allocated_cores = cores_per_rank
        allocated_cores = max(cores_per_rank, threads)
        map_by = "ppr:{:d}:numa:SPAN,PE={:d}".format(ranks_per_numa, allocated_cores)


    # map_by = "ppr:{:d}:node:PE={:d},SPAN".format(ranks_per_node, allocated_cores)

    rank_by = "node:SPAN"
    bind_to = "core"

    if (not parameters.run.batch_mode):
        # run on front end
        #
        # skip bindings
        invocation = [
            "mpiexec",
            "--n", "{:d}".format(parameters.run.hybrid_ranks),
        ]
    else:
        # run on compute node
        invocation = [
            "mpiexec",
            "--display-allocation",
            "--display-map",
            "--n", "{:d}".format(parameters.run.hybrid_ranks),
            "--map-by", map_by,
            "--rank-by", rank_by,
            "--bind-to", bind_to,
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

    pass

def termination():
    """ Do any local termination tasks.
    """

    pass
