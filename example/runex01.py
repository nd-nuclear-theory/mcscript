#!/usr/bin/python3

""" runex01.py -- multi-task example of hello world

   There are several ways you should try invoking this script, to have
   a chance to try out the range of possiblities...

   When you are writing and debugging the script, you might first do a
   do-nothing test run (for syntax only) on front end, just to make
   sure it doesn't crash in the setup phase, i.e., as it generates the
   task list:
   
      qsubm ex01

   But, actually, probably at the same time you would print a table of
   contents of the tasks, still running on front end:

      qsubm ex01 --toc

   To actually execute a task, you have to specify the task's pool.
   Here, for instance, we try to run the tasks in pool "greet", still
   on front end:
   
      qsubm ex01 --pool=greet

   Now if you generate a table of contents again, you should see some
   tasks marked as completed:

      qsubm ex01 --toc

   If you are on a cluster, on the other hand, you can go ahead and
   run these jobs on some appropriate queue, with some time limit (the
   details are cluster specific), for instance:
   

   Note:

      -- task standard output is always redirected to directory named
      output

      -- task completion logs are saved to directory flags

      -- task runs in working directory task-nnnn.dir
      
      
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

worlds = ["Mercury", "Venus", "Earth", "Mars"]

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
# implementation functions for doing a "hello world" task
#
# For a more complicated application, you would separate these out
# into their own module.
##################################################################

def task_descriptor_hello(task):
    """ Return task descriptor for hello task.
    """

    return "{world_name}".format(**task)

def task_handler_hello(task):
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
            mcscript.run.name
            ]
        )


##################################################################
# task list entry annotation functions
##################################################################

def task_pool(task):
    """ Create task pool identifier.
    """
    
    return "greet"

##################################################################
# master loop
##################################################################

mcscript.task.init(
    tasks,
    task_descriptor=task_descriptor_hello,
    task_pool=task_pool,
    phase_handler_list=[task_handler_hello]
    )

################################################################
# termination
################################################################

mcscript.termination()
