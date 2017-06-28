""" mcscript_task -- task control utility functions

    Meant to be loaded as part of mcscript.  Provides the
    mcscript.task.* definitions in mcscript.

    Globals: requires attributes of mcscript.run to be populated

    Language: Python 3

    M. A. Caprio
    University of Notre Dame

    + 3/2/13 (mac): Originated as task.py.
    + 5/28/13 (mac): Updated to recognize ScriptError exception.
    + 6/5/13 (mac): Absorbed into mcscript package.
    + 11/1/13 (mac): Add local archive dir in scratch to help circumvent home space overruns.
    + 1/22/14 (mac): Python 3 update.
    + 7/3/14 (mac): Add generic archiving support.
    + 5/14/15 (mac): Insert "future" statements and convert print to write
          for Python 2 legacy support.  Upgrade string formatting to
          Python 2.7 format method.
    + 6/4/15 (mac): Add check for locking clashes.
    + 6/25/15 (mac): Simplify task interface to single init() function.
    + 6/13/16 (mac): Rename environment variables TASK_* to MCSCRIPT_TASK_*. Restructure subpackages.
    + 1/18/17 (mac):
          - Update archive handler.
          - Rename optional argument archive_handler_list to archive_phase_handler_list.
    + 1/21/17 (mac): Fix spurious argument on archive_handler_hsi.
    + 2/23/17 (mac): Switch from os.mkdir to mcscript.utils.mkdir.
    + 3/16/17 (mac):
        - Restructure to avoid most global variables.
        - Upgrade docstrings.
        - Change environment interface to expect MCSCRIPT_TASK_MODE.
        - Allow for "setup" task mode.
        - Define task "metadata" field.
    + 3/18/17 (mac):
        - Define task modes as enum.
        - Rename "setup" mode to "prerun".
    + 5/22/17 (mac): Fix processing of boolean option MCSCRIPT_TASK_REDIRECT.
    + 6/28/17 (mac): Add archive handler archive_handler_no_results.
"""

import datetime
import enum
import glob
import os
import sys
import time
import copy


import mcscript.control
import mcscript.exception
import mcscript.parameters
import mcscript.utils

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
    """ make_task_dirs () ensures the existence of special subdirectories for task processing

    TODO: since existence check is not robust against multiple scripts
    attempting in close succession, replace this with a try/except.
    """

    if ( not os.path.exists(flag_dir)):
        mcscript.utils.mkdir(flag_dir)

    if ( not os.path.exists(output_dir)):
        mcscript.utils.mkdir(output_dir)

    if ( not os.path.exists(results_dir)):
        mcscript.utils.mkdir(results_dir)

    if ( not os.path.exists(archive_dir)):
        mcscript.utils.mkdir(archive_dir)

################################################################
# generic archiving support
################################################################


def archive_handler_generic(include_results=True):
    """Make generic archive of all metadata and results directories,
    to the run's archive directory.

    A fresh TOC file is generated before archiving.

    That is, the archive contains everything except the archive
    directory and task work directories.  The result is placed in the
    archive directory.  This is just a local archive in scratch, so
    subsequent intervention is required to transfer the archive more
    permanently to, e.g., a home directory or tape storage.

    The files in the archive are of the form runxxxx/results/*, etc.

    Known issue: The tar call is liable to failure with exit code 1, e.g.:

       tar: run0235/flags: file changed as we read it

    The problem arises since since the archive phase produces lock and
    redirected output files.  One could ignore the error, but this is
    clearly perilous.  The problem is usually avoided by avoiding
    running archive phases in parallel with each other or, of course,
    runs of regular tasks.

    Known issue: The tar call is *still* liable to failure with exit code 1, e.g.:

       tar: run0318/batch/1957945.edique02.ER: file changed as we read it

    if run in batch mode, since batch system may update output in
    batch directory.  A solution would be to run archive phase from
    archive subdirectory rather than batch subdirectory.


    Returns:
        (str): archive filename (for convenience of calling function if
            wrapped in larger task handler)

    """

    # make archive -- whole dir
    work_dir_parent = os.path.join(task_root_dir,"..")
    archive_filename = os.path.join(
        archive_dir,
        "{:s}-archive-{:s}.tgz".format(mcscript.parameters.run.name, mcscript.utils.date_tag())
        )
    toc_filename = "{}.toc".format(mcscript.parameters.run.name)
    filename_list = [
        os.path.join(mcscript.parameters.run.name,toc_filename),
        os.path.join(mcscript.parameters.run.name,"flags"),
        os.path.join(mcscript.parameters.run.name,"output"),
        os.path.join(mcscript.parameters.run.name,"batch")
    ]
    if (include_results):
        filename_list.append(os.path.join(mcscript.parameters.run.name,"results"))
    mcscript.control.call(
        ["tar", "zcvf", archive_filename ] + filename_list,
        cwd=work_dir_parent,check_return=True
        )

    # copy archive out to home results archive directory
    ## mcscript.control.call(["cp","-v",archive_filename,"-t",ncsm_config.data_dir_results_archive], cwd=mcscript.task.results_dir)

    ## # put to hsi
    ## hsi_subdir = "2013"
    ## hsi_arg = "lcd %s; cd %s; put %s" % (os.path.dirname(archive_filename), hsi_subdir, os.path.basename(archive_filename))
    ## subprocess.call(["hsi",hsi_arg])

    return archive_filename

def archive_handler_no_results():
    archive_handler_generic(include_results=False)

def archive_handler_hsi():
    """ Generate standard archive and save to tape.
    """

    # make archive -- whole dir
    archive_filename = mcscript.task.archive_handler_generic()

    # put to hsi
    hsi_subdir = format(datetime.date.today().year,"04d")  # subdirectory named by year
    hsi_argument = "lcd {archive_directory}; mkdir {hsi_subdir}; cd {hsi_subdir}; put {archive_filename}".format(
        archive_filename=os.path.basename(archive_filename),
        archive_directory=os.path.dirname(archive_filename),
        hsi_subdir=hsi_subdir
    )
    mcscript.control.call(["hsi",hsi_argument])

    return archive_filename

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

def task_toc(task_list,phases):
    """ Generate a task status report as a newline-delimited string.

    Arguments:
        task_list (dict): task list
        phases (int): number of phases

    Returns:
        (str): table of contents
    """

    lines = [
        "Run: {:s}".format(mcscript.parameters.run.name),
        "{:s}".format(time.asctime()),
        "Tasks: {:d}".format(len(task_list)),
        ]
    for task_index in range(len(task_list)):

        # retrieve task properties
        task = task_list[task_index]
        task_pool = task["metadata"]["pool"]
        task_descriptor = task["metadata"]["descriptor"]
        task_mask = task["metadata"]["mask"]

        # assemble line
        fields = [ index_str(task_index), task_pool]
        fields += [task_status(task_index,task_phase,task_mask) for task_phase in range(phases)]
        fields += [ task_descriptor ]

        # accumulate line
        lines.append(mcscript.utils.spacify(fields))

    return "\n".join(lines)

def task_unlock():
    """ Remove all lock and fail flags.
    """

    flag_files = glob.glob(os.path.join(flag_dir,"task*.lock")) + glob.glob(os.path.join(flag_dir,"task*.fail"))
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

    return os.path.join(flag_dir,"task-{:s}-{:d}".format(index_str(task_index),phase))

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

def task_status(task_index,phase,task_mask):
    """ Generate status flag for the given phase of the given task.

    Status flag values:
        "L": locked (in progress or crashed ungracefully)
        "F": failure (crashed gracefully)
        "X": done
        ".": masked out
        "-": pending

    Arguments:
        task_index (int or str): task index
        phase (int): task phase
        task_mask (bool): mask flag for task

    Returns:
        (str): status flag
    """

    flag_base = task_flag_base(task_index,phase)
    if ( os.path.exists(flag_base + ".lock") ):
        return "L"
    elif ( os.path.exists(flag_base + ".fail") ):
        return "F"
    elif ( os.path.exists(flag_base + ".done") ):
        return "X"
    elif ( not task_mask ):
        return "."
    else:
        return "-"

################################################################
# locking protocol
################################################################

def get_lock(task_index,task_phase):
    """ Write lock file for given task and given phase.

    Arguments:
        task_index (int or str): task index
        task_phase (int): task phase
    """

    flag_base = task_flag_base(task_index,task_phase)

    # preliminary lock
    lock_stream = open(flag_base+".lock", "w")
    lock_stream.write("{}".format(mcscript.parameters.run.job_id))  # omit newline since will do string comparison below
    lock_stream.close()
    # make sure lock was successful
    if (mcscript.parameters.run.batch_mode):
        # only need to worry about locking clash when jobs start simultaneously in batch mode
        wait_time = 3
        time.sleep(wait_time)
        lock_stream = open(flag_base+".lock", "r")
        line = lock_stream.readline()
        lock_stream.close()
        if (line == mcscript.parameters.run.job_id):
            print("Lock was apparently successful...")
        else:
            print("Locking clash: Current job is {} but lock file is from {}.  Yielding lock.".format(mcscript.parameters.run.job_id,line))
            raise mcscript.exception.ScriptError("Yielding lock to other instance")

    # write expanded lock contents
    lock_stream = open(flag_base+".lock","a")
    lock_stream.write("\n".format(flag_base))  # add newline after job id
    lock_stream.write("{}\n".format(flag_base))
    lock_stream.write("{}\n".format(time.asctime()))
    lock_stream.close()


def fail_lock(task_index,task_phase,task_time):
    """Rename lock file to failure file.

    Arguments:
        task_index (int or str): task index
        task_phase (int): task phase
    """

    flag_base = task_flag_base(task_index,task_phase)
    os.rename(flag_base+".lock",flag_base+".fail")

def finalize_lock(task_index,task_phase,task_time):
    """Finalize lock file for given task and given phase, and covert it
    to done file.

    Arguments:
        task_index (int or str): task index
        task_phase (int): task phase
        task_time (float): timing for task
    """

    flag_base = task_flag_base(task_index,task_phase)

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

def write_toc(task_list,phases):
    """ Write current table of contents to file runxxxx.toc.

    Arguments:
        task_list (dict): task list
        phases (int): number of phases

    Returns:
        (str): toc filename, sans path (as convenience to caller)
    """

    # write current toc
    toc_filename = "{}.toc".format(mcscript.parameters.run.name)
    toc_stream = open(toc_filename, "w")
    toc_stream.write(task_toc(task_list,phases))
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
    output_filename = task_output_filename(task_index,task_phase)
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

    # select remaining tasks in given pool
    # (or all pools if pool is ALL)
    remaining_pool_task_indices = [
        task_index
        for task_index in range(prior_task_index+1,len(task_list))
        if ((task_list[task_index]["metadata"]["pool"] == task_pool) or (task_pool == "ALL"))
        ]
    ## DEBUG: print pool_task_indices

    next_index = None
    for task_index in remaining_pool_task_indices:

        # skip if task locked or done
        task_mask = task_list[task_index]["metadata"]["mask"]
        if ( task_status(task_index,task_phase,task_mask) != "-" ):
            continue

        # skip if prior phase not completed
        if (task_phase > 0):
            if ( task_status(task_index,task_phase-1,task_mask) != "X" ):
                print("Missing prerequisite", task_flag_base(task_index,task_phase-1))
                continue

        # designate this task as the one to do
        next_index = task_index
        break

    return next_index

def do_task(task_parameters,task,phase_handlers):
    """ do_task() --> time sets up a task/phase, calls its handler, and closes up

    The current working directory is changed to the task directory.
    A lock file is created for the task and phase.
    The phase handler is called.
    The current working directory is changed back up one level (presumably to the run scratch directory).
    The lock file for the task and phase is changed into a completion file.

    Arguments:
       task_parameters (dict): task parameters (needed for some global properties, e.g., redirection mode)
       task (dict): Task dictionary (including metadata such as desired phase)
       phase_handlers (list): List of phase handlers
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


    # set up task directory
    task_dir = os.path.join(task_root_dir, "task-{:04d}.dir".format(task_index))
    if (not os.path.exists(task_dir)):
        mcscript.utils.mkdir(task_dir)
    os.chdir(task_dir)

    # get lock
    if (task_mode != TaskMode.kPrerun):
        get_lock(task_index,task_phase)

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
        print(mcscript.parameters.run.run_data_string())
        print(mcscript.utils.time_stamp())
        print(64*"-")
        print()
        sys.stdout.flush()

    # invoke task handler
    try:
        phase_handlers[task_phase](task)
    except mcscript.exception.ScriptError as err:
        # on failure, flag failure and propagate exception so script terminates
        print("ScriptError:", err)
        if (task_mode == "normal"):
            fail_lock(task_index,task_phase)
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

    return task_time


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
        task = copy.deepcopy(task_list[task_index])

        # display diagnostic header for task
        #     this goes to global (unredirected) output
        print("[task {} phase {} {}]".format(task_index,task_phase,task["metadata"]["descriptor"]))
        sys.stdout.flush()

        # execute task
        task_time = do_task(task_parameters,task,phase_handlers)
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
    ## if (mcscript.parameters.run.parallel_epar != -1):
    ##     print("In epar task_master ({:d})...".format(mcscript.parameters.run.epar_rank))
    ##     sys.stdout.flush()

    task_index = task_start_index-1  # "last run task" for seeking purposes
    task_count = 0
    loop_start_time = time.time()
    task_time = 0.
    while (True):

        # check limits
        if (not ( (task_count_limit == -1) or (task_count < task_count_limit) ) ):
            print("Reached task count limit.")
            break

        # check remaining time
        loop_elapsed_time = time.time() - loop_start_time
        remaining_time = mcscript.parameters.run.wall_time_sec - loop_elapsed_time
        safety_factor = 1.1
        required_time = task_time*safety_factor
        print()
        print("Task timing: elapsed {:g}, remaining {:g}, last task {:g}, required {:g}".format(
            loop_elapsed_time,remaining_time,task_time,required_time
            ))
        print()
        if ( required_time > remaining_time ):
            print("Reached time limit.")
            break

        # seek next task
        task_index = seek_task(task_list,task_pool,task_phase,task_index)
        if (task_index is None):
            print("No more available tasks in pool", task_pool)
            break
        task = copy.deepcopy(task_list[task_index])

        # display diagnostic header for task
        #     this goes to global (unredirected) output
        print("[task {} phase {} {}]".format(task_index,task_phase,task["metadata"]["descriptor"]))
        sys.stdout.flush()

        # execute task (with timing)
        task_time = do_task(task_parameters,task,phase_handlers)
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
        toc_filename = write_toc(task_list,len(phase_handlers))
        # replicate toc file contents to stdout
        with open(toc_filename) as toc_stream:
            print()
            sys.stdout.writelines(toc_stream.readlines())
            print()
    elif (task_mode == TaskMode.kUnlock):
        task_unlock()
    elif (task_mode == TaskMode.kArchive):
        write_toc(task_list,len(phase_handlers))  # update toc for archive
        do_archive(task_parameters,archive_phase_handlers)
    elif (task_mode == TaskMode.kPrerun):
        invoke_tasks_prerun(task_parameters,task_list,phase_handlers)
    elif ((task_mode == TaskMode.kRun) or (task_mode == TaskMode.kOffline)):
        invoke_tasks_run(task_parameters,task_list,phase_handlers)
    else:
        raise(mcscript.exception.ScriptError("Unsupported run mode: {:s}".format(task_mode)))


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
    task_root_dir = mcscript.parameters.run.work_dir
    flag_dir = os.path.join(mcscript.parameters.run.work_dir,"flags")
    output_dir = os.path.join(mcscript.parameters.run.work_dir,"output")
    results_dir = os.path.join(mcscript.parameters.run.work_dir,"results")
    archive_dir = os.path.join(mcscript.parameters.run.work_dir,"archive")

    # task environment variable communication
    task_parameters = task_read_env()

    # set up task directories
    make_task_dirs()

    # process task list
    for index in range(len(task_list)):
        task = task_list[index]

        # legacy descriptor field
        # DEPRECATED in favor of ["metadata"]["descriptor"]
        # TODO -- remove legacy fields once sure nobody uses them
        task["descriptor"] = task_descriptor(task)

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

    # alias handler arguments
    phase_handlers = phase_handler_list
    archive_phase_handlers = archive_phase_handler_list

    # invoke master loop
    task_master(task_parameters,task_list,phase_handlers,archive_phase_handlers)
