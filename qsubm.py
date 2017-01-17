#!/usr/bin/python3
"""qsubm -- generic queue submission for task-oriented batch scripts

See readme.txt for setup instructions and further documentation.

----------------------------------------------------------------

Debugging:

The Popen argument syntax is tricky.  On hopper, through early June
2013, arguments of form "-q qeueue" worked just fine.  As of June 24,
these are treated as atomic arguments and not properly parsed.  Instead
must break up as ["-q", "queue"].


----------------------------------------------------------------

  Created by M. A. Caprio, University of Notre Dame.
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
  
"""

import sys
import os
import argparse
import subprocess
import shutil

import config  # local configuration (usually symlink)

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

    Environment variables:

    MCSCRIPT_RUN_HOME must specify the directory in which job files are
    found.

    MCSCRIPT_WORK_HOME should specify the parent directory in which
    run scratch directories should be made.

    MCSCRIPT_LAUNCH_HOME (optional) should specify the parent directory
    in which run subdirectories for qsub invocation and output logging
    should be made.  Otherwise, this will default to MCSCRIPT_WORK_HOME.

    MCSCRIPT_RUN_PREFIX should specify the prefix for run names, e.g.,"run".

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

    """
    )

parser.add_argument("run",help="Run number (e.g., 0000 for run0000)")
# latter arguments are made optional to simplify bare-bones syntax for --toc, etc., calls
parser.add_argument("queue",nargs='?',help="Submission queue, or RUN for direct interactive run",default="RUN")  
parser.add_argument("wall",type=int,nargs='?',help="Wall time (minutes)",default=60)
##parser.add_argument("vars",nargs="?",help="Environment variables to pass to script, with optional values, comma delimited (e.g., METHOD2,PARAM=1.0)")
parser.add_argument("--here",action="store_true",help="Force run in current working directory")
parser.add_argument("--vars",help="Environment variables to pass to script, with optional values, comma delimited (e.g., --vars=METHOD2,PARAM=1.0)")
## parser.add_argument("--stat",action="store_true",help="Display queue status information") 
parser.add_argument("--width",type=int,default=1,help="MPI width (number of processes) on hybrid parallel run")
parser.add_argument("--depth",type=int,default=1,help="OMP depth (threads per process) on hybrid parallel run")
parser.add_argument("--serialthreads",type=int,default=1,help="OMP threads for nominally serial (non-MPI) run")
parser.add_argument("--spread",type=int,default=1,help="Undersubscription factor (e.g., spread=2 requests twice the cores needed)")
parser.add_argument("--nodesize",type=int,default=None,help="Physical cores per node")
## parser.add_argument("--pernode",type=int,default=None,help="MPI processes per node (may be superfluous if nodesize specified)")
parser.add_argument("--epar",type=int,default=None,help="Width for embarassingly parallel job")
parser.add_argument("--nopar",action="store_true",help="Disable parallel resource requests (for use on special serial queues)")
parser.add_argument("--num",type=int,default=1,help="Number of repetitions")
parser.add_argument("--opt",action="append",help="Additional option arguments to be passed to job submission command (e.g., --opt=\"-m ae\"), may be repeated (e.g., --opt=\"-A acct\" --opt=\"-a 1200\"); beware the spaces may be important to the job submission command")
parser.add_argument("--toc",action="store_true",help="Task table-of-contents request for task.py interface")
parser.add_argument("--pool",help="Task pool for task.py interface")
parser.add_argument("--phase",type=int,default=0,help="Task phase for task.py interface")
parser.add_argument("--start",type=int,help="Starting task number for task.py interface")
parser.add_argument("--limit",type=int,help="Task iteration limit for task.py interface")
parser.add_argument("--noredirect",action="store_true",help="Disable redirection of standard output/error to file for task.py interface")
parser.add_argument("--unlock",action="store_true",help="Task unlock request for task.py interface")
parser.add_argument("--archive",action="store_true",help="Task archive request for task.py interface")

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

# initialize accumulation lists
environment_definitions = []  # environment variable definitions

# set run name
run_prefix = os.environ["MCSCRIPT_RUN_PREFIX"]
run = run_prefix + args.run
print ("Run:", run)
environment_definitions.append("MCSCRIPT_RUN=%s" % run)

# ...and process run file
script_extensions = [".py", ".csh"]
job_file = None
for extension in script_extensions:
    filename = os.path.join(run_home,run+extension)
    if (filename):
        job_file = filename
        job_extension = extension
        break
print ("  Run home:", run_home)  # useful to report now, in case job file missing
if (job_file is None):
    print ("No job file %s.* found with an extension in the set %s." % (run, script_extensions))
    exit(1)
print ("  Job file:", job_file)
environment_definitions.append("MCSCRIPT_JOB_FILE=%s" % job_file )

# set queue and flag batch or local mode
# force local run for task.py toc mode
if ((args.queue == "RUN") or args.toc or args.unlock):
    run_mode = "local"
    run_queue = None
    print ("  Mode:", run_mode)
else:
    run_mode = "batch"
    print ("  Mode:", run_mode, "(%s)" % args.queue)
environment_definitions.append("MCSCRIPT_RUN_MODE=%s" % run_mode)

# set wall time
wall_time_min = args.wall
print ("  Wall time (min):", wall_time_min)
environment_definitions.append("MCSCRIPT_WALL_SEC=%d" % (wall_time_min*60))

# record width and depth parameters
environment_definitions.append("MCSCRIPT_WIDTH=%d" % args.width)
environment_definitions.append("MCSCRIPT_DEPTH=%d" % args.depth)
environment_definitions.append("MCSCRIPT_SERIALTHREADS=%d" % args.serialthreads)
environment_definitions.append("MCSCRIPT_SPREAD=%d" % args.spread)
if ( (args.depth != 1) and (args.nodesize is None)):
    print ("OMP --depth specified without a --nodesize")
    exit(1)
## if (args.pernode is not None):
##     environment_definitions.append("MCSCRIPT_PERNODE=%d" % args.pernode)
## else:
##     environment_definitions.append("MCSCRIPT_PERNODE=%d" % -1)
if (args.nodesize is not None):
    environment_definitions.append("MCSCRIPT_NODESIZE=%d" % args.nodesize)
else:
    environment_definitions.append("MCSCRIPT_NODESIZE=%d" % -1)
if (args.epar is not None):
    environment_definitions.append("MCSCRIPT_EPAR=%d" % args.epar)
else:
    environment_definitions.append("MCSCRIPT_EPAR=%d" % -1)

# set repetition parameter
repetitions = args.num

# process task options
if (args.toc):
    environment_definitions.append("MCSCRIPT_TASK_TOC")
if (args.noredirect):
    environment_definitions.append("MCSCRIPT_TASK_NOREDIRECT")
if (args.unlock):
    environment_definitions.append("MCSCRIPT_TASK_UNLOCK")
if (args.archive):
    # archive mode
    environment_definitions.append("MCSCRIPT_TASK_POOL=ARCH")
else:
    # standard run mode
    if (args.pool is not None):
        environment_definitions.append("MCSCRIPT_TASK_POOL=%s" % args.pool)
if (args.phase is not None):
    environment_definitions.append("MCSCRIPT_TASK_PHASE=%s" % args.phase)
if (args.start is not None):
    environment_definitions.append("MCSCRIPT_TASK_START=%d" % args.start)
if (args.limit is not None):
    environment_definitions.append("MCSCRIPT_TASK_COUNT_LIMIT=%d" % args.limit)



# set user-specified variable definitions
# Note conditional is required since "".split(",") is [""] rather than [].
if (args.vars is None):
    user_environment_definitions = []
else:
    user_environment_definitions = args.vars.split(",")
    print("  User environment definitions:",user_environment_definitions)

environment_definitions += user_environment_definitions


################################################################
# directory setup
################################################################

# set up scratch directory (for batch job work)
#   name is defined here, but creation is left up to job script,
#   in case scratch is local to the compute note
work_dir = os.path.join(work_home,run)
## if ( not os.path.exists(work_dir)):
##     os.mkdir(work_dir)
environment_definitions.append("MCSCRIPT_WORK_DIR=%s" % work_dir)

# set up run launch directory (for batch job output logging)
launch_dir_parent = os.path.join(launch_home,run)
if ( not os.path.exists(launch_home)):
    os.mkdir(launch_home)
if ( not os.path.exists(launch_dir_parent)):
    os.mkdir(launch_dir_parent)
if (args.archive):
    # archive mode
    # launch in archive directory rather than usual batch job output directory
    # (important since if batch job server directs output to the
    # regular output directory while tar is archiving that directory,
    # tar will return with an error code, torpedoing the archive task)
    launch_dir = os.path.join(launch_home,run,"archive")
else:
    # standard run mode
    launch_dir = os.path.join(launch_home,run,"batch")
if ( not os.path.exists(launch_dir)):
    os.mkdir(launch_dir)
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
    (submission_args, submission_input_string) = config.submission(job_name,job_file,qsubm_path,environment_definitions,args)
    
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
        popen_args = [python_executable,job_file]
    elif (extension == ".csh"):
        popen_args = ["csh",job_file]
    print ()
    print ("-"*64)
    process = subprocess.Popen(popen_args,cwd=launch_dir,env=job_environ)
    process.wait()

