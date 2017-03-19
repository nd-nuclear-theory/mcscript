"""runex02.py -- multi-task example of hello world

   There are several ways you should try invoking this script, to have
   a chance to try out the range of possiblities...

   When you are writing and debugging the script, you might first do a
   do-nothing test run (for syntax only) on front end, just to make
   sure it doesn't crash in the setup phase, i.e., as it generates the
   task list:
   
       % qsubm ex02

   But, actually, probably at the same time you would print a table of
   contents of the tasks, still running on front end:

       % qsubm ex02 --toc

   To actually execute a task, you have to specify the task's pool.
   Tasks within a given pool should all require the same computing
   resources and take approximately the same amount of time.  Here,
   for instance, we try to run the tasks in the pool for inner planets
   ("inner"), still on front end:
   
       % qsubm ex02 --pool=inner --phase=0

   Now if you generate a table of contents again, you should see some
   tasks marked as completed:

       % qsubm ex02 --toc

            0000 inner X - Mercury
            0001 inner X - Venus
            0002 inner X - Earth
            0003 inner X - Mars
            0004 outer - - Jupiter
            0005 outer - - Saturn
            0006 outer - - Uranus
            0007 outer - - Neptune

   Once phase 0 is completed, we can run phase 1:

       % qsubm ex02 --pool=inner --phase=1
       % qsubm ex02 --toc

            0000 inner X X Mercury
            0001 inner X X Venus
            0002 inner X X Earth
            0003 inner X X Mars
            0004 outer - - Jupiter
            0005 outer - - Saturn
            0006 outer - - Uranus
            0007 outer - - Neptune

   What if we try to do the second phase of the outer planet tasks now?

       % qsubm ex02 --pool=outer --phase=1

            Missing prerequisite /scratch/runs/runex02/flags/task-0004-0
            Missing prerequisite /scratch/runs/runex02/flags/task-0005-0
            Missing prerequisite /scratch/runs/runex02/flags/task-0006-0
            Missing prerequisite /scratch/runs/runex02/flags/task-0007-0

   The script will skip over all of them, since phase 0 was not
   completed for these tasks.  We have to do phase 0 first, then we
   can do phase 1...

       % qsubm ex02 --pool=outer --phase=0
       % qsubm ex02 --pool=outer --phase=1
       % qsubm ex02 --toc

            0000 inner X X Mercury
            0001 inner X X Venus
            0002 inner X X Earth
            0003 inner X X Mars
            0004 outer X X Jupiter
            0005 outer X X Saturn
            0006 outer X X Uranus
            0007 outer X X Neptune

   If you are on a cluster, on the other hand, you can go ahead and
   run these jobs on some appropriate queue, with some time limit (the
   details are cluster specific), for instance:
   

   Note:

      -- task standard output is always redirected to directory named
      output

      -- task completion logs are saved to directory flags

      -- task runs in working directory task-nnnn.dir

  M. A. Caprio
  Department of Physics
  University of Notre Dame

  1/8/17 (mac): Add renamed results file.  Rename to runex02.py.
  1/20/17 (mac): Add second phase to example.
  3/16/17 (mac): Add generic archive handler.
  3/18/17 (mac): Update to use task descriptor from metadata record.

"""

# generic packages for use below
import math
import sys

# load mcscript
# -- parse environment for various script parameters
#    (e.g., are we in batch mode? are we supposed to run certain tasks?)
# -- do basic run setup
#    (e.g., make working directory in scratch space)
# -- make available some functions for use in script
#    (including mcscript utility functions and mcscript.task task management)
import mcscript
mcscript.init()

##################################################################
# build task list
##################################################################

# configuration

worlds = [
    "Mercury", "Venus", "Earth", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune"
]

# generate task list

# This should be a list of dictionaries, with keys that your task
# handler function will understand.  Then, mcscript will automatically
# add some extra keys to these dictionaries, e.g., a task identifier
# name.

tasks = [
    {
        "world_name" : world_name
    }
    for world_name in worlds
]

##################################################################
# metadata functions
#
# These provide annotations to each task, based on the parameters.
##################################################################

def task_descriptor_world(task):
    """ Return task descriptor for hello/goodbye task.
    """

    return "{world_name}".format(**task)

def task_pool_world(task):
    """ Create task pool identifier.
    """
    
    if (task["world_name"] in ["Mercury", "Venus", "Earth", "Mars"]):
        pool = "inner"
    else:
        pool = "outer"
        
    if (task["world_name"]=="Pluto"):
        raise(ValueError("no longer a valid world name"))

    return pool

##################################################################
# implementation functions for doing a "hello/goodbye world" task
#
# For a more complicated application, you would separate these out
# into their own module.
##################################################################

def say_hello(task):
    """ Do a hello world task  given current task parameters.

    Expected dictionary keys:

    "world_name" : name of world to greet

    """

    # write greeting message to file
    mcscript.utils.write_input(
        "hello.txt",
        input_lines=[
            "Dear {world_name},".format(**task),
            "   Hello!",
            "Your script",
            mcscript.parameters.run.name
            ]
        )

    # save results file to common results directory
    print("Saving renamed output file...")
    results_filename = "{}-hello-{:s}.txt".format(mcscript.parameters.run.name,task["metadata"]["descriptor"])
    mcscript.call(
        [
            "cp",
            "--verbose",
            "hello.txt",
            results_filename
        ]
    ) 
    mcscript.call(
        [
            "cp",
            "--verbose",
            results_filename,
            "--target-directory={}".format(mcscript.task.results_dir)
        ]
    )

def say_goodbye(task):
    """Do a goodbye world task given current task parameters.

    We are using this as an example of a second (well, first) "phase"
    of a calculation, which should only be attempted if the first
    (well, zeroth) "phase" has been flagged as having successfully
    completed.

    Expected dictionary keys:

    "world_name" : name of world to greet

    """

    # write greeting message to file
    mcscript.utils.write_input(
        "goodbye.txt",
        input_lines=[
            "We have already said hello, {world_name},".format(**task),
            "and now it is time to say goodbye."
            ]
        )

    # save results file to common results directory
    print("Saving renamed output file...")
    results_filename = "{}-goodbye-{:s}.txt".format(mcscript.parameters.run.name,task["metadata"]["descriptor"])
    mcscript.call(
        [
            "cp",
            "--verbose",
            "goodbye.txt",
            results_filename
        ]
    ) 
    mcscript.call(
        [
            "cp",
            "--verbose",
            results_filename,
            "--target-directory={}".format(mcscript.task.results_dir)
        ]
    )

##################################################################
# master loop
##################################################################

mcscript.task.init(
    tasks,
    task_descriptor=task_descriptor_world,
    task_pool=task_pool_world,
    phase_handler_list=[say_hello,say_goodbye],
    archive_phase_handler_list=[mcscript.task.archive_handler_generic]
    )

################################################################
# termination
################################################################

mcscript.termination()
