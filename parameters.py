""" parameters.py -- read runtime environment for mcscript

  Language: Python 3

  M. A. Caprio
  Department of Physics, University of Notre Dame

  + 6/13/16 (mac): Extracted from mcscript.py as submodule environment.py.
  + 11/22/16 (mac):
    - Rename to parameters.py.
    - Move run_data_string into RunParameters as method.
    - Eliminate load-time construction of global run object.
  + 1/16/17 (mac): Add support for serial_threads attribute.

"""

import os

import mcscript.config as config
import mcscript.utils as utils

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


    Example usage:
        run = mcscript.RunParameters()
        print(run.run_data_string())

    """
    def __init__(self):
        """ Create empty run parameters."""
        pass

    def populate(self):
        
        ################################################################
        # environment information 
        ################################################################

        # basic run information
        self.name = os.environ["MCSCRIPT_RUN"]
        self.run_mode = os.environ["MCSCRIPT_RUN_MODE"]
        self.batch_mode = (os.environ["MCSCRIPT_RUN_MODE"] == "batch")
        self.launch_dir = os.environ["MCSCRIPT_LAUNCH_DIR"]
        self.work_dir = os.environ["MCSCRIPT_WORK_DIR"]
        self.host_name = os.environ["HOST"]

        # job details
        self.job_file = os.environ["MCSCRIPT_JOB_FILE"]
        self.wall_time_sec = int(os.environ["MCSCRIPT_WALL_SEC"])

        # optional parallel queue environment variables
        #   will be integers, potentially -1 if left as None in qsub call
        self.serial_threads = int(os.environ["MCSCRIPT_SERIALTHREADS"])
        self.parallel_width = int(os.environ["MCSCRIPT_WIDTH"])
        self.parallel_depth = int(os.environ["MCSCRIPT_DEPTH"])
        self.parallel_spread = int(os.environ["MCSCRIPT_SPREAD"])
        ## self.parallel_pernode = int(os.environ["MCSCRIPT_PERNODE"])
        self.parallel_nodesize = int(os.environ["MCSCRIPT_NODESIZE"])
        self.parallel_epar = int(os.environ["MCSCRIPT_EPAR"])
        if (self.parallel_epar!=-1):
            raise(ValueError("mcscript: embarassingly parallel mode not currently supported"))

        # generate local definitions
        self.job_id = config.job_id()

        # verbosity level
        self.verbose = (
            not ("TASK_TOC" in os.environ)
            and not ("TASK_UNLOCK" in os.environ)
            )

        ## # adjust verbosity level for epar
        ## self.verbose = ( self.verbose and 
        ##                 ((self.epar_rank == None) or (self.epar_rank == 1))
        ##                 )

    def run_data_string(self):
        """ Generate multiline string documenting run variables for
        diagnostic output.

        Returns:
            (str): diagnostic string
        """

        message = "\n".join(
            [
            "Run: {}".format(self.name),
            "Job file: {}".format(self.job_file),
            "Job ID: {}".format(self.job_id),
            "Host name: {}".format(self.host_name),
            "Batch mode: {}".format(self.batch_mode),
            "Batch launch directory: {}".format(self.launch_dir),
            "Work directory: {}".format(self.work_dir),
            "Wall time (sec): {}".format(self.wall_time_sec)
            ]
            )

        return message
