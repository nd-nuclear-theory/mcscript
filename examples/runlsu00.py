#!/usr/bin/python3

""" runlsu00.py -- running lsu3shell, for multiple Nmax and JJ

    phase 1: LSU3shell diagonalization
    phase 2: SU(3) decomposition

    Generate table of contents on front end:

        qsubm lsu00 --toc

    Do small test run on front end (and limit it to just one task):

        qsubm lsu00 --pool=Nmax00 --width=1 --limit=1

    Do batch run:

        qsubm lsu00 regular 60 --pool=Nmax04 --width=1

    For comparison, for a larger parallel job with, say, 21 diagonal
    processes, on the NDCRC cluster, once would set the task parameter
    ndiag=21 below in the script, and invoke with something like the
    actual following command line used with my run0297:
   
        qsubm 0297 "*@@ivybridge" 240 --pool=Nmax06 --width=231 --nodesize=16 --start=4

    When all the tasks are done, you can make a nice tarball archive
    (in the archive subdirectory runlsu00/archive) with:

        qsubm lsu00 --archive

    Based on run0297.py.

"""

# generic packages for use below
import math
import sys

# load mcscript
import mcscript

# load lsu3shell application-specific definitions
import lsu3shell

##################################################################
# build task list
##################################################################

# nuclide parameters
nuclide = (2,2)
Nmax_list = [0,2,4]
twice_J_list = [0,2]

# Hamiltonian parameters
hw = 20
coulomb = True
aLawson = 50
interaction_short = "JISP16"
interaction_dir = "V_JISP16_bare_Jmax4"
interaction_name = "V_JISP16_bare_Jmax4_sq_10shl_hw20_vxx_r4_PNfmt_SU3_Nmax8_pshell"

# diagonalization parameters
eigenvectors = 5
ndiag = 1
lanczos = 100

# generate task list
tasks = [
    {
        # nuclide parameters
        "nuclide" : nuclide,
        "model_space" : lsu3shell.make_model_space_Nmax(nuclide,twice_J,Nmax),
        "twice_J" : twice_J,
        # Hamiltonian parameters
        "hw" : hw,
        "coulomb" : coulomb,
        "aLawson" : aLawson,
        "interaction_short" : interaction_short,
        "interaction_dir" : interaction_dir,
        "interaction_name" : interaction_name,
        # diagonalization parameters
        "eigenvectors" : eigenvectors,
        "lanczos" : lanczos,
        "ndiag" : ndiag,
        # executables
        "lsu3shell_executable" : "LSU3shell_MPI",
        "su3_decomposition_executable" : "ncsmSU3xSU2wfnDecomposition"
        }    
    # many-body-truncation
    for Nmax in Nmax_list
    for twice_J in twice_J_list
]

##################################################################
# master loop
##################################################################

mcscript.init()

mcscript.task.set_task_list(
    tasks,
    task_descriptor=lsu3shell.task_descriptor_lsu3shell_2,
    task_pool=lsu3shell.task_pool_model_space
    )
mcscript.task.set_phase_handlers(
    phase_handler_list=[
        lsu3shell.task_handler_lsu3shell,
        lsu3shell.task_handler_su3_decomposition
        ],
    archive_handler_list=[mcscript.task.archive_handler_generic]
    )
mcscript.task.task_master()

################################################################
# termination
################################################################

mcscript.termination()
