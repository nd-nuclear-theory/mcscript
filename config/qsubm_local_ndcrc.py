""" qsubm_local.py -- local definitions for qsubm

    Version for NDCRC.

    NDCRC: To select hardware via pe request, set nodesize.  Then,
    optionally, specify width/depth.  These determine node reservation
    via pe request, plus they are passed to run script via environment
    to allow determination of MPI/OMP parameters.

    Wall time is not communicated in queue request but is passed on to script.

    Note: Currently only support mpi environment, not smp environment.

    EX: MPI on HPC cluster (8-core)

        qsubm 0290 long 1440 --width=231 --nodesize=8 --pool=Nmax06

    EX: OpenMP on any available 12-core cluster (12-core)

        qsubm 0298 long --depth=12 --nodesize=12 --pool=Nmax06 

    EX: default single core request on long cluster (12-core),
    script MPI call uses default width 1

        qsubm 0291 long 30 --pool=Nmax04
        
    Language: Python 3
    Mark A. Caprio
    University of Notre Dame
    Written ~7/13 (mac).
    Last modified 12/18/14 (mac).

"""

import os
import sys

def submission (job_name,job_file,qsubm_path,environment_definitions,args):
    """ Prepare submission command invocation.

    job_name : job name string
    
    job_file : job script file
    
    qsubm_path : path to qsubm files (for locating wrapper script)
    
    environment_definitions : list of environment variable definitions
    to include in queue submission arguments

    args : qsub's argument parser return structure (contains lots of
    parameters)

    Returns tuple (submission_args, submission_string): list of
    arguments for subprocess.call and string giving standard input for
    subprocess.
    """

    submission_args = [ "qsub" ]

    # job name
    submission_args += ["-N", "%s" % job_name]

    # queue
    submission_args += ["-q", "%s" % args.queue]

    # wall time
    pass  # enforced by queue

    # miscellaneous options
    submission_args += ["-j","y"]  # merge standard error
    submission_args += ["-r","n"]  # job not restartable
                        
    # parallel environment
    if (  not ( (args.epar is None) and (args.width == 1) and (args.depth == 1) and (args.nodesize == None) ) ):

        # check that nodesize was specified
        if (args.nodesize is None):
            print ("Please specify --nodesize for parallel run on NDCRC.")
            sys.exit(1)

        # calculate number of needed cores
        if (args.epar is not None):
            # epar -- serial or smp
            needed_cores = args.epar * args.depth
        else:
            # standars -- smp/mpi
            needed_cores = args.width * args.depth
        rounded_cores = args.nodesize * (needed_cores // args.nodesize)
        if ((needed_cores % args.nodesize) != 0):
            rounded_cores += args.nodesize

        # generate parallel environment specifier
        if (args.width != 1):
            # handle mpi run
            submission_args += ["-pe", "mpi-%d %d" % (args.nodesize, rounded_cores) ]
        elif (args.depth != 1):
            # handle smp run
            submission_args += ["-pe", "smp %d" % (args.nodesize) ]

    # append user-specified arguments
    if (args.opt is not None):
        submission_args += args.opt.split(",")

    # environment definitions
    submission_args += ["-v", "%s" % ",".join(environment_definitions)]

    # job command
    if (args.epar is not None):
        # embarassingly parallel serial job
        # TODO -- support smp on embarassingly parallel run
        submission_args += [
            os.path.join(qsubm_path,"wrapper.csh"),     # csh wrapper
            "mpiexec", # parallel relaunch
            "-n%d" % args.epar,
            ## "-b", "/usr/bin/env",  # executable wrapper to launch on compute node -- see if needed at NDCRC?
            "python", # call interpreter, so py file does not need to be executable
            job_file
            ]
    else:
        # plain non-epar job 
        submission_args += [
            os.path.join(qsubm_path,"wrapper.csh"),  # csh wrapper required at NDCRC
            "python", # call interpreter, so py file does not need to be executable
            job_file
            ]

    # stdin to qsubm
    submission_string = ""

    return (submission_args,submission_string)
