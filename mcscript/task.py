"""mcscript_task -- task control utility functions

    Meant to be loaded as part of mcscript.  Provides the
    mcscript.task.* definitions in mcscript.

    Globals: requires attributes of mcscript.run to be populated

    Language: Python 3

    M. A. Caprio
    University of Notre Dame

    + 03/02/13 (mac): Originated as task.py.
    + 05/28/13 (mac): Updated to recognize ScriptError exception.
    + 06/05/13 (mac): Absorbed into mcscript package.
    + 11/01/13 (mac): Add local archive dir in scratch to help circumvent home space overruns.
    + 01/22/14 (mac): Python 3 update.
    + 07/03/14 (mac): Add generic archiving support.
    + 05/14/15 (mac): Insert "future" statements and convert print to write
          for Python 2 legacy support.  Upgrade string formatting to
          Python 2.7 format method.
    + 06/04/15 (mac): Add check for locking clashes.
    + 06/25/15 (mac): Simplify task interface to single init() function.
    + 06/13/16 (mac): Rename environment variables TASK_* to MCSCRIPT_TASK_*. Restructure subpackages.
    + 01/18/17 (mac):
          - Update archive handler.
          - Rename optional argument archive_handler_list to archive_phase_handler_list.
    + 01/21/17 (mac): Fix spurious argument on archive_handler_hsi.
    + 02/23/17 (mac): Switch from os.mkdir to mcscript.utils.mkdir.
    + 03/16/17 (mac):
        - Restructure to avoid most global variables.
        - Upgrade docstrings.
        - Change environment interface to expect MCSCRIPT_TASK_MODE.
        - Allow for "setup" task mode.
        - Define task "metadata" field.
    + 03/18/17 (mac):
        - Define task modes as enum.
        - Rename "setup" mode to "prerun".
    + 05/22/17 (mac): Fix processing of boolean option MCSCRIPT_TASK_REDIRECT.
    + 06/28/17 (mac): Add archive handler archive_handler_no_results.
    + 06/29/17 (pjf): Fix archive handler trying to archive its own log.
    + 09/24/17 (pjf):
        - Catch all exceptions (not just ScriptError) to ensure .fail files are created.
        - Check task_mode against TaskMode.kRun rather than "normal"
    + 09/25/17 (pjf): Improve archive_handler_generic() with tar --transform.
    + 09/21/17 (pjf): Output phase docstring summary lines in toc.
    + 04/04/18 (mac): Improve task handling.
      - Respond to locking clash with quiet yield.
      - Place floor on required time for next task, to allow for large fluctuations on short tasks.
    + 04/23/18 (pjf): Improve pool matching with comma-separated lists and glob-like patterns.
    + 05/30/19 (pjf):
        - Rewrite archive_handler_generic() to handle more complex results directory structures.
        - Generate subarchives for subdirectories of results directory.
    + 06/06/19 (pjf):
        - Improve performance of toc generation with os.listdir().
        - Colorize toc terminal output.
    + 07/14/19 (mac):
        - Restore archive_handler_generic as archive handler for generic use case from commit b12373a.
        - Rename pjf archive_handler_generic to archive_handler_automagic().
        - Add archive_handler_subarchives(), taking custom subarchive list.
    + 11/05/19 (pjf): Catch all exceptions derived from BaseException, to create
        fail flags more robustly.
    + 11/13/19 (mac): Change creation condition for subarchives in
        archive_handler_subarchives().
    + 12/10/19 (pjf):
        - Remove extraneous directory existence checks.
        - Fail on duplicate task descriptor.
    + 12/11/19 (pjf): Add save_results_single() and save_results_multi() for
        convenient saving of results files to appropriate locations.
    + 06/02/20 (pjf):
        - Allow tasks to signal incompleteness by raising exception.InsufficientTime.
        - Get elapsed and remaining time using interface from parameters.
    + 06/29/20 (mac): Fix default (generic) case of archive_handler_hsi().
    + 08/11/20 (pjf):
        - Use utils.TaskTimer in invoke_tasks_run().
        - Don't return timing from do_task().
        - Use exception.LockContention to allow do_task() to yield on lock clash.
    + 08/16/20 (pjf): Correctly handle empty file list in save_results_multi().
"""

import datetime
import enum
import glob
import os
import sys
import time
import inspect
import fnmatch


from . import (
    control,
    exception,
    parameters,
    utils,
)


################################################################
# task special run modes
################################################################

class TaskMode(enum.Enum):
    kRun = 0
    kTOC = 1
    kUnlock = 2
    kArchive = 3
    kPrerun = 4
    kOffline = 5

################################################################
# task statuses
################################################################

class TaskStatus(enum.Enum):
    kLocked = "\033[33m"+"L"+"\033[0m"
    kFailed = "\033[31m"+"F"+"\033[0m"
    kIncomplete = "\033[34m"+"I"+"\033[0m"
    kDone = "\033[32m"+"X"+"\033[0m"
    kMasked = "."
    kPending = "-"

################################################################
# global storage
################################################################

# directory structure -- global definitions
task_root_dir = None
flag_dir = None
output_dir = None
results_dir = None
archive_dir = None


################################################################
# bookkeeping initialization
################################################################

def task_read_env():
    """ Read environment variables for task settings.

    Environment variables:
        MCSCRIPT_TASK_MODE -- major run mode: toc, setup, archive, unlock, normal
        MCSCRIPT_TASK_PHASE -- phase (0-based) for tasks to be executed
        MCSCRIPT_TASK_POOL -- named pool for tasks to be executed (or ALL)
        MCSCRIPT_TASK_START_INDEX -- starting value for task index (or offset for job rank in epar mode)
        MCSCRIPT_TASK_COUNT_LIMIT -- flag to request generation of TOC file
        MCSCRIPT_TASK_REDIRECT -- flag to request diagnostic dump of output to terminal

    Parameter fields:
        "mode"
        "phase"
        "pool"
        "start_index"
        "count_limit"
        "redirect"

    Returns:
        (dict): multi-task run parameters
    """

    task_parameters = {}

    task_parameters["mode"] = TaskMode(int(os.environ["MCSCRIPT_TASK_MODE"]))
    task_parameters["phase"] = int(os.environ.get("MCSCRIPT_TASK_PHASE",0))
    task_parameters["pool"] = os.environ.get("MCSCRIPT_TASK_POOL")
    task_parameters["count_limit"] = int(os.environ.get("MCSCRIPT_TASK_COUNT_LIMIT",-1))
    task_parameters["start_index"] = int(os.environ.get("MCSCRIPT_TASK_START_INDEX",0))
    task_parameters["redirect"] = os.environ.get("MCSCRIPT_TASK_REDIRECT")=="True"

    return task_parameters

################################################################
# directory setup
################################################################

def make_task_dirs ():
    """Ensure the existence of special subdirectories for task processing.
    """

    utils.mkdir(flag_dir, exist_ok=True)
    utils.mkdir(output_dir, exist_ok=True)
    utils.mkdir(results_dir, exist_ok=True)
    utils.mkdir(archive_dir, exist_ok=True)

################################################################
# generic result storage support
################################################################

def save_results_single(
    task,
    source_file_path,
    target_filename=None,
    subdirectory="",
    command="mv"
):
    """Save single results file from task.

    Arguments:
        task (dict): task dictionary
        source_file_path (str): path of file to be saved
        target_filename (str, optional): target filename, default to
            source filename
        subdirectory (str, optional): destination subdirectory for results
        command (str, optional): type of save, "mv" or "cp", defaults to "mv"
    """
    # determine results directory path and ensure existence
    if results_dir is not None:
        res_dir = os.path.join(results_dir, subdirectory)
    else:
        res_dir = os.path.join(parameters.run.work_dir, subdirectory)
    utils.mkdir(res_dir, exist_ok=True)

    # determine target file path
    if target_filename is not None:
        target_file_path = os.path.join(res_dir, target_filename)
    else:
        target_file_path = os.path.join(res_dir, os.path.basename(source_file_path))

    # move file to destination
    control.call(
        [
            command,
            "--verbose",
            source_file_path,
            target_file_path
        ]
    )


def save_results_multi(
    task,
    source_file_list,
    target_directory_name=None,
    subdirectory="",
    command="mv"
):
    """Save multiple results files from task.

    Arguments:
        task (dict): task dictionary
        source_file_list (list of str): list of files to be saved
        target_directory_name (str, optional): target directory name, default to
            task descriptor
        subdirectory (str, optional): destination subdirectory for results
        command (str, optional): type of save, "mv" or "cp", defaults to "mv"
    """
    # determine results directory path and ensure existence
    if results_dir is not None:
        res_dir = os.path.join(results_dir, subdirectory)
        if target_directory_name is not None:
            target_directory_path = os.path.join(res_dir, target_directory_name)
        else:
            target_directory_path = os.path.join(res_dir, task["metadata"]["descriptor"])
    else:
        target_directory_path = os.path.join(parameters.run.work_dir, subdirectory)
    utils.mkdir(target_directory_path, parents=True, exist_ok=True)

    # do nothing if empty list passed
    if len(source_file_list) == 0:
        print("no source files provided... skipping")
        return

    # move file to destination
    control.call(
        [
            command,
            "--verbose",
            "--target-directory={}".format(target_directory_path)
        ] + source_file_list
    )


################################################################
# generic archiving support
################################################################

def archive_handler_generic(include_results=True):
    """Make archive of all metadata and results directories,
    to the run's archive directory.

    This is a "generic" archive handler, meant for use cases where the user does
    not wish to customize what the archive contains, how the archive is split
    up, whether or not there is compression, etc.

    The archive contains all the standard subdirectories except the archive
    directory and task work directories.  The result is placed in the archive
    directory.  This is just a local archive in scratch, so subsequent
    intervention is required to transfer the archive more permanently to, e.g.,
    a home directory or tape storage.

    The paths for the files in the archive are of the form runxxxx/results/*,
    etc.

    Returns:
        (str): archive filename (for convenience of calling function if
            wrapped in larger task handler)

    """

    # Debugging note: The tar call is liable to failure with exit code 1, e.g.:
    #
    #     tar: run0235/flags: file changed as we read it
    #
    # The problem arises since since the archive phase produces lock and
    # redirected output files.  One could ignore all error return codes
    # from tar, but this is clearly perilous.
    #
    # The problem is usually
    # avoided by avoiding running archive phases in parallel with each
    # other or, of course, runs of regular tasks.
    #
    # However: The tar call is *still* liable to failure with exit code
    # 1, e.g.:
    #
    #     tar: run0318/batch/1957945.edique02.ER: file changed as we read it
    #
    # if run in batch mode, since batch system may update output in
    # batch directory.  A solution would be to run archive phase from
    # archive subdirectory rather than batch subdirectory.
    #
    # And it reared its head again locally on cygwin due to logging of
    # the standard output to task-ARCH-*.out:
    #
    #     tar: runxxxx/output/task-ARCH-0.out: file changed as we read it
    #
    # Ah, robust solution is simply to exclude files "task-ARCH-*" from
    # the tar archive.


    # make archive -- whole dir
    if (include_results):
        mode_flag = ""
    else:
        mode_flag = "-nores"
    archive_filename = os.path.join(
        archive_dir,
        "{:s}-archive-{:s}{:s}.tgz".format(parameters.run.name,utils.date_tag(),mode_flag)
        )
    toc_filename = "{}.toc".format(parameters.run.name)
    filename_list = [
        toc_filename,
        "flags",
        "output",
        "batch"
    ]
    if (include_results):
        filename_list += ["results"]
    control.call(
        [
            "tar",
            "zcvf",
            archive_filename,
            "--transform=s,^,{:s}/,".format(parameters.run.name),  # prepend run name as directory
            "--show-transformed",
            "--exclude=task-ARCH-*"   # avoid failure return code due to "tar: runxxxx/output/task-ARCH-0.out: file changed as we read it"
        ] + filename_list,
        cwd=parameters.run.work_dir, check_return=True
        )

    return archive_filename

def archive_handler_automagic(include_results=True):
    """Make separate archives of all results subdirectories, plus metadata.

    Each archive contains all files or a single subdirectory of the results
    directory, plus all metadata (i.e. everything except the archive directory
    and task work directories).  The results are placed in the archive
    directory.  These are just local archives in scratch, so subsequent
    intervention is required to transfer the archives more permanently to, e.g.,
    a home directory or tape storage.

    The files in the archives are of the form runxxxx/results/res/*,
    runxxxx/results/out/*, runxxxx/results/*, etc.

    Returns:
        (list of str): archive filenames (for convenience of calling function if
            wrapped in larger task handler)

    """


    # make archive -- whole dir
    postfix_paths_list = []
    if (include_results):
        # determine sub-archives to generate
        with os.scandir("results") as results_dir:
            postfix_paths_list += [
                ("-"+str(entry.name), [entry.path])
                for entry in results_dir if entry.is_dir()
            ]
            if len(postfix_paths_list) > 0:
                # collect files in results dir into main archive
                file_list = [entry.path for entry in results_dir if entry.is_file()]
                if len(file_list) > 0:
                    postfix_paths_list += [("", file_list)]
            else:
                #
                postfix_paths_list += [("", ["results"])]
    else:
        postfix_paths_list += [("-nores", [])]
    toc_filename = "{}.toc".format(parameters.run.name)

    archive_filename_list = []
    for (postfix, paths) in postfix_paths_list:
        filename_list = [
            toc_filename,
            "flags",
            "output",
            "batch"
        ] + paths
        archive_filename = os.path.join(
            archive_dir,
            "{:s}-archive-{:s}{:s}.tar".format(parameters.run.name,utils.date_tag(),postfix)
            )
        control.call(
            [
                "tar",
                "cvf",
                archive_filename,
                "--transform=s,^,{:s}/,".format(parameters.run.name),  # prepend run name as directory
                "--show-transformed",
                "--exclude=task-ARCH-*"   # avoid failure return code due to "tar: runxxxx/output/task-ARCH-0.out: file changed as we read it"
            ] + filename_list,
            cwd=parameters.run.work_dir, check_return=True
            )
        archive_filename_list.append(archive_filename)

    # compress if applicable
    for (i, filename) in enumerate(archive_filename_list):
        if utils.is_compressible(filename):
            control.call(["gzip", "--verbose", "--suffix", ".gz", filename])
            archive_filename_list[i] = filename+".gz"

    return archive_filename_list

def archive_handler_subarchives(archive_parameters_list):
    """Make sepearate archives of specified results subdirectories, plus metadata.

    That is, each archive contains all files or a single subdirectory of the
    results directory, plus all metadata (i.e. everything except the archive
    directory and task work directories).  The results are placed in the
    archive directory.  These are just local archives in scratch, so
    subsequent intervention is required to transfer the archives more
    permanently to, e.g., a home directory or tape storage.

    A subarchive is created if if *any* of the requested paths exist or if the
    archive is supposed to include metadata.  Otherwise, it is skipped.

    The files in the archives are of the form runxxxx/results/res/*,
    runxxxx/results/out/*, runxxxx/results/*, etc.

    Arguments:
        archive_parameters_list (list of dict): list specifying resulting subarchives
            Each dict must contain:
              "postfix" (str): postfix to use on archive name (e.g., "", "-res", ...)
              "paths" (list): list of subdirectories with respect to results directory
              "compress" (bool,optional): whether or not to compress
              "include_metadata" (bool,optional): whether or not to include metadata directories

    Returns:
        (list of str): archive filenames (for convenience of calling function if
            wrapped in larger task handler)

    """

    toc_filename = "{}.toc".format(parameters.run.name)
    archive_filename_list = []
    for archive_parameters in archive_parameters_list:

        # extract parameters
        postfix = archive_parameters["postfix"]
        paths = archive_parameters["paths"]
        compress = archive_parameters.get("compress",False)
        include_metadata = archive_parameters.get("include_metadata",False)

        # construct archive filename
        extension = ".tgz" if compress else ".tar"
        archive_filename = os.path.join(
            archive_dir,
            "{:s}-archive-{:s}{:s}{:s}".format(parameters.run.name,utils.date_tag(),postfix,extension)
            )
        print("Archive: {}".format(archive_filename))

        # check that at least some contents exist (else skip)
        available_paths = []
        for path in paths:
            if (os.path.isdir(path)):
                available_paths.append(path)
        if ((len(available_paths)==0) and (not include_metadata)):
            print("None of paths {} available and no request to save metadata.  Skipping archive...".format(paths))
            continue
        archive_filename_list.append(archive_filename)

        # construct archive
        filename_list = [toc_filename]
        if (include_metadata):
            filename_list += ["flags","output","batch"]
        filename_list += available_paths
        tar_flags = "zcvf" if compress else "cvf"
        control.call(
            [
                "tar",
                tar_flags,
                archive_filename,
                "--transform=s,^,{:s}/,".format(parameters.run.name),  # prepend run name as directory
                "--show-transformed",
                "--exclude=task-ARCH-*"   # avoid failure return code due to "tar: runxxxx/output/task-ARCH-0.out: file changed as we read it"
            ] + filename_list,
            cwd=parameters.run.work_dir, check_return=True
            )

    return archive_filename_list

def archive_handler_no_results():
    return archive_handler_generic(include_results=False)

def archive_handler_hsi(archive_filename_list=None):
    """Save archive to tape.

    Arguments:
        archive_filename: (list of str, optional) names of files to move to tape;
            generate standard archive if omitted

    Returns:
        (list of str): names of files moved to tape (for convenience of calling
            function if wrapped in larger task handler)
    """

    # make archive -- whole dir
    if archive_filename_list is None:
        archive_filename_list = [archive_handler_generic()]

    # put to hsi
    hsi_subdir = format(datetime.date.today().year,"04d")  # subdirectory named by year
    for archive_filename in archive_filename_list:
        hsi_argument = "lcd {archive_directory}; mkdir {hsi_subdir}; cd {hsi_subdir}; put {archive_filename}".format(
            archive_filename=os.path.basename(archive_filename),
            archive_directory=os.path.dirname(archive_filename),
            hsi_subdir=hsi_subdir
        )
        control.call(["hsi",hsi_argument])

    return archive_filename_list

################################################################
# recall functions
################################################################

def index_str(task_index):
    """ Format a task index as %04d, or pass through other strings
    for special purposes (e.g., ARCH).

    Arguments:
        task_index (int or str): task index

    Returns:
        (str): formatted index
    """

    if (type(task_index) == int):
        return format(task_index,"04d")
    else:
        return str(task_index)

def task_toc(task_list,phase_handlers,color=False):
    """ Generate a task status report as a newline-delimited string.

    Arguments:
        task_list (dict): task list
        phase_handlers (list of callables): phase handlers
        color (bool, optional): colorize task status

    Returns:
        (str): table of contents
    """

    lines = [
        "Run: {:s}".format(parameters.run.name),
        "{:s}".format(time.asctime()),
        "Phases: {:d}".format(len(phase_handlers))
        ]

    for task_phase in range(len(phase_handlers)):
        # retrieve phase handler docstring
        phase_docstring = inspect.getdoc(phase_handlers[task_phase])
        phase_summary = "{}".format(phase_docstring).splitlines()[0]
        lines.append("  Phase {:d} summary: {:s}".format(task_phase, phase_summary))

    # get flag directory contents
    flag_dir_list = os.listdir(flag_dir)

    lines.append("Tasks: {:d}".format(len(task_list)))
    for task_index in range(len(task_list)):

        # retrieve task properties
        task = task_list[task_index]
        task_pool = task["metadata"]["pool"]
        task_descriptor = task["metadata"]["descriptor"]
        task_mask = task["metadata"]["mask"]

        # assemble line
        fields = [index_str(task_index), task_pool]
        fields += [task_status(task_index,task_phase,task_mask,flag_dir_list).value for task_phase in range(len(phase_handlers))]
        fields += [task_descriptor]

        # accumulate line
        lines.append(utils.spacify(fields))

    return "\n".join(lines)

def task_unlock(lock_types=(TaskStatus.kLocked,TaskStatus.kFailed)):
    """ Remove all lock and fail flags.
    """

    flag_files = []
    if TaskStatus.kLocked in lock_types:
        flag_files += glob.glob(os.path.join(flag_dir,"task*.lock"))
    if TaskStatus.kFailed in lock_types:
        flag_files += glob.glob(os.path.join(flag_dir,"task*.fail"))
    print("Removing lock/fail files:", flag_files)
    for flag_file in flag_files:
        os.remove(flag_file)

def task_flag_base(task_index,phase):
    """Generate flag file basename for the given phase of the given task.

    Arguments:
        task_index (int or str): task index
        phase (int): task phase

    Returns:
        (str): base file name
    """

    return "task-{:s}-{:d}".format(index_str(task_index), phase)

def task_output_filename(task_index,phase):
    """Generate the output redirection filename for the given phase of
    the given task.

    Arguments:
        task_index (int or str): task index
        phase (int): task phase

    Returns:
        (str): redirection file name

    """

    return os.path.join(output_dir,"task-{:s}-{:d}.out".format(index_str(task_index),phase))

def task_status(task_index,task_phase,task_mask,flag_dir_list=None):
    """ Generate status flag for the given phase of the given task.

    Status flag values:
        "L": locked (in progress or crashed ungracefully)
        "F": failure (crashed gracefully)
        "X": done
        ".": masked out
        "-": pending

    Arguments:
        task_index (int or str): task index
        task_phase (int): task phase
        task_mask (bool): mask flag for task
        flag_dir_list (list of str): directory listing for flag directory

    Returns:
        (TaskStatus): status flag
    """
    if flag_dir_list is not None:
        flag_base = task_flag_base(task_index,task_phase)
        if (flag_base + ".lock") in flag_dir_list:
            return TaskStatus.kLocked
        elif (flag_base + ".fail") in flag_dir_list:
            return TaskStatus.kFailed
        elif (flag_base + ".incp") in flag_dir_list:
            return TaskStatus.kIncomplete
        elif (flag_base + ".done") in flag_dir_list:
            return TaskStatus.kDone
        elif not task_mask:
            return TaskStatus.kMasked
        else:
            return TaskStatus.kPending
    else:
        flag_base = os.path.join(flag_dir, task_flag_base(task_index,task_phase))
        if os.path.exists(flag_base + ".lock"):
            return TaskStatus.kLocked
        elif os.path.exists(flag_base + ".fail"):
            return TaskStatus.kFailed
        elif os.path.exists(flag_base + ".incp"):
            return TaskStatus.kIncomplete
        elif os.path.exists(flag_base + ".done"):
            return TaskStatus.kDone
        elif not task_mask:
            return TaskStatus.kMasked
        else:
            return TaskStatus.kPending

################################################################
# locking protocol
################################################################

def get_lock(task_index,task_phase):
    """ Write lock file for given task and given phase.

    Arguments:
        task_index (int or str): task index
        task_phase (int): task phase

    Returns:
        success (bool): if lock was successfully obtained
    """

    flag_base = os.path.join(flag_dir, task_flag_base(task_index,task_phase))

    # preliminary lock
    lock_stream = open(flag_base+".lock", "w")
    lock_stream.write("{}".format(parameters.run.job_id))  # omit newline since will do string comparison below
    lock_stream.close()
    # make sure lock was successful
    if (parameters.run.batch_mode):
        # primarily need to worry about locking clash in batch mode, either when
        # batch jobs start simultaneously or, less frequently, when concurrent
        # batch jobs reach for their next task at the same time (although it
        # could happen in interactive mode if two runs are being done
        # simultaneously, e.g., from different terminal windows)
        wait_time = 3
        time.sleep(wait_time)
        lock_stream = open(flag_base+".lock", "r")
        line = lock_stream.readline()
        lock_stream.close()
        if (line == parameters.run.job_id):
            print("Lock was apparently successful...")
        else:
            print("Locking clash: Current job is {} but lock file is from {}.  Yielding lock.".format(parameters.run.job_id,line))
            ## raise exception.ScriptError("Yielding lock to other instance")
            return False

    # write expanded lock contents
    lock_stream = open(flag_base+".lock","a")
    lock_stream.write("\n".format(flag_base))  # add newline after job id
    lock_stream.write("{}\n".format(flag_base))
    lock_stream.write("{}\n".format(time.asctime()))
    lock_stream.close()

    # remove any prior incomplete flag
    if os.path.exists(flag_base+".incp"):
        os.remove(flag_base+".incp")

    return True

def fail_lock(task_index,task_phase,task_time):
    """Rename lock file to failure file.

    Arguments:
        task_index (int or str): task index
        task_phase (int): task phase
    """

    flag_base = os.path.join(flag_dir, task_flag_base(task_index,task_phase))
    os.rename(flag_base+".lock",flag_base+".fail")

def incomplete_lock(task_index, task_phase, task_time):
    """Rename lock to incomplete file.

    Arguments:
        task_index (int or str): task index
        task_phase (int): task phase
        task_time (float): timing for task
    """

    flag_base = os.path.join(flag_dir, task_flag_base(task_index, task_phase))
    os.rename(flag_base+".lock",flag_base+".incp")

def finalize_lock(task_index,task_phase,task_time):
    """Finalize lock file for given task and given phase, and covert it
    to done file.

    Arguments:
        task_index (int or str): task index
        task_phase (int): task phase
        task_time (float): timing for task
    """

    flag_base = os.path.join(flag_dir, task_flag_base(task_index,task_phase))

    # augment lock file
    lock_stream = open(flag_base+".lock","a")
    lock_stream.write("{}\n".format(time.asctime()))
    lock_stream.write("{:.2f}\n".format(task_time))
    lock_stream.close()

    # move lock file to done file
    os.rename(flag_base+".lock",flag_base+".done")


################################################################
# special runs: archive
################################################################

def write_toc(task_list,phase_handlers):
    """ Write current table of contents to file runxxxx.toc.

    Arguments:
        task_list (dict): task list
        phase_handlers (list of callables): phase handlers

    Returns:
        (str): toc filename, sans path (as convenience to caller)
    """

    # write current toc
    toc_filename = "{}.toc".format(parameters.run.name)
    toc_stream = open(toc_filename, "w")
    toc_stream.write(utils.scrub_ansi(task_toc(task_list,phase_handlers)))
    toc_stream.close()

    # return filename
    return toc_filename

def do_archive(task_parameters,archive_phase_handlers):
    """ do_archive() --> time sets up the archive task/phase, calls its handler, and closes up

    The phase handler is called

    Arguments:
        ...

    """

    task_index = "ARCH"  # special value for use in filename generation
    task_phase = task_parameters["phase"]
    # lock task
    # CAVEAT: file system asynchrony (?) or simultaneus running of
    # different archive phases can cause trouble with tar archiving,
    # if tar senses lock file appearing or disappearing during
    # archiving of flags directory -- results in exit with failure code
    get_lock(task_index,task_phase)

    # initiate timing
    task_start_time = time.time()

    # handle task
    # with output redirection
    saved_stdout = sys.stdout
    ## output_filename = task_output_filename(task_index,task_phase)
    output_filename = os.path.join(
        archive_dir,
        "{:s}-archive-{:s}.out".format(parameters.run.name, utils.date_tag())
        )

    print("Redirecting to", output_filename)
    sys.stdout = open(output_filename, "w")
    archive_phase_handlers[task_phase]()
    sys.stdout = saved_stdout

    # process timing
    task_end_time = time.time()
    task_time = task_end_time - task_start_time

    # process lock file to done file
    finalize_lock(task_index,task_phase,task_time)

    # cd back to task root directory
    os.chdir(task_root_dir)


################################################################
# task invocation functions
################################################################

def match_pool(pool, patterns):
    """Check if pool matches pattern.

    Arguments:
        pool (str): pool to check
        patterns (str): match patterns, possibly comma-delimited

    Returns:
        (bool): whether or not pool matches (one of) pattern(s)
    """
    # check for None pattern
    if (patterns is None) and (pool is None):
        return True

    # check for "ALL" pattern
    if patterns == "ALL":
        return True

    # check against patterns as patterns
    pattern_list = patterns.split(",")
    for pattern in pattern_list:
        if fnmatch.fnmatchcase(pool, pattern):
            return True

    # no pattern matched
    return False

def seek_task(task_list,task_pool,task_phase,prior_task_index):
    """Seek next available task, at given phase, in given pool.

    Arguments:
        task_list (dict): dictionary of tasks
        task_pool (str): pool to consider (or "ALL")
        task_phase (int): phase to consider
        prior_task_index (int): last checked task index

    Returns:
       (int or None): index for next eligible task, or None if none found

    """

    next_index = None
    for task_index in range(prior_task_index+1, len(task_list)):
        # skip if task not matched by pool
        if not match_pool(task_list[task_index]["metadata"]["pool"], task_pool):
            continue

        # skip if task locked or done
        task_mask = task_list[task_index]["metadata"]["mask"]
        if task_status(task_index, task_phase, task_mask) not in (TaskStatus.kPending, TaskStatus.kIncomplete):
            continue

        # skip if prior phase not completed
        if (task_phase > 0):
            if task_status(task_index, task_phase-1, task_mask) != TaskStatus.kDone:
                print("Missing prerequisite", task_flag_base(task_index, task_phase-1))
                continue

        # designate this task as the one to do
        next_index = task_index
        break

    return next_index

def do_task(task_parameters,task,phase_handlers):
    """ do_task() --> sets up a task/phase, calls its handler, and closes up

    The current working directory is changed to the task directory.
    A lock file is created for the task and phase.
    The phase handler is called.
    The current working directory is changed back up one level (presumably to the run scratch directory).
    The lock file for the task and phase is changed into a completion file.

    Arguments:
       task_parameters (dict): task parameters (needed for some global properties, e.g., redirection mode)
       task (dict): Task dictionary (including metadata such as desired phase)
       phase_handlers (list): List of phase handlers

    Returns:
       (float): task time (or None)

    """

    # extract task parameters
    task_mode = task_parameters["mode"]
    task_phase = task_parameters["phase"]
    task_index = task["metadata"]["index"]
    task_descriptor = task["metadata"]["descriptor"]
    task_mask = task["metadata"]["mask"]

    # fill in further metadata for task handlers
    task["metadata"]["phase"] = task_phase
    task["metadata"]["mode"] = task_mode

    # get lock
    if task_mode != TaskMode.kPrerun:
        success = get_lock(task_index, task_phase)
        # if lock is already taken, yield this task
        if not success:
            raise exception.LockContention(task_index, task_phase)

    # set up task directory
    task_dir = os.path.join(task_root_dir, "task-{:04d}.dir".format(task_index))
    utils.mkdir(task_dir, exist_ok=True)
    os.chdir(task_dir)

    # initiate timing
    task_start_time = time.time()

    # set up output redirection
    if (task_mode != TaskMode.kPrerun):
        redirect_stdout = task_parameters["redirect"]
        output_filename = task_output_filename(task_index,task_phase)
        # purge any old file -- else it may persist if current task aborts
        if (os.path.exists(output_filename)):
            os.remove(output_filename)
        if (redirect_stdout):
            print("Redirecting to", output_filename)
            saved_stdout = sys.stdout
            sys.stdout = open(output_filename, "w")

    # generate header for task output file
    if (task_mode != TaskMode.kPrerun):
        print(64*"-")
        print("task {} phase {}".format(task_index,task_phase))
        print(task["metadata"]["descriptor"])
        print(64*"-")
        print(parameters.run.run_data_string())
        print(utils.time_stamp())
        print(64*"-")
        print()
        sys.stdout.flush()

    # invoke task handler
    try:
        phase_handlers[task_phase](task)
    except exception.InsufficientTime as err:
        print("Insufficient time to complete task")
        if task_mode is TaskMode.kRun:
            task_end_time = time.time()
            task_time = task_end_time - task_start_time
            print("  task elapsed: {:g}, total elapsed: {:g}, required: {:g}, remaining: {:g}".format(
                task_time, parameters.run.get_elapsed_time(),
                err.required_time, parameters.run.get_remaining_time()
                ))
            incomplete_lock(task_index, task_phase, task_time)
        raise
    except BaseException as err:
        # on failure, flag failure and propagate exception so script terminates
        print("Exception:", err)
        if task_mode is TaskMode.kRun:
            # process timing
            task_end_time = time.time()
            task_time = task_end_time - task_start_time
            fail_lock(task_index, task_phase, task_time)
        raise

    # undo output redirection
    if (task_mode != TaskMode.kPrerun):
        sys.stdout.flush()
        if (redirect_stdout):
            sys.stdout.close()
            sys.stdout = saved_stdout

    # process timing
    task_end_time = time.time()
    task_time = task_end_time - task_start_time

    # process lock file to done file
    if (task_mode != TaskMode.kPrerun):
        finalize_lock(task_index,task_phase,task_time)

    # cd back to task root directory
    os.chdir(task_root_dir)


################################################################
# task master function
################################################################

def invoke_tasks_prerun(task_parameters,task_list,phase_handlers):
    """ Iterate over tasks to invoke them for setup run.

    Arguments:
        task_parameters (dict): multi-task run parameters
        task_list (dict): task list
        phase_handlers (list): phase handlers
    """

    # retrieve multi-task run parameters
    task_mode = task_parameters["mode"]
    task_pool = task_parameters["pool"]
    task_phase = task_parameters["phase"]
    task_start_index = task_parameters["start_index"]
    task_count_limit = task_parameters["count_limit"]

    task_index = -1  # "last run task" for seeking purposes
    while (True):
        # seek next task
        task_index = seek_task(task_list,task_pool,task_phase,task_index)
        if (task_index is None):
            print("No more available tasks in pool", task_pool)
            break
        task = task_list[task_index]

        # display diagnostic header for task
        #     this goes to global (unredirected) output
        print("[task {} phase {} {}]".format(task_index,task_phase,task["metadata"]["descriptor"]))
        sys.stdout.flush()

        # execute task
        do_task(task_parameters,task,phase_handlers)
        ## print("(Task setup time: {:.2f} sec)".format(task_time))


def invoke_tasks_run(task_parameters,task_list,phase_handlers):
    """ Iterate over tasks to invoke them for normal run.

    Arguments:
        task_parameters (dict): multi-task run parameters
        task_list (dict): task list
        phase_handlers (list): phase handlers
    """

    # retrieve multi-task run parameters
    task_mode = task_parameters["mode"]
    task_pool = task_parameters["pool"]
    task_phase = task_parameters["phase"]
    task_start_index = task_parameters["start_index"]
    task_count_limit = task_parameters["count_limit"]

    # epar diagnostics
    ## if (parameters.run.parallel_epar != -1):
    ##     print("In epar task_master ({:d})...".format(parameters.run.epar_rank))
    ##     sys.stdout.flush()

    task_index = task_start_index-1  # "last run task" for seeking purposes
    task_count = 0
    avg_task_time = 0.
    task_time = 0.
    timer = utils.TaskTimer(
        remaining_time=parameters.run.get_remaining_time(),
        safety_factor=1.1,
        minimum_time=60
        )
    while True:

        # check limits
        if not ((task_count_limit == -1) or (task_count < task_count_limit)) :
            print("Reached task count limit.")
            break

        # check remaining time
        print()
        print("Task timing: elapsed {:g}, remaining {:g}, last task {:g}, average {:g}, required {:g}".format(
            timer.elapsed_time,timer.remaining_time,timer.last_time,timer.average_time,timer.required_time
            ))
        print()

        # seek next task
        task_index = seek_task(task_list,task_pool,task_phase,task_index)
        if task_index is None:
            print("No more available tasks in pool", task_pool)
            break
        task = task_list[task_index]

        try:
            timer.start_timer()
        except exception.InsufficientTime:
            print("Reached time limit.")
            break

        # display diagnostic header for task
        #     this goes to global (unredirected) output
        print("[task {} phase {} {}]".format(task_index,task_phase,task["metadata"]["descriptor"]))
        sys.stdout.flush()

        # execute task
        try:
            do_task(task_parameters,task,phase_handlers)
        except exception.LockContention:
            print("(Task yielded)")
            timer.cancel_timer()
        else:
            task_time = timer.stop_timer()
            print("(Task time: {:.2f} sec)".format(task_time))
            # tally
            task_count += 1


def task_master(task_parameters,task_list,phase_handlers,archive_phase_handlers):
    """ Control multi-task run.

    Globals:
        ...

    Arguments:
        ...
    """

    task_mode = task_parameters["mode"]
    task_pool = task_parameters["pool"]

    # check that pool defined
    if (task_mode in (TaskMode.kRun,TaskMode.kPrerun,TaskMode.kOffline)):
        if (task_pool == None):
            print("Exiting without doing anything, since no pool specified.")
            return

    # special run modes
    if (task_mode == TaskMode.kTOC):
        # update toc file
        toc_filename = write_toc(task_list,phase_handlers)
        # replicate toc file contents to stdout
        print()
        color = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
        print(task_toc(task_list,phase_handlers,color))
        print()
    elif (task_mode == TaskMode.kUnlock):
        task_unlock()
    elif (task_mode == TaskMode.kArchive):
        write_toc(task_list,phase_handlers)  # update toc for archive
        do_archive(task_parameters,archive_phase_handlers)
    elif (task_mode == TaskMode.kPrerun):
        invoke_tasks_prerun(task_parameters,task_list,phase_handlers)
    elif ((task_mode == TaskMode.kRun) or (task_mode == TaskMode.kOffline)):
        invoke_tasks_run(task_parameters,task_list,phase_handlers)
    else:
        raise(exception.ScriptError("Unsupported run mode: {:s}".format(task_mode)))


################################################################
# caller interface
################################################################

def init(
        task_list,
        task_descriptor=(lambda task : None),
        task_pool=(lambda task : None),
        task_mask=(lambda task : True),
        phase_handler_list=[],
        archive_phase_handler_list=[]
):
    """Stores the given list of tasks and postprocesses it, adding
    fields with values given by the given functions.

    The task "descriptor", "pool", and "mask" fields are set by invoking the given
    functions task_descriptor, task_pool, and task_mask, respectively, on each task.

    Also registers the phase handlers.  The number of phases is also
    set from the length of the phase handler list.

    Finally, invokes master task handling loop.

    Globals:
        phase, ...

    Arguments:
        ...
    """

    # task directories
    #
    # Note: ideally these should be moved out of global storage, but
    # user code will need modification.

    global task_root_dir, flag_dir, output_dir, results_dir, archive_dir
    task_root_dir = parameters.run.work_dir
    flag_dir = os.path.join(parameters.run.work_dir,"flags")
    output_dir = os.path.join(parameters.run.work_dir,"output")
    results_dir = os.path.join(parameters.run.work_dir,"results")
    archive_dir = os.path.join(parameters.run.work_dir,"archive")

    # task environment variable communication
    task_parameters = task_read_env()

    # set up task directories
    make_task_dirs()

    # process task list
    task_descriptor_set = set()
    for (index, task) in enumerate(task_list):
        # encapsulated metadata
        metadata = {
            "descriptor" : task_descriptor(task),
            "pool" : task_pool(task),
            "mask" : task_mask(task),
            "index" : index,
            "mode" : None,  # to be set at task invocation time
            "phase" : None  # to be set at task invocation time
        }
        task["metadata"] = metadata

        # check for duplicate task descriptors
        if metadata["descriptor"] in task_descriptor_set:
            raise exception.ScriptError(
                "duplicate task descriptor: {}".format(metadata["descriptor"])
            )
        task_descriptor_set.add(metadata["descriptor"])

    # alias handler arguments
    phase_handlers = phase_handler_list
    archive_phase_handlers = archive_phase_handler_list

    # invoke master loop
    task_master(task_parameters,task_list,phase_handlers,archive_phase_handlers)
