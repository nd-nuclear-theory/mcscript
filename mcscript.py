""" mcscript.py -- scripting setup, utilities, and task control for cluster runs 

  Environment setup
  
  Scripts which use mcscript should be launched using the qsubm
  utility.  This utility requires several configuration variables,
  with names of the form "QSUBM_*", to be defined in the environment.
  These variables are documented in the qsubm online help message.
  See also example definitions below.

  The Python interpreter which is running the job script must be
  able to find mcscript and its subsidiary modules.  It will therefore
  typically be necessary to set the environment variable PYTHONPATH to
  reflect this.

  A typical setup in a .cshrc initialization file would be:

    # configure python
    module load python
    module load mpi4py

    # mcscript/qsubm configuration
    # Note: this setenv PYTHONPATH appends to path defined above by module load mpi4py
    setenv PYTHONPATH ${HOME}/runs/mcscript:${PYTHONPATH}
    setenv QSUBM_RUN_HOME ${HOME}/runs
    setenv QSUBM_LAUNCH_HOME ${HOME}/runs
    setenv QSUBM_SCRATCH_HOME ${SCRATCH}/runs
    setenv QSUBM_RUN_PREFIX run

  Note that the Python interpreter which runs the job file may
  variously be running on the front end, a dedicated script node, or a
  compute node, depending on how the job is invoked.  Compute nodes
  may have poor access to the home filesystem, and even searching
  within the directory may be a slow process.  In such instances, it
  is therefore recommended (from hard experience) that the number of
  files in the directories in the Python search path be kept to a
  minimum, e.g., just the mcscript files.

  Local scripting setup

  It is also necessary to provide local definitions (i.e., specific to
  the local cluster and user) via the module file mcscript_local.py.
  The template file provided with this package should be modified as
  appropriate and placed in the Python search path (e.g., most simply,
  with the other mcscript files).

  Instructions for use in job script

  The mcscript package is meant to be called from a user's job file,
  written in Python, e.g., run0001.py.  To use the basic setup code
  and variable definitions provided by mcscript, the job file should
  start with

    import mcscript

  preferably as its first import statement.  This will automatically
  run the setup code.  At its end, the job script should then
  explicitly call the termination code

    mcscript.termination()

  The job script may then access various utility functions, e.g.,

    mcscript.call(["cat"],input_lines=["a","b"])

  The job script may also invoke mcscript's task management features,
  by first registering the tasks and handler functions, then invoking the main loop:
  
  mcscript.task.set_task_list(...)
  mcscript.task.set_phase_handlers(...)
  mcscript.task.task_master()

  Created by M. A. Caprio, University of Notre Dame.
  6/5/13 (mac): Derived from earlier job.py, script.py, task.py complex (2/13).
  1/22/14 (mac): Python 3 update.
  5/13/15 (mac): Insert "future" statements for Python 2 legacy support.
  Last modified 12/18/14 (mac).

"""

from __future__ import print_function, division

import sys
import os
import subprocess
import time

################################################################
# define global run parameter names -- STOPGAP
#
# For now, names must be defined globally so mcscript.local
# package can reference them when it is imported.  To be
# replaced with neater bundling in a separate object.
################################################################

## # basic run information
## run = None
## batch_mode = None
## launch_dir = None
## work_dir = None
## host_name = None
## 
## # job details
## job_file = None
## wall_time_sec = None
## 
## # optional parallel queue environment variables
## parallel_width = None
## parallel_depth = None
## parallel_pernode = None
## parallel_nodesize = None
## parallel_epar = None
## 
## # note: task-control environment variables are imported in
## # mcscript.task.init()


################################################################
# import subpackages
################################################################

# import utils -- directly into namespace
from mcscript_utils import *

# import local definitions subpackage
import mcscript_local as local

# import task subpackage
import mcscript_task as task


################################################################
# run parameters object
################################################################

class RunParameters(object):
    """ Object to bundle run parameters into common name space.

    Defines several variables based on information provided by qsubm
    through the environment:
    
        run: run identifier, provided in environment by qsubm, e.g.,
        run0001
    
        batch_mode: True if running in batch mode, False if running
        interactively, provided in environment by qsubm
    
        work_dir: scratch directory for run, e.g.,
        /scratch/mcaprio/runs/run0001

        launch_dir: directory in which run was launched (batch mode)
        or current working directory in which it is running
        (interactive), e.g., /home/mcaprio/runs/run0001

        job_file,wall_time_sec,parallel_width,parallel_depth,...: job
        information from qsubm.py

    Defines variables completed by invoking local customization code:

        job_id: batch system job id
    
        serial_prefix: command prefix for serial invocation 
        parallel_prefix: command prefixes for parallel invocation

        epar_rank: MPI rank in epar run

    """
    def __init__(self):
        
        ################################################################
        # environment information 
        ################################################################

        # basic run information
        self.name = os.environ["QSUBM_RUN"]
        self.batch_mode = (os.environ["QSUBM_RUN_MODE"] == "batch")
        self.launch_dir = os.environ["QSUBM_LAUNCH_DIR"]
        self.work_dir = os.environ["QSUBM_WORK_DIR"]
        self.host_name = os.environ["HOST"]

        # job details
        self.job_file = os.environ["QSUBM_JOB_FILE"]
        self.wall_time_sec = int(os.environ["QSUBM_WALL_SEC"])

        # optional parallel queue environment variables
        #   will be integers, potentially -1 if left as None in qsub call
        self.parallel_width = int(os.environ["QSUBM_WIDTH"])
        self.parallel_depth = int(os.environ["QSUBM_DEPTH"])
        self.parallel_pernode = int(os.environ["QSUBM_PERNODE"])
        self.parallel_nodesize = int(os.environ["QSUBM_NODESIZE"])
        self.parallel_epar = int(os.environ["QSUBM_EPAR"])

        # generate local definitions
        self.job_id = local.job_id()
        self.parallel_prefix = local.parallel_prefix(self)
        if (self.batch_mode):
            if (self.parallel_epar != -1):
                # set configuration so serial codes will launch locally under this
                # daughter process (presumably already on compute node)
                self.serial_prefix = local.serial_prefix("epar")
            else:
                # set configuration so serial codes will launch appropriately for
                # batch jobs at the present facility (perhaps on a separate
                # compute node if the job scripts run on dedicated nodes distinct
                # from the compute nodes)
                self.serial_prefix = local.serial_prefix("batch")
        else:
            # local run on front end
            self.serial_prefix = local.serial_prefix("local")

        # epar rank
        if (self.parallel_epar != -1):
            # load MPI machinery to determine rank
            from mpi4py import MPI
            comm = MPI.COMM_WORLD
            self.epar_rank = comm.Get_rank()
        else:
            self.epar_rank = None
            

        # verbosity level
        self.verbose = (
            not ("TASK_TOC" in os.environ)
            and not ("TASK_UNLOCK" in os.environ)
            )
        # adjust verbosity level for epar
        self.verbose = ( self.verbose and 
                        ((self.epar_rank == None) or (self.epar_rank == 1))
                        )

run = RunParameters()

################################################################
# diagnostic output
################################################################

def run_data_string():
    """ Generate multiline string documenting run variables for
    diagnostic output.
    """

    message = "\n".join(
        [
        ("Run: %s" % run.name),
        ("Job file: %s" % run.job_file),
        ("Job ID: %s" % run.job_id),
        ("Host name: %s" % run.host_name),
        ("Batch mode: %s" % run.batch_mode),
        ("Launch directory: %s" % run.launch_dir),
        ("Scratch directory: %s" % run.work_dir),
        ("Wall time (sec): %d" % run.wall_time_sec),
        ("Epar: %s" % run.parallel_epar)
        ]
        )

    return message


################################################################
# initialization code
################################################################

def init():
    """ Carry out run setup.
    """
    ################################################################
    # make and cd to scratch directory
    ################################################################

    # dependencies: in epar mode, this must come before launching
    # daughters, which require directory to already exist

    if (run.parallel_epar != -1):
        subprocess.call(["mkdir", "-p", run.work_dir])
    os.chdir(run.work_dir)

    ################################################################
    # invoke local configuration and setup tasks
    ################################################################

    local.init()

    ## ################################################################
    ## # handle embarassingly parallel relaunch -- SUPPLANTED
    ## ################################################################
    ## 
    ## if (parallel_epar_status == "parent"):
    ##     # launch epar daughters
    ##     print "Embarassingly parallel mode (launching daughters)..." 
    ##     sys.stdout.flush()   # needed so output doesn't get mixed with daughters
    ##     os.environ["QSUBM_EPAR"] = "daughter"
    ##     subprocess.call(mcscript.local.epar_args)
    ##     sys.stdout.flush()
    ##     print "Daughters returned..."
    ##     exit

    ################################################################
    # epar logging
    ################################################################

    if (run.parallel_epar != -1):

        # trap invalid epar situation
        if (not run.batch_mode):
            raise ValueError("parallel_epar: Cannot have embarassingly parallel mode in local run.")

        # flag embarassingly parallel daughter process
        print("Embarassingly parallel mode...")
        print("My rank is %d..." % run.epar_rank)
        sys.stdout.flush()
        

    ################################################################
    # summarize job information
    ################################################################

    if (run.verbose):
        print("")
        print("-"*64),
        print(run_data_string())
        print("-"*64),
        print(time_stamp()),
        sys.stdout.flush()

    ################################################################
    # basic OMP environment setup
    ################################################################

    openmp_setup()

################################################################
# termination code
#   to be invoked explicitly by job file
################################################################

def termination():
    # invoke local termination
    local.termination()
    # provide verbose ending
    #   only if top-level invocation of job file, not epar daughter
    if (run.verbose):
        sys.stdout.flush()
        print("-"*64)
        print("End script")
        print(time_stamp())
        print("-"*64)
    sys.stdout.flush()


################################################################
# OpenMP setup
################################################################

def openmp_setup(stack_size=None):
    """ Set OpenMP environment variables.

    stack_size: string for stack size (e.g., "16M"), or None
    """

    # set number of threads by global qsubm depth parameter
    os.environ["OMP_NUM_THREADS"] = str(run.parallel_depth)

    # set stack size
    if (stack_size != None):
        os.environ["OMP_STACKSIZE"] = stack_size
