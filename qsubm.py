#!/usr/bin/python3
"""qsubm -- generic queue submission for task-oriented batch scripts

    Environment variables:

    MCSCRIPT_RUN_HOME must specify the directory in which job files are
    found.

    MCSCRIPT_WORK_HOME should specify the parent directory in which
    run scratch directories should be made.

    MCSCRIPT_LAUNCH_HOME (optional) should specify the parent directory
    in which run subdirectories for qsub invocation and output logging
    should be made.  Otherwise, this will default to MCSCRIPT_WORK_HOME.

    MCSCRIPT_RUN_PREFIX should specify the prefix for run names, e.g., "run".

    MCSCRIPT_MODULE_CMD (expected by mcscript) should give the module
    command on the given system, which you can find by asking "where
    module" and looking inside the results.  You may be able to use an
    environment variable rather than a hard-coded version number,
    which is likely to change frequently, e.g.,
    "${MODULESHOME}/bin/modulecmd" is preferable to
    "/opt/modules/3.2.6.6/bin/modulecmd".

    MCSCRIPT_DIR (expected by some config files) should specify the
    directory in which qsubm is installed.

    MCSCRIPT_PYTHON should give the full filename (including path) to the
    appropriate Python executable for running run script files.  This
    is needed for qsubm to do a local run of a script, which involves
    invoking a Python interpreter for it.  A typical value would be
    "python3" if the Python 3 executable is in the path.  However, on
    clusters, this will likely have to point towards a specific Python
    version, loaded with a specific module load.

    Requires local definitions file config.py to translate
    options into arguments for local batch server.  See directions in
    readme.txt.  Your local definitions might not make use of or
    support all the parallel environment options.

    Language: Python 3

    M. A. Caprio
    University of Notre Dame

    + 3/6/13 (mac): Based on earlier qsubm csh script.
    + 7/4/13 (mac): Support for multiple cluster flavors via qsubm_local.
    + 1/22/14 (mac): Python 3 update.
    + 10/27/14 (mac): Updates to --archive handling.
    + 5/14/15 (mac):
        - Insert "future" statements for Python 2 legacy support.
        - Add --noredirect switch.
        - Mandatory environment variable QSUBM_PYTHON.
    + 8/4/15 (mac): Make user environment variable definitions into option.
    + 6/13/16 (mac): Rename environment variables to MCSCRIPT_*.
    + 6/22/16 (mac): Update to use config.py for local configuration.
    + 12/14/16 (mac): Add --here option.
    + 12/29/16 (mac):
        - Add --spread option.
        - Remove --pernode option.
        - Make --opt option repeatable.
    + 1/16/17 (mac): Add --serialthreads option.
    + 2/23/17 (mac): Switch from os.mkdir to mcscript.utils.mkdir.
    + 3/16/17 (mac):
        - Add --setup option.
        - Change environment interface to pass MCSCRIPT_TASK_MODE.
    + 3/18/17 (mac):
        - Revise to support updated hybrid run parameters.
        - Rename option --setup to --prerun.
    + 5/22/17 (mac): Fix processing of boolean option --redirect.
    + 10/11/17 (pjf): Add --switchwaittime option.
"""

import argparse
import os
import shutil
import subprocess
import sys

import mcscript.config  # local configuration (usually symlink)
import mcscript.utils

################################################################
# argument parsing
################################################################

parser = argparse.ArgumentParser(
    description="Queue submission for numbered run.",
    usage=
    "%(prog)s [option] run queue|RUN wall [var1=val1, ...]\n",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    epilog=
    """Simply omit the queue name and leave off the wall time for a
    local interactive run.
    """
    )

# general arguments
parser.add_argument("run", help="Run number (e.g., 0000 for run0000)")
# latter arguments are made optional to simplify bare-bones syntax for --toc, etc., calls
parser.add_argument("queue", nargs='?', help="Submission queue, or RUN for direct interactive run", default="RUN")
parser.add_argument("wall", type=int, nargs='?', help="Wall time (minutes)", default=60)
##parser.add_argument("vars", nargs="?", help="Environment variables to pass to script, with optional values, comma delimited (e.g., METHOD2, PARAM=1.0)")
parser.add_argument("--here", action="store_true", help="Force run in current working directory")
parser.add_argument("--vars", help="Environment variables to pass to script, with optional values, comma delimited (e.g., --vars=METHOD2, PARAM=1.0)")
## parser.add_argument("--stat", action="store_true", help="Display queue status information")
parser.add_argument("--num", type=int, default=1, help="Number of repetitions")
parser.add_argument("--opt", action="append", help="Additional option arguments to be passed to job submission command (e.g., --opt=\"-m ae\" or --opt=\"--mail-type=ALL\"), may be repeated (e.g., --opt=\"-A acct\" --opt=\"-a 1200\"); beware the spaces may be important to the job submission command")

# serial run parallelization parameters
serial_group = parser.add_argument_group("serial run options (single-node, non-MPI)")
serial_group.add_argument("--serialthreads", type=int, default=1, help="OMP threads")

# hybrid run parallelization parameters
#
# Not all local configuration files need necessarily require or
# respect all of the following parameters.
hybrid_group = parser.add_argument_group("hybrid run options")
hybrid_group.add_argument("--nodes", type=int, default=1, help="number of nodes")
hybrid_group.add_argument("--ranks", type=int, default=1, help="number of MPI ranks")
hybrid_group.add_argument("--threads", type=int, default=1, help="OMP threads per rank)")
hybrid_group.add_argument("--nodesize", type=int, default=0, help="logical threads available per node"
                          " (might instead be interpreted physical CPUs depending on local config file)")
hybrid_group.add_argument("--switchwaittime", type=str, default="2:00:00", help="maximum time to wait for switch count")
##hybrid_group.add_argument("--undersubscription", type=int, default=1, help="undersubscription factor (e.g., spread=2 requests twice the cores needed)")

# multi-task interface: invocation modes
task_mode_group = parser.add_mutually_exclusive_group()
task_mode_group.add_argument("--toc", action="store_true", help="Invoke run script to generate task table of contents")
task_mode_group.add_argument("--unlock", action="store_true", help="Delete any .lock or .fail flags for tasks")
task_mode_group.add_argument("--archive", action="store_true", help="Invoke archive-generation run")
task_mode_group.add_argument("--prerun", action="store_true", help="Invoke prerun mode, for argument validation and file staging only")
task_mode_group.add_argument("--offline", action="store_true", help="Invoke offline mode, to create batch scripts for later submission instead of running compute codes")

# multi-task interface: task selection
task_selection_group = parser.add_argument_group("multi-task run")
task_selection_group.add_argument("--pool", help="Set task pool (or ALL) for task selection")
task_selection_group.add_argument("--phase", type=int, default=0, help="Set task phase for task selection")
task_selection_group.add_argument("--start", type=int, help="Set starting task number for task selection")
task_selection_group.add_argument("--limit", type=int, help="Set task count limit for task selection")
task_selection_group.add_argument("--redirect", default="True", choices=["True", "False"], help="Allow redirection of standard"
                    " output/error to file (may want to disable for interactive debugging)")

# some special options (deprecated?)
##parser.add_argument("--epar", type=int, default=None, help="Width for embarassingly parallel job")
##parser.add_argument("--nopar", action="store_true", help="Disable parallel resource requests (for use on special serial queues)")

##parser.print_help()
##print
args = parser.parse_args()
##print args

################################################################
# special mode: status display
################################################################

# TODO
# will have to modify argument processing to allow no arguments, local
# customization for qstat

# @ i = 0
# while (($i == 0) || ($loop))
#    @ i++
#    clear
#    echo "****************************************************************"
#    qstat -u $user
#    if ($loop) sleep 5
# end

## if (args.stat):
##     pass

################################################################
# environment processing
################################################################

if (args.here):
    run_home = os.environ["PWD"]
elif ("MCSCRIPT_RUN_HOME" in os.environ):
    run_home = os.environ["MCSCRIPT_RUN_HOME"]
else:
    print ("MCSCRIPT_RUN_HOME not found in environment")
    exit(1)

if (args.here):
    work_home = os.environ["PWD"]
elif ("MCSCRIPT_WORK_HOME" in os.environ):
    work_home = os.environ["MCSCRIPT_WORK_HOME"]
else:
    print ("MCSCRIPT_WORK_HOME not found in environment")
    exit(1)

if (args.here):
    launch_home = os.environ["PWD"]
elif ("MCSCRIPT_LAUNCH_HOME" in os.environ):
    launch_home = os.environ["MCSCRIPT_LAUNCH_HOME"]
else:
    launch_home = work_home

if ("MCSCRIPT_PYTHON" in os.environ):
    python_executable = os.environ["MCSCRIPT_PYTHON"]
else:
    print ("MCSCRIPT_PYTHON not found in environment")
    exit(1)

if ("MCSCRIPT_DIR" in os.environ):
    qsubm_path = os.environ["MCSCRIPT_DIR"]
else:
    print ("MCSCRIPT_DIR not found in environment")
    exit(1)

################################################################
# argument processing
################################################################

# set run name
run_prefix = os.environ["MCSCRIPT_RUN_PREFIX"]
run = run_prefix + args.run
print ("Run:", run)

# ...and process run file
script_extensions = [".py", ".csh"]
job_file = None
for extension in script_extensions:
    filename = os.path.join(run_home, run+extension)
    if (filename):
        job_file = filename
        job_extension = extension
        break
print ("  Run home:", run_home)  # useful to report now, in case job file missing
if (job_file is None):
    print ("No job file %s.* found with an extension in the set %s." % (run, script_extensions))
    exit(1)
print ("  Job file:", job_file)

# set queue and flag batch or local mode
# force local run for task.py toc mode
if ((args.queue == "RUN") or args.toc or args.unlock):
    run_mode = "local"
    run_queue = None
    print ("  Mode:", run_mode)
else:
    run_mode = "batch"
    print ("  Mode:", run_mode, "(%s)" % args.queue)

# set wall time
wall_time_min = args.wall
print ("  Wall time (min): {:d}".format(wall_time_min))
wall_time_sec = wall_time_min*60

# environment definitions: general run parameters
environment_definitions = [
    "MCSCRIPT_RUN={:s}".format(run),
    "MCSCRIPT_JOB_FILE={:s}".format(job_file),
    "MCSCRIPT_RUN_MODE={:s}".format(run_mode),
    "MCSCRIPT_WALL_SEC={:d}".format(wall_time_sec)
]

# environment definitions: serial run parameters
environment_definitions += [
    "MCSCRIPT_SERIAL_THREADS={:d}".format(args.serialthreads)
]

# environment definitions: hybrid run parameters
environment_definitions += [
    "MCSCRIPT_HYBRID_NODES={:d}".format(args.nodes),
    "MCSCRIPT_HYBRID_RANKS={:d}".format(args.ranks),
    "MCSCRIPT_HYBRID_THREADS={:d}".format(args.threads),
    "MCSCRIPT_HYBRID_NODESIZE={:d}".format(args.nodesize)
]

# set repetition parameter
repetitions = args.num


# set multi-task run parameters
if (args.toc):
    task_mode = mcscript.task.TaskMode.kTOC
elif (args.unlock):
    task_mode = mcscript.task.TaskMode.kUnlock
elif (args.archive):
    task_mode = mcscript.task.TaskMode.kArchive
elif (args.prerun):
    task_mode = mcscript.task.TaskMode.kPrerun
elif (args.offline):
    task_mode = mcscript.task.TaskMode.kOffline
else:
    task_mode = mcscript.task.TaskMode.kRun

# TODO (mac): neaten up so that these arguments are always provided
# (and simplify this code to a simple list += as above)
environment_definitions.append("MCSCRIPT_TASK_MODE={:d}".format(task_mode.value))
if (args.pool is not None):
    environment_definitions.append("MCSCRIPT_TASK_POOL={:s}".format(args.pool))
if (args.phase is not None):
    environment_definitions.append("MCSCRIPT_TASK_PHASE={:d}".format(args.phase))
if (args.start is not None):
    environment_definitions.append("MCSCRIPT_TASK_START_INDEX={:d}".format(args.start))
if (args.limit is not None):
    environment_definitions.append("MCSCRIPT_TASK_COUNT_LIMIT={:d}".format(args.limit))
environment_definitions.append("MCSCRIPT_TASK_REDIRECT={:s}".format(args.redirect))

# include additional environment setup if defined
if os.environ.get("MCSCRIPT_SOURCE"):
    environment_definitions += [
        "MCSCRIPT_SOURCE={:s}".format(os.environ["MCSCRIPT_SOURCE"])
    ]

# set user-specified variable definitions
# Note conditional is required since "".split(", ") is [""] rather than [].
if (args.vars is None):
    user_environment_definitions = []
else:
    user_environment_definitions = args.vars.split(",")
    print("  User environment definitions:", user_environment_definitions)

environment_definitions += user_environment_definitions


################################################################
# directory setup
################################################################

# set up scratch directory (for batch job work)
#   name is defined here, but creation is left up to job script,
#   in case scratch is local to the compute note
work_dir = os.path.join(work_home, run)
## if ( not os.path.exists(work_dir)):
##     mcscript.utils.mkdir(work_dir)
environment_definitions.append("MCSCRIPT_WORK_DIR=%s" % work_dir)

# set up run launch directory (for batch job output logging)
launch_dir_parent = os.path.join(launch_home, run)
if ( not os.path.exists(launch_home)):
    mcscript.utils.mkdir(launch_home)
if ( not os.path.exists(launch_dir_parent)):
    mcscript.utils.mkdir(launch_dir_parent)
if (args.archive):
    # archive mode
    # launch in archive directory rather than usual batch job output directory
    # (important since if batch job server directs output to the
    # regular output directory while tar is archiving that directory,
    # tar will return with an error code, torpedoing the archive task)
    launch_dir = os.path.join(launch_home, run, "archive")
else:
    # standard run mode
    launch_dir = os.path.join(launch_home, run, "batch")
if ( not os.path.exists(launch_dir)):
    mcscript.utils.mkdir(launch_dir)
environment_definitions.append("MCSCRIPT_LAUNCH_DIR=%s" % launch_dir)


################################################################
# job environment setup
################################################################

# construct job name
job_name = "%s" % run
##job_name += "-w%d" % args.width
if (args.pool is not None):
    job_name += "-%s" % args.pool
job_name += "-%s" % args.phase
print ("  Job name:", job_name)

# process environment definitions
# regularize environment definitions
#   Convert all plain variable name definitions "VAR" into definition
#   as null string "VAR=".  Note that "VAR" would be an environment
#   variable pass-through request to qsub, but it causes trouble with
#   defining an environment for local execution.  So doing this
#   regularization simplifies further processing and ensures
#   uniformity of the environment between batch and local runs.
for i in range(len(environment_definitions)):
    if (not "=" in environment_definitions[i]):
        environment_definitions[i] += "="
print ()
print ("Vars:", ",".join(environment_definitions))
# for local run
job_environ=os.environ
environment_keyvalues = [
    entry.split("=")
    for entry in environment_definitions
    ]
job_environ.update(dict(environment_keyvalues))


################################################################
# run invocation
################################################################

# flush script output before invoking job
print ()
sys.stdout.flush()

# handle batch run
if (run_mode == "batch"):

    # set local qsub arguments
    (submission_args, submission_input_string) = mcscript.config.submission(job_name, job_file, qsubm_path, environment_definitions, args)

    # notes: options must come before command on some platforms (e.g., Univa)
    print (" ".join(submission_args))
    print (submission_input_string)
    print ()
    print ("-"*64)
    for i in range(repetitions):
        process = subprocess.Popen(
            submission_args,
            stdin=subprocess.PIPE,     # to take input from communicate
            stdout=subprocess.PIPE,    # to send output to communicate -- default merged stderr
            cwd=launch_dir
            )
        stdout_bytes = process.communicate(input=submission_input_string)[0]
        stdout_string = stdout_bytes.decode("utf-8")
        print (stdout_string)

# handle interactive run
# Note: We call interpreter rather than trying to directly execute
# job file since this saves us from bothering with execute permissions.
# But, beware the interpreter enforced by the script's shebang line might
# be different from the version of the interpreter found in the below invocation,
# especially in a "module" environment.
elif (run_mode == "local"):
    if (extension == ".py"):
        popen_args = [python_executable, job_file]
    elif (extension == ".csh"):
        popen_args = ["csh", job_file]
    print ()
    print ("-"*64)
    process = subprocess.Popen(popen_args, cwd=launch_dir, env=job_environ)
    process.wait()
