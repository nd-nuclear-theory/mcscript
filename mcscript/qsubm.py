"""qsubm -- generic queue submission for task-oriented batch scripts

    See INSTALL.md for configuration information:

    - A local definitions file config.py must be defined.

    - Several environment variables must be defined.  In addition to the
      mandatory environment variables defined there, the following (deprecated?)
      variables are recognized (but not frequently useful):

      > MCSCRIPT_LAUNCH_HOME (optional) specifies the parent directory in which
      > run subdirectories for qsub invocation and output logging should be made.
      > Otherwise, this will default to MCSCRIPT_WORK_HOME.

      > MCSCRIPT_PYTHON (optional) specifies the command name to use to invoke
      > Python 3 to execut run script files.  The default is simply "python3",
      > assuming the Python 3 executable is in the shell's command search
      > PATH. However, you can instead specify, e.g., a full, qualified filename
      > (i.e., including path).  See note on "Availability of Python" in INSTALL.md.

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
    + 01/05/18 (pjf): Sort arguments into groups.
    + 02/11/18 (pjf):
        - Pass through MCSCRIPT_INSTALL_HOME.
        - Use job_environ for submission.
    + 07/06/18 (pjf):
        - Pass queue via MCSCRIPT_RUN_QUEUE.
        - Remove MCSCRIPT_HYBRID_NODESIZE.
    + 06/04/19 (pjf):
        - Add hook for individual configurations to add command-line arguments.
        - Move --switchwaittime option into config-slurm-nersc.py.
    + 09/11/19 (pjf): Add expert mode argument.
    + 11/18/19 (pjf): Fix job file existence check.
    + 06/26/20 (mac): Make MCSCRIPT_PYTHON and MCSCRIPT_RUN_PREFIX optional.
    + 10/11/20 (pjf):
        - Rename `--num` to `--jobs`.
        - Add `--workers` to allow multiple workers per job.
    + 02/01/22 (pjf): Allow MCSCRIPT_RUN_HOME to be a colon-delimited list.
    + 02/08/22 (pjf):
        - Fix script extension selection.
        - Switch from subprocess.Popen to subprocess.run.
    + 07/02/22 (pjf):
        - Force run_prefix="run".
        - Warn if MCSCRIPT_RUN_PREFIX still defined.
    + 07/14/22 (pjf):
        - Add `--edit` mode.
        - Update xterm title when running directly.
    + 09/20/22 (pjf): Use os.exec instead of subprocess for local run_mode.
    + 07/28/23 (mac/slv): Simplify argument handling for local runs (replace "RUN" with None as default queue).
    + 09/10/23 (mac): Provide diagnostic environment variables MCSCRIPT_QSUBM_INVOCATION
        and MCSCRIPT_SUBMISSION_INVOCATION.
    + 11/10/23 (pjf): Populate selected values in parameters.run for use by
        config.submission().
    + 01/19/24 (pjf):
        - Ensure `MCSCRIPT_PYTHON` is always set.
        - Add quiet mode.
        - Cosmetic improvements to argument handling.
"""

import argparse
import os
import shutil
import subprocess
import sys
import types

from . import (
    config,
    parameters,
    task,
    utils,
)

def get_user_config():
    """Get user configuration from environment."""
    user_config = types.SimpleNamespace()

    user_config.install_home = utils.expand_path(os.environ.get("MCSCRIPT_INSTALL_HOME"))
    user_config.run_home_list = utils.expand_path(os.environ.get("MCSCRIPT_RUN_HOME", ".").split(":"))
    user_config.work_home = utils.expand_path(os.environ.get("MCSCRIPT_WORK_HOME"))

    # optional fields
    user_config.launch_home = utils.expand_path(os.environ.get("MCSCRIPT_LAUNCH_HOME"))
    user_config.python_executable = utils.expand_path(os.environ.get("MCSCRIPT_PYTHON"))
    user_config.env_script = utils.expand_path(os.environ.get("MCSCRIPT_SOURCE"))
    user_config.run_prefix = "run"

    return user_config


def parse_args():
    """Parse arguments.

    Returns:
        (argparse.Namespace) parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Set up execution environment for run script and submit to batch system (or launch local interactive execution).",
        usage="%(prog)s [option] run [queue] [wall] [var1=val1, ...]\n",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog=
        """For a local (interactive) run, simply omit the queue name
        (and wall time) arguments.

        Environment variables for qsubm are described in INSTALL.md.

        Note that qsubm relies upon code in the local `config.py`
        configuration file for the system or cluster you are running on, in
        order to interpret the following arguments and translate them into
        arguments for your local batch system.  Your local configuration
        file might not make use of or support all the parallel environment
        options listed below.
        """
        )

    # general arguments
    parser.add_argument("run", help="Run number (e.g., 0000 for run0000)")

    # latter arguments are made optional to simplify bare-bones syntax for --toc, etc., calls
    parser.add_argument("queue", nargs='?', help="Submission queue (or omit for local interactive run)", default=None)
    parser.add_argument("wall", type=int, nargs='?', help="Wall time (minutes)", default=60)
    ##parser.add_argument("vars", nargs="?", help="Environment variables to pass to script, with optional values, comma delimited (e.g., METHOD2, PARAM=1.0)")
    parser.add_argument("--here", action="store_true", help="Force run in current working directory")
    parser.add_argument("--vars", help="Environment variables to pass to script, with optional values, comma delimited (e.g., --vars=METHOD2, PARAM=1.0)")
    ## parser.add_argument("--stat", action="store_true", help="Display queue status information")
    parser.add_argument("--jobs", type=int, default=1, help="Number of (identical) jobs to submit")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers to launch per job (not supported by all queues)")
    parser.add_argument("--opt", action="append", help="Additional option arguments to be passed to job submission command (e.g., --opt=\"-m ae\" or --opt=\"--mail-type=END,FAIL\"), may be repeated (e.g., --opt=\"-A acct\" --opt=\"-a 1200\"); beware the spaces may be important to the job submission command")
    parser.add_argument("--expert", action="store_true", help="Run mcscript in expert mode")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress qsubm output text")

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
                            " (might instead be interpreted as physical CPUs depending on local config file)")
    ##hybrid_group.add_argument("--undersubscription", type=int, default=1, help="undersubscription factor (e.g., spread=2 requests twice the cores needed)")

    # multi-task interface: invocation modes
    task_mode_group = parser.add_argument_group("run modes").add_mutually_exclusive_group()
    task_mode_group.add_argument("--edit", action="store_true", help="Edit run script using EDITOR")
    task_mode_group.add_argument("--toc", action="store_true", help="Invoke run script to generate task table of contents")
    task_mode_group.add_argument("--unlock", action="store_true", help="Delete any .lock or .fail flags for tasks")
    task_mode_group.add_argument("--archive", action="store_true", help="Invoke archive-generation run")
    task_mode_group.add_argument("--prerun", action="store_true", help="Invoke prerun mode, for argument validation and file staging only")
    task_mode_group.add_argument("--offline", action="store_true", help="Invoke offline mode, to create batch scripts for later submission instead of running compute codes")

    # multi-task interface: task selection
    task_selection_group = parser.add_argument_group("multi-task run options")
    task_selection_group.add_argument("--pool", help="Set task pool (may be Unix-style filename pattern, or comma-delimited list, or ALL) for task selection")
    task_selection_group.add_argument("--phase", type=int, default=0, help="Set task phase for task selection")
    task_selection_group.add_argument("--start", type=int, default=0, help="Set starting task number for task selection")
    task_selection_group.add_argument("--limit", type=int, help="Set task count limit for task selection")
    task_selection_group.add_argument("--redirect", default=True, action=argparse.BooleanOptionalAction, help="Redirect standard"
                        " output/error to file (may want to disable for interactive debugging)")

    # site-local options
    try:
        config.qsubm_arguments(parser)
    except AttributeError:
        # local config doesn't provide arguments, ignore gracefully
        pass

    return parser.parse_args()

def main():
    """Run qsubm command-line utility."""

    args = parse_args()
    user_config = get_user_config()

    ################################################################
    # environment processing
    ################################################################

    if args.here:
        user_config.run_home_list = [os.environ["PWD"]]
        user_config.work_home = os.environ["PWD"]
        user_config.launch_home = os.environ["PWD"]

    if not user_config.run_home_list:
        print("MCSCRIPT_RUN_HOME not found in environment")
        exit(1)

    if not user_config.work_home:
        print("MCSCRIPT_WORK_HOME not found in environment")
        exit(1)

    if not user_config.launch_home:
        user_config.launch_home = user_config.work_home

    if not user_config.python_executable:
        user_config.python_executable = "python3"

    if not user_config.install_home:
        print("MCSCRIPT_INSTALL_HOME not found in environment")
        exit(1)

    ################################################################
    # argument processing
    ################################################################

    # quiet modes
    if args.edit:
        args.quiet = True

    # set run name
    run = user_config.run_prefix + args.run
    if not args.quiet:
        print("Run:", run)

    # ...and process run file
    script_extensions = [".py", ".csh"]
    job_file = None
    for extension in script_extensions:
        for run_home in user_config.run_home_list:
            filename = os.path.join(run_home, run+extension)
            if os.path.exists(filename):
                job_file = filename
                job_extension = extension
                break
    if not args.quiet:
        print("  Run homes:", user_config.run_home_list)  # useful to report now, in case job file missing
    if (job_file is None):
        print(f"No job file {run}.* found with an extension in the set {script_extensions}.")
        exit(1)
    if not args.quiet:
        print("  Job file:", job_file)

    # set queue and flag batch or local mode
    # force local run for task.py toc mode
    if ((args.queue is None) or args.toc or args.unlock):
        run_mode = "local"
    else:
        run_mode = "batch"
    if not args.quiet:
        print("  Mode: {:s}  (Queue: {:s})".format(run_mode,str(args.queue)))

    # set wall time
    wall_time_min = args.wall
    if not args.quiet:
        print("  Wall time (min): {:d}".format(wall_time_min))
    wall_time_sec = wall_time_min*60

    # environment definitions: general run parameters
    environment_definitions = [
        "MCSCRIPT_RUN={:s}".format(run),
        "MCSCRIPT_JOB_FILE={:s}".format(job_file),
        "MCSCRIPT_RUN_MODE={:s}".format(run_mode),
        "MCSCRIPT_RUN_QUEUE={:s}".format(str(args.queue)),
        "MCSCRIPT_WALL_SEC={:d}".format(wall_time_sec),
        "MCSCRIPT_WORKERS={:d}".format(args.workers),
    ]
    parameters.run.name = run
    parameters.run.job_file = job_file
    parameters.run.run_queue = str(args.queue)

    # environment definitions: serial run parameters
    environment_definitions += [
        "MCSCRIPT_SERIAL_THREADS={:d}".format(args.serialthreads)
    ]

    # environment definitions: hybrid run parameters
    environment_definitions += [
        "MCSCRIPT_HYBRID_NODES={:d}".format(args.nodes),
        "MCSCRIPT_HYBRID_RANKS={:d}".format(args.ranks),
        "MCSCRIPT_HYBRID_THREADS={:d}".format(args.threads),
    ]


    # set multi-task run parameters
    if (args.edit):
        editor = os.environ.get("EDITOR", "vi")
        os.execlp(editor, editor, job_file)
    elif (args.toc):
        task_mode = task.TaskMode.kTOC
    elif (args.unlock):
        task_mode = task.TaskMode.kUnlock
    elif (args.archive):
        task_mode = task.TaskMode.kArchive
    elif (args.prerun):
        task_mode = task.TaskMode.kPrerun
    elif (args.offline):
        task_mode = task.TaskMode.kOffline
    else:
        task_mode = task.TaskMode.kRun

    # environment definitions: multi-task run parameters
    environment_definitions += [
        f"MCSCRIPT_TASK_MODE={task_mode.value:d}",
        f"MCSCRIPT_TASK_PHASE={args.phase:d}",
        f"MCSCRIPT_TASK_START_INDEX={args.start:d}",
        f"MCSCRIPT_TASK_REDIRECT={args.redirect}",
    ]
    # TODO (mac): neaten up so that these arguments are always provided
    # (and simplify this code to a simple list += as above)
    if (args.pool is not None):
        environment_definitions.append(f"MCSCRIPT_TASK_POOL={args.pool:s}")
    if (args.limit is not None):
        environment_definitions.append(f"MCSCRIPT_TASK_COUNT_LIMIT={args.limit:d}")

    # environment definitions: pass through install directory
    environment_definitions += [
        f"MCSCRIPT_INSTALL_HOME={user_config.install_home:s}"
    ]

    # environment definitions: set MCSCRIPT_PYTHON
    environment_definitions += [
        f"MCSCRIPT_PYTHON={user_config.python_executable:s}"
    ]

    # include additional environment setup if defined
    if user_config.env_script:
        environment_definitions += [
            f"MCSCRIPT_SOURCE={user_config.env_script:s}"
        ]

    # set user-specified variable definitions
    # Note conditional is required since "".split(", ") is [""] rather than [].
    if (args.vars is None):
        user_environment_definitions = []
    else:
        user_environment_definitions = args.vars.split(",")
        if not args.quiet:
            print("  User environment definitions:", user_environment_definitions)

    environment_definitions += user_environment_definitions


    ################################################################
    # directory setup
    ################################################################

    # set up scratch directory (for batch job work)
    #   name is defined here, but creation is left up to job script,
    #   in case scratch is local to the compute note
    work_dir = os.path.join(user_config.work_home, run)
    ## if ( not os.path.exists(work_dir)):
    ##     utils.mkdir(work_dir)
    environment_definitions.append(f"MCSCRIPT_WORK_DIR={work_dir}")
    parameters.run.work_dir = work_dir

    # set up run launch directory (for batch job output logging)
    launch_dir_parent = os.path.join(user_config.launch_home, run)
    if not os.path.exists(user_config.launch_home):
        utils.mkdir(user_config.launch_home)
    if not os.path.exists(launch_dir_parent):
        utils.mkdir(launch_dir_parent)
    if args.archive:
        # archive mode
        # launch in archive directory rather than usual batch job output directory
        # (important since if batch job server directs output to the
        # regular output directory while tar is archiving that directory,
        # tar will return with an error code, torpedoing the archive task)
        launch_dir = os.path.join(user_config.launch_home, run, "archive")
    else:
        # standard run mode
        launch_dir = os.path.join(user_config.launch_home, run, "batch")
    if not os.path.exists(launch_dir):
        utils.mkdir(launch_dir)
    environment_definitions.append(f"MCSCRIPT_LAUNCH_DIR={launch_dir}")
    parameters.run.launch_dir = launch_dir


    ################################################################
    # job environment setup
    ################################################################

    # construct job name
    job_name = f"{run:s}"
    ##job_name += "-w%d" % args.width
    if args.pool is not None:
        job_name += f"-{args.pool:s}"
    job_name += f"-{args.phase:d}"
    if not args.quiet:
        print("  Job name:", job_name)

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
    if not args.quiet:
        print()
        print("Vars:", ",".join(environment_definitions))
    # for local run
    job_environ=os.environ
    environment_keyvalues = [
        tuple(entry.split("=", maxsplit=1))  # maxsplit is to support values which themselves contain an equals sign
        for entry in environment_definitions
        ]
    job_environ.update(dict(environment_keyvalues))


    ################################################################
    # run invocation
    ################################################################

    # flush script output before invoking job
    if not args.quiet:
        print()
        sys.stdout.flush()

    # quiet environment definitions: diagnostic
    os.environ["MCSCRIPT_QSUBM_INVOCATION"] = "{}".format(sys.argv)

    # handle batch run
    if (run_mode == "batch"):

        # set local qsub arguments
        (submission_args, submission_input_string, repetitions) = config.submission(job_name, job_file, environment_definitions, args)

        os.environ["MCSCRIPT_SUBMISSION_INVOCATION"] = "{}".format(submission_args)

        # notes: options must come before command on some platforms (e.g., Univa)
        if not args.quiet:
            print(" ".join(submission_args))
            print(submission_input_string)
            print()
            print("-"*64)
        for i in range(repetitions):
            subprocess.run(
                submission_args,
                input=submission_input_string,
                stdout=sys.stdout,
                stderr=subprocess.STDOUT,  #  to redirect via stdout
                env=job_environ,
                cwd=launch_dir
                )

    # handle interactive run
    # Note: We call interpreter rather than trying to directly execute
    # job file since this saves us from bothering with execute permissions.
    # But, beware the interpreter enforced by the script's shebang line might
    # be different from the version of the interpreter found in the below invocation,
    # especially in a "module" environment.
    elif (run_mode == "local"):
        if (job_extension == ".py"):
            popen_args = [user_config.python_executable, job_file]
        elif (job_extension == ".csh"):
            popen_args = ["csh", job_file]
        if not args.quiet:
            print()
            print("-"*64)
        if task_mode is task.TaskMode.kRun:
            if not args.quiet:
                print(f"\033]2;qsubm {run}\007")
        os.chdir(launch_dir)
        os.environ["MCSCRIPT_SUBMISSION_INVOCATION"] = "{}".format(popen_args)
        os.execvpe(popen_args[0], popen_args, env=job_environ)
