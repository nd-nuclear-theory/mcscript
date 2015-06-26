""" mcscript_task -- task control utility functions

    Meant to be loaded as part of mcscript.  Provides the
    mcscript.task.* definitions in mcscript.

    Globals: requires attributes of mcscript.run to be populated 

    Environment variables:
      TASK_PHASE -- phase (0-based) for tasks to be executed
      TASK_POOL -- named pool for tasks to be executed (or ALL)
      TASK_TOC -- flag to request generation of TOC file
      TASK_STDOUT -- flag to request diagnostic dump of output to terminal
      TASK_COUNT_LIMIT -- flag to request generation of TOC file
      TASK_START -- starting value for task index (or offset for job rank in epar mode)

    Created by M. A. Caprio, University of Notre Dame.
    3/2/13 (mac): Originated as task.py.
    5/28/13 (mac): Updated to recognize ScriptError exception.
    6/5/13 (mac): Absorbed into mcscript package.
    11/1/13 (mac): Add local archive dir in scratch to help circumvent home space overruns.
    1/22/14 (mac): Python 3 update.
    7/3/14 (mac): Add generic archiving support.
    5/14/15 (mac): Insert "future" statements and convert print to write
        for Python 2 legacy support.  Upgrade string formatting to
        Python 2.7 format method.
    6/4/15 (mac): Add check for locking clashes.
    6/25/15 (mac): Simplify task interface to single init() function.
    Last modified 6/25/15 (mac).

"""

from __future__ import print_function, division

import sys
import os
import time
import glob

# Circular import:
#   Should load after mcscript base definitions and utilities are already loaded.
import mcscript


################################################################
# global storage
################################################################

# task management storage
task_list = []
phase_handlers = []
phases = 0
archive_phase_handlers = []
archive_phases = 0

task_index = None
task = None

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
    """

    global phase, pool, task_count_limit, task_start, make_toc, do_unlock
    global task_root_dir, flag_dir, output_dir, results_dir, archive_dir

    if "TASK_PHASE" in os.environ:
        phase = int(os.environ["TASK_PHASE"])
    else:
        # default to 0th phase -- natural default when tasks only have single-phase
        phase = 0

    if "TASK_POOL" in os.environ:
        pool = os.environ["TASK_POOL"]
    else:
        pool = None

    if "TASK_COUNT_LIMIT" in os.environ:
        task_count_limit = int(os.environ["TASK_COUNT_LIMIT"])
    else:
        task_count_limit = None

    task_start = int(os.environ.get("TASK_START","0"))

    make_toc = ("TASK_TOC" in os.environ)
    do_unlock = ("TASK_UNLOCK" in os.environ)
    ##make_archive = ("TASK_ARCHIVE" in os.environ)

    # task directories
    flag_dir = os.path.join(mcscript.run.work_dir,"flags")
    output_dir = os.path.join(mcscript.run.work_dir,"output")
    results_dir = os.path.join(mcscript.run.work_dir,"results")
    archive_dir = os.path.join(mcscript.run.work_dir,"archive")
    task_root_dir = mcscript.run.work_dir

################################################################
# directory setup
################################################################

def make_task_dirs ():
    """ make_task_dirs () ensures the existence of special subdirectories for task processing

    TODO: since existence check is not robust against multiple scripts
    attempting in close succession, replace this with a try/except.
    """

    if ( not os.path.exists(flag_dir)):
        os.mkdir(flag_dir)

    if ( not os.path.exists(output_dir)):
        os.mkdir(output_dir)

    if ( not os.path.exists(results_dir)):
        os.mkdir(results_dir)

    if ( not os.path.exists(archive_dir)):
        os.mkdir(archive_dir)

################################################################
# generic archiving support
################################################################


def write_current_toc ():
    """ Write current table of contents to file runxxxx.toc.

    Returns filename, sans path, as convenience to caller.
    """
    
    # write current toc
    toc_relative_filename = "{}.toc".format(mcscript.run.name)
    toc_filename = os.path.join(task_root_dir,toc_relative_filename)
    toc_stream = open(toc_filename, "w")
    toc_stream.write(task_toc())
    toc_stream.close()

    # return filename 
    return toc_relative_filename


def archive_handler_generic ():
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
    archive subdiretory rather than batch subdirectory.


    Returns archive filename.  For convenience of calling function if
    wrapped in larger task handler.

    """
    
    # write current toc
    toc_filename = write_current_toc()

    # make archive -- whole dir
    work_dir_parent = os.path.join(task_root_dir,"..")
    archive_filename = os.path.join(
        mcscript.task.archive_dir,
        "{:s}-archive-{:s}.tgz".format(mcscript.run.name, mcscript.date_tag())
        )
    filename_list = [
        os.path.join(mcscript.run.name,toc_filename),
        os.path.join(mcscript.run.name,"flags"),
        os.path.join(mcscript.run.name,"output"),
        os.path.join(mcscript.run.name,"batch"),
        os.path.join(mcscript.run.name,"results")
        ]
    mcscript.call(
        ["tar", "zcvf", archive_filename ] + filename_list,
        cwd=work_dir_parent,check_return=True
        )

    # copy archive out to home results archive directory
    ## mcscript.call(["cp","-v",archive_filename,"-t",ncsm_config.data_dir_results_archive], cwd=mcscript.task.results_dir)

    ## # put to hsi
    ## hsi_subdir = "2013"
    ## hsi_arg = "lcd %s; cd %s; put %s" % (os.path.dirname(archive_filename), hsi_subdir, os.path.basename(archive_filename))
    ## subprocess.call(["hsi",hsi_arg])

    return archive_filename

################################################################
# recall functions
################################################################

def index_str (index):
    """ index_str() formats a task index as %04d, or passes through other strings
    for special purposes (e.g., ARCH).
    """
    if (type(index) == int):
        return format(index,"04d")
    else:
        return str(index)

def task_toc ():
    """ task_toc() returns a status report as a newline-delimited string.
    """

    lines = [
        "Run: {:s}".format(mcscript.run.name),
        "{:s}".format(time.asctime()),
        "Tasks: {:d}".format(len(task_list)),
        "Archive phases: {:d}".format(archive_phases)
        ]
    for index in range(len(task_list)):
        task = task_list[index]
        # TODO: align on length of longest pool: format(task["pool"],"12s")
        if ((pool == None) or (pool == "ARCH") or (task["pool"] == pool)):
            fields = [ index_str(index), task["pool"]]
            fields += [task_status(index,phase) for phase in range(phases)]
            fields += [ task["descriptor"] ]
            lines.append(mcscript.spacify(fields))

    return "\n".join(lines)

def task_unlock ():
    """ task_unlock() removes all lock and fail flags.
    """
    
    flag_files = glob.glob(os.path.join(flag_dir,"task*.lock")) + glob.glob(os.path.join(flag_dir,"task*.fail"))
    print("Removing lock/fail files:", flag_files)
    for flag_file in flag_files:
        os.remove(flag_file)

def task_flag_base (index, phase):
    """ task_flag_base(index, phase) returns the flag file basename for the given
    phase of the given task.
    """

    return os.path.join(flag_dir,"task-{:s}-{:d}".format(index_str(index),phase))

def task_output_filename (index, phase):
    """ task_output_filename(index, phase) returns the output redirection filename for the given
    phase of the given task.
    """

    return os.path.join(output_dir,"task-{:s}-{:d}.out".format(index_str(index),phase))

def task_status (index, phase):
    """ task_status(index, phase) returns "-", "L", "F", or "X" to indicate whether the given
    phase of the given task is pending, locked, failed, or done.
    """

    flag_base =  task_flag_base(index,phase)
    if ( os.path.exists(flag_base + ".lock") ):
        return "L"
    elif ( os.path.exists(flag_base + ".fail") ):
        return "F"
    elif ( os.path.exists(flag_base + ".done") ):
        return "X"
    elif ( not task_list[index]["mask"] ):
        return "."
    else:
        return "-"


################################################################
# task invocation functions
################################################################

def seek_task ():
    """ seek_task() sets task_index and task to indicate the next task
    to be executed in the current phase, or else sets both to None.

    Returns True if eligible task found, False if not.
    """

    global task_index, task

    # select tasks in given pool
    # (or all pools if pool is ALL)
    pool_task_indices = [
        index
        for index in range(len(task_list))
        if ((task_list[index]["pool"] == pool) or (pool == "ALL"))
        ]
    ## DEBUG: print pool_task_indices

    # look through pool for next task
    if (mcscript.run.parallel_epar != -1):
        if (mcscript.run.epar_rank is None):
            print("Invalid rank None encountered in epar mode...")
            sys.exit(1)
        min_task_index = task_start + mcscript.run.epar_rank
        max_task_index = task_start + mcscript.run.epar_rank
    else:
        if (task_index == None):
            min_task_index = task_start
        else:
            min_task_index = task_index + 1
        max_task_index = len(task_list) - 1
    task_index = None
    for index in pool_task_indices:
        # only search forward (to avoid excessive lock file requests)
        if (index < min_task_index):
            continue
        # don't overrun any given limit on task index
        if (index > max_task_index):
            break
        
        # skip if task locked or done
        ##DEBUG: print(index, phase), task_status(index, phase)
        if ( task_status(index, phase) != "-" ):
            ## print "Skipping", (index,phase), task_status(index, phase)
            continue

        # skip if prior phase not completed
        if (phase > 0):
            if ( task_status(index, phase-1) != "X" ):
                print("Missing prerequisite", task_flag_base(index, phase-1))
                continue

        # designate this task as the one to do
        task_index = index
        break

    # return emptyhanded if no task found
    if task_index is None:
        task = None
        return False
    
    # store corresponding task dictionary
    task = task_list[task_index]

    # return success
    return True

def do_task ():
    """ do_task() --> time sets up a task/phase, calls its handler, and closes up
    
    The current working directory is changed to the task directory.
    A lock file is created for the task and phase.
    The phase handler is called.
    The current working directory is changed back up one level (presumably to the run scratch directory).
    The lock file for the task and phase is changed into a completion file.
    """

    # store corresponding task dictionary
    task = task_list[task_index]


    # lock task
    flag_base = task_flag_base(task_index, phase)
    # preliminary lock
    lock_stream = open(flag_base+".lock", "w")
    lock_stream.write(mcscript.run.job_id)
    lock_stream.close()
    # make sure lock was successful
    if (mcscript.run.batch_mode):
        # only need to worry about locking clash when jobs start simultaneously in batch mode
        wait_time = 3
        time.sleep(wait_time)
        lock_stream = open(flag_base+".lock", "r")
        line = lock_stream.readline()
        lock_stream.close()
        if (line == mcscript.run.job_id):
            print("Lock was apparently successful...")
        else:
            print("Locking clash: Current job is {} but lock file is from {}.  Yielding lock.".format(mcscript.run.job_id,line))
            raise mcscript.ScriptError("Yielding lock to other instance")
    # full lock
    lock_stream = open(flag_base+".lock", "w")
    lock_stream.write("{}\n".format(flag_base))
    lock_stream.write("pool {} descriptor {}\n".format(task["pool"],task["descriptor"]))
    lock_stream.write("job_id {} epar_rank {}\n".format(mcscript.run.job_id,mcscript.run.epar_rank))
    lock_stream.write("{}\n".format(time.asctime()))
    lock_stream.close()

    # set up task directory
    task_dir = os.path.join(task_root_dir, "task-{:04d}.dir".format(task_index))
    if ( not os.path.exists(task_dir)):
        os.mkdir(task_dir)
    os.chdir(task_dir)

    # initiate timing
    task_start_time = time.time()

    # set up output redirection
    redirect_stdout = not ("TASK_NOREDIRECT" in os.environ)
    output_filename = task_output_filename (task_index, phase)
    # purge any old file -- else it may persist if current task aborts
    if (os.path.exists(output_filename)):
        os.remove(output_filename)
    if (redirect_stdout):
        print("Redirecting to", output_filename)
        saved_stdout = sys.stdout
        sys.stdout = open(output_filename, "w")

    # generate header for task output file
    print(64*"-")
    print("task", task_index, "phase", phase)
    print(task["descriptor"])
    print(64*"-")
    print(mcscript.run_data_string())
    print(mcscript.time_stamp())
    print(64*"-")
    print()
    sys.stdout.flush()

    # invoke task handler
    try:
        phase_handlers[phase](task)
    except mcscript.ScriptError as err:
        # on failure, flag failure and propagate exception so script terminates
        print("ScriptError:", err)
        os.rename(flag_base+".lock",flag_base+".fail")
        raise

    # undo output redirection
    sys.stdout.flush()
    if (redirect_stdout):
        sys.stdout.close()
        sys.stdout = saved_stdout

    # process timing
    task_end_time = time.time()
    task_time = task_end_time - task_start_time

    # process lock file to done file
    lock_stream = open(flag_base+".lock", "a")
    lock_stream.write("{}\n".format(time.asctime()))
    lock_stream.write("{:.2f}\n".format(task_time))
    lock_stream.close()
    os.rename(flag_base+".lock",flag_base+".done")

    # cd back to task root directory
    os.chdir(task_root_dir)

    return task_time

def do_archive ():
    """ do_archive() --> time sets up the archive task/phase, calls its handler, and closes up
    
    The phase handler is called.
    """

    # lock task
    # CAVEAT: file system asynchrony (?) or simultaneus running of
    # different archive phases can cause trouble with tar archiving,
    # if tar senses lock file appearing or disappearing during
    # archiving of flags directory -- results in exit with failure code
   
    task_index = "ARCH"
    flag_base = task_flag_base(task_index, phase)
    lock_stream = open(flag_base+".lock", "w")
    lock_stream.write("{}\n".format(flag_base))
    lock_stream.write("---\n")
    lock_stream.write("{} {}\n".format(mcscript.run.job_id,"---"))
    lock_stream.write("{}\n".format(time.asctime()))
    lock_stream.close()

    # initiate timing
    task_start_time = time.time()

    # handle task
    # with output redirection
    saved_stdout = sys.stdout
    output_filename = task_output_filename (task_index, phase)
    print("Redirecting to", output_filename)
    sys.stdout = open(output_filename, "w")
    archive_phase_handlers[phase]()
    sys.stdout = saved_stdout
    
    # process timing
    task_end_time = time.time()
    task_time = task_end_time - task_start_time

    # process lock file to done file
    lock_stream = open(flag_base+".lock", "a")
    lock_stream.write("{}\n".format(time.asctime()))
    lock_stream.write("{:.2f}\n".format(task_time))
    lock_stream.close()
    os.rename(flag_base+".lock",flag_base+".done")

    # cd back to task root directory
    os.chdir(task_root_dir)

    return task_time


################################################################
# task master function
################################################################

def task_master():
    """ task_master() performs a master task execution loop, acting on the given phase and pool.
    """
    global task_index

    # task general initialization
    task_read_env()
    
    # task directory setup
    make_task_dirs()

    # special case handlers
    
    if (make_toc):
        print()
        print(task_toc())
        return

    if (do_unlock):
        task_unlock()
        return

    # configure pool
    
    if (pool == None):
        print("No pool specified -- using None.")

    if (pool == "ARCH"):
        do_archive()
        return

    # epar diagnostics

    if (mcscript.run.parallel_epar != -1):
        print("In epar task_master ({:d})...".format(mcscript.run.epar_rank))
        sys.stdout.flush()

    # main loop
    task_count = 0
    loop_start_time = time.time()
    task_time = 0.
    while (True):

        # check limits
        if (not ( (task_count_limit is None) or (task_count < task_count_limit) ) ):
            print("Reached task count limit.")
            break

        # check remaining time
        loop_elapsed_time = time.time() - loop_start_time
        remaining_time = mcscript.run.wall_time_sec - loop_elapsed_time
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
        if (not seek_task()):
            print("Found no available tasks in pool", pool)
            break

        # display diagnostic header for task
        #     this goes to global (unredirected) output
        print(64*"-")
        print("task", task_index, "phase", phase)
        print(task["descriptor"])
        print(64*"-")
        sys.stdout.flush()


        # execute task (with timing)
        task_time = do_task()
        print("(Task time: {:.2f} sec)".format(task_time))

        # tally
        task_count += 1



################################################################
# caller interface
################################################################

def init(
        tasks,
        task_descriptor=(lambda task : None),
        task_pool=(lambda task : None),
        task_mask=(lambda task : True),
        phase_handler_list=[],
        archive_handler_list=[]
):
    """Stores the given list of tasks and postprocesses it, adding
    fields with values given by the given functions.

    The task "descriptor", "pool", and "mask" fields are set by invoking the given
    functions task_descriptor, task_pool, and task_mask, respectively, on each task.

    Also registers the phase handlers.  The number of phases is also
    set from the length of the phase handler list.

    Finally, invokes master task handling loop.
    """

    # process task list
    global task_list, phases
    task_list = tasks
    for index in range(len(task_list)):
        task_list[index]["descriptor"] = task_descriptor(task_list[index])
        task_list[index]["pool"] = task_pool(task_list[index])
        task_list[index]["mask"] = task_mask(task_list[index])

    # register phase handlers
    global phase_handlers, phases, archive_phase_handlers, archive_phases
    phase_handlers = phase_handler_list
    phases = len(phase_handlers)
    archive_phase_handlers = archive_handler_list
    archive_phases = len(archive_phase_handlers)

    # invoke master loop
    task_master()
