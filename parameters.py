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
  + 3/18/17 (mac):
    - Revise to support updated hybrid run parameters.
    - Move run parameters object instantiation back into this module.

"""

import os

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

        # environment definitions: serial run parameters
        self.serial_threads = int(os.environ["MCSCRIPT_SERIAL_THREADS"])

        # environment definitions: hybrid run parameters
        self.hybrid_nodes = int(os.environ["MCSCRIPT_HYBRID_NODES"])
        self.hybrid_ranks = int(os.environ["MCSCRIPT_HYBRID_RANKS"])
        self.hybrid_threads = int(os.environ["MCSCRIPT_HYBRID_THREADS"])
        self.hybrid_nodesize = int(os.environ["MCSCRIPT_HYBRID_NODESIZE"])

        # generate local definitions
        #
        # To be provided by local configuration init.
        self.job_id = None

        # verbosity level
        #
        # Note: may want to reduce for toc and unlock runs
        self.verbose = True

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
                "Wall time: {} sec (={:.2f} min)".format(self.wall_time_sec,self.wall_time_sec/60)
            ]
            )

        return message

# instantiate, but don't populate, since qsubm won't have needed variables in environment
run = RunParameters()
