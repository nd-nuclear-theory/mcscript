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

"""

# Notes:
#
# Node size is calculated based on queue:
#
#   We currently ignore hyperthreading?
#
#   long/debug: 2x12=24
#   infiniband: 2x4=8
#
# Wall time is not communicated in queue request but is passed on to script.
#
# Note: Currently only support mpi environment, not smp environment.
#
# We currently grab an integer number of nodes.  This doesn't support
# cluster-style sharing of nodes by serial jobs.

# Queues as of 4/22/17:
#
#   http://wiki.crc.nd.edu/wiki/index.php/Available_Hardware
#
#   General Access Compute Clusters
#
#   d12chas332-d12chas519.crc.nd.edu
#
#    176 Dell PowerEdge R730 Servers
#    Dual 12 core Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz Haswell processors
#    256 GB RAM  -  1.4TB Solid State Disk - SSD
#    Usage:  Queue syntax for job submission script:
#       #$ -q long
#       or
#       #$ -q *@@general_access
#
#   d12chas520-d12chas543.crc.nd.edu
#
#    24 Dell PowerEdge R730 Servers
#    Dual 12 core Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz Haswell processors
#    64 GB RAM  -  1.4TB Solid State Disk - SSD
#    Usage:  Queue syntax for job submission script:
#       #$ -q debug
#
#
#   dqcneh075-104.crc.nd.edu CRC General Access (with Infiniband interconnection network, available upon request)
#
#   30 IBM I-dataplex
#   Dual Quad-core 2.53 GHz Intel Nehalem processors
#   Qlogic QDR Infiniband Non-Blocking  HBA
#   12 GB RAM
#   Usage:  Queue syntax for job submission script:
#       #$ -q *@@dqcneh_253GHZ




import os
import sys

from . import parameters


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

    # deduce queue properties
    queues = {
        "long" : ("*@@general_access",24),
        "debug" : ("debug",24),
        "infiniband" : ("*@@dqcneh_253GHZ",8)
    }
    if (args.queue not in queues):
        raise(ValueError("unrecognized queue name"))
    (queue_identifier,nodesize) = queues[args.queue]
    print("Deduced queue properties: identifier {}, nodesize {}".format(queue_identifier,nodesize))
    environment_definitions.append("MCSCRIPT_HYBRID_NODESIZE={:d}".format(nodesize))

    # start accumulating command line
    submission_invocation = [ "qsub" ]

    # job name
    submission_invocation += ["-N {}".format(job_name)]

    # queue
    submission_invocation += ["-q {}".format(queue_identifier)]

    # wall time
    pass  # enforced by queue

    # miscellaneous options
    submission_invocation += ["-j","y"]  # merge standard error
    submission_invocation += ["-r","n"]  # job not restartable

    # generate parallel environment specifier
    needed_cores = args.ranks * args.threads
    rounded_cores = nodesize * (needed_cores // nodesize)
    if ((needed_cores % nodesize) != 0):
        rounded_cores += nodesize

    # generate parallel environment specifier
    submission_invocation += [
        "-pe",
        "mpi-{nodesize:d} {rounded_cores:d}".format(nodesize=nodesize,rounded_cores=rounded_cores)
    ]

    # append user-specified arguments
    if (args.opt is not None):
        submission_invocation += args.opt

    # environment definitions
    submission_invocation += [
        "-v",
        ",".join(environment_definitions)
    ]

    # wrapper call
    #
    # calls interpreter explicitly, so do not have to rely upon default python
    #   version or shebang line in script
    submission_invocation += [
        os.path.join(qsubm_path,"csh_job_wrapper.csh"),
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
    #
    # https://www.mail-archive.com/users@lists.open-mpi.org/msg28276.html
    #
    # Ex: ppr:2:socket:pe=7
    #   "processes per resource" -- resource=socket, processes=2
    #   "processing elements" -- threads=7

    # Why does this fail?
    #
    #   "--map-by","ppr:{:d}:node:PE={:d}:NOOVERSUBSCRIBE".format(processes_per_resource,processing_elements_per_rank)

    #
    # An invalid value was given for the number of processes
    # per resource (ppr) to be mapped on each node:
    #
    #   PPR:  6:node:pe=4
    #
    # The specification must be a comma-separated list containing
    # combinations of number, followed by a colon, followed
    # by the resource type. For example, a value of "1:socket" indicates that
    # one process is to be mapped onto each socket. Values are supported
    # for hwthread, core, L1-3 caches, socket, numa, and node. Note that
    # enough characters must be provided to clearly specify the desired
    # resource (e.g., "nu" for "numa").

    # Works but bad mapping, since ignores proper spacing and binding...
    #             "--map-by","ppr:{:d}:node:NOOVERSUBSCRIBE".format(processes_per_resource)

    # This may work, but gets warning message on one node and untested on multiple nodes...
    #
    #   WARNING: a request was made to bind a process. While the system
    #   supports binding the process itself, at least one node does NOT
    #   support binding memory to the process location.

    #             "--map-by","node:PE={:d}:NOOVERSUBSCRIBE".format(processes_per_resource)

    # 6/3/17 (mac): using binding on compute nodes causes mess for SU3RME, so disable...

    #   ----------------------------------------------------------------
    #   Setting OMP_NUM_THREADS to 1.
    #   WARNING: NDCRC mpiexec binding is not yet set up properly for more than one thread per process!!!
    #   ----------------------------------------------------------------
    #   Executing external code
    #   Command line: ['mpiexec', '--report-bindings', '--n', '1', '--map-by', 'node:PE=24:NOOVERSUBSCRIBE', '/afs/crc.nd.edu/user/m/mcaprio/code/lsu3shell/programs/tools/SU3RME_MP
    #   I', 'model_space.dat', 'model_space.dat', 'relative_operators.dat']
    #   Call mode: CallMode.kHybrid
    #   Start time: Sat Jun  3 22:45:19 2017
    #   ----------------
    #   Standard output:
    #   --------------------------------------------------------------------------
    #   WARNING: a request was made to bind a process. While the system
    #   supports binding the process itself, at least one node does NOT
    #   support binding memory to the process location.
    #
    #     Node:  d12chas417
    #
    #   Open MPI uses the "hwloc" library to perform process and memory
    #   binding. This error message means that hwloc has indicated that
    #   processor binding support is not available on this machine.
    #
    #   On OS X, processor and memory binding is not available at all (i.e.,
    #   the OS does not expose this functionality).
    #
    #   On Linux, lack of the functionality can mean that you are on a
    #   platform where processor and memory affinity is not supported in Linux
    #   itself, or that hwloc was built without NUMA and/or processor affinity
    #   support. When building hwloc (which, depending on your Open MPI
    #   installation, may be embedded in Open MPI itself), it is important to
    #   have the libnuma header and library files available. Different linux
    #   distributions package these files under different names; look for
    #   packages with the word "numa" in them. You may also need a developer
    #   version of the package (e.g., with "dev" or "devel" in the name) to
    #   obtain the relevant header files.
    #
    #   If you are getting this message on a non-OS X, non-Linux platform,
    #   then hwloc does not support processor / memory affinity on this
    #   platform. If the OS/platform does actually support processor / memory
    #   affinity, then you should contact the hwloc maintainers:
    #   https://github.com/open-mpi/hwloc.
    #
    #   This is a warning only; your job will continue, though performance may
    #   be degraded.
    #   --------------------------------------------------------------------------
    #   --------------------------------------------------------------------------
    #   MPI_ABORT was invoked on rank 0 in communicator MPI_COMM_WORLD
    #   with errorcode 1.
    #
    #   NOTE: invoking MPI_ABORT causes Open MPI to kill all MPI processes.
    #   You may or may not see output from other processes, depending on
    #   exactly when Open MPI kills them.
    #   --------------------------------------------------------------------------
    #
    #   ----------------
    #   Standard error:
    #   [d12chas417.crc.nd.edu:07260] MCW rank 0 is not bound (or bound to all available processors)
    #   Master-slave program requires at least 2 MPI processes!


    # TODO:
    #   - redo binding by socket (default)
    #   - fix PE thread spacing
    #   - consider hyperthreading?

    undersubscription_factor = 1
    processing_elements_per_rank = parameters.run.hybrid_threads*undersubscription_factor
    processes_per_resource = parameters.run.hybrid_nodesize // processing_elements_per_rank

    if (processes_per_resource > 1):
        print("WARNING: NDCRC mpiexec binding is not yet set up properly for more than one thread per process!!!")

    if (not parameters.run.batch_mode):
        # run on front end
        #
        # skip bindings
        invocation = [
            "mpiexec",
            "--n","{:d}".format(parameters.run.hybrid_ranks),
        ]
    else:
        # run on compute node
        invocation = [
            "mpiexec",
            ## "--report-bindings",
            "--n","{:d}".format(parameters.run.hybrid_ranks),
            ## "--map-by","node:PE={:d}:NOOVERSUBSCRIBE".format(processes_per_resource)
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
