# qsubm local definition file

# NERSC
#
# Simple test of inline script submission:
#   qsub -q debug -l walltime=60 -
#   /bin/csh /global/homes/m/mcaprio/runs/mcscript/wrapper.csh echo hello world

# directly-invoked script cannot start with #!/usr/bin/python3 shebang,
# since that is not location of interpreter

import os

def submission (job_name,job_file,qsubm_path,environment_definitions,args):

    submission_args = [ "qsub" ]

    # job name
    submission_args += ["-N", "%s" % job_name]

    # queue
    submission_args += ["-q", "%s" % args.queue]

    # wall time 
    submission_args += ["-l", "walltime=%d:00" % args.wall]

    # parallel environment
##    if ( (not args.nopar) and not ( (args.width == 1) and (args.nodesize == None) ) ):
##        submission_args += ["-l", "mppwidth=%d" % args.width]
##        submission_args += ["-l", "mppdepth=%d" % args.depth]
    if (args.nopar):
        # true serial job
        pass
    elif ((args.width == 1) and (args.depth == 1)):
        # apparently this was also treated as a serial job, though I remember not why
        pass
    elif (args.epar is not None):
        # embarassingly parallel serial job
        submission_args += ["-l", "mppwidth=%d" % args.epar]
        # allow pernode specification on epar
        if (args.pernode is not None):
            submission_args += ["-l", "mppnppn=%d" % args.pernode]
    elif (args.depth == 1):
        # pure MPI parallel job
        submission_args += ["-l", "mppwidth=%d" % args.width]
    else:
        # OMP or hybrid MPI/OMP parallel job
        # the ad hoc hopper way
        #    https://www.nersc.gov/users/computational-systems/hopper/running-jobs/using-openmp-with-mpi/
        # Although "-l mppwidth=6 -l mppdepth=6 -l mppnppn=4" would seem to make sense, it fails with
        #    ['aprun', '-n6', '-d6', '-N4', '-S1', '-ss', ...]
        # giving error 
        #    apsched: claim exceeds reservation's memory
        # Must use recommended "-l mppwidth=36".
        #
        # The "proper-seeming" way (but fails)
        ## submission_args += ["-l", "mppwidth=%d" % args.width]
        ## submission_args += ["-l", "mppdepth=%d" % args.depth]
        ## pernode = args.nodesize / args.depth
        ## submission_args += ["-l", "mppnppn=%d" % pernode]

        submission_args += ["-l", "mppwidth=%d" % (args.width*args.depth)]


    # append user-specified arguments
    if (args.opt is not None):
        submission_args += args.opt.split(",")

    # force environment variable CRAY_ROOTFS=DSL
    #   enables access to shared object libraries (needed for Python on compute node)
    environment_definitions.append("CRAY_ROOTFS=DSL")
    
    # environment definitions
    submission_args += ["-v", "%s" % ",".join(environment_definitions)]

    # job command
    if (args.epar is not None):
        # embarassingly parallel serial job
        submission_args += [ "-" ]  # force qsub to read script from stdin
        if (args.pernode is not None):
            pernode_string = "-N%d" % args.pernode
        else:
            pernode_string = ""
        submission_string_entries = [
            "#!/bin/csh",
            "\n",
            "date",
            "\n",        
            "echo \"Entering epar qsub script...\"",
            "\n",  
            "aprun", # parallel relaunch
            "-axt",  # "-a xt" fails, try w/o space; really useful?
            "-n%d" % args.epar,
            "%s" % pernode_string,
            "-b", "/usr/bin/env",  # executable wrapper to launch on compute node
            # NOTE: must ensure this is correct python version
            "python", # call interpreter, so py file does not need to be executable
            job_file,
            "\n",
            "echo \"Exiting epar qsub script...\"",
            "\n",
            "date",
            "\n"        
            ]
        submission_string = " ".join(submission_string_entries)
    else:
        # plain serial or parallel job 
        submission_args += [ job_file ]
        submission_string = ""

    return (submission_args, submission_string)


