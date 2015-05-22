#!/usr/bin/env python3

"""runmfdn00.py -- running h2mixer + MFDn

    phase 1: constructing TBME files with h2mixer
    phase 2: running MFDn

    Note: It might be necessary to include a module load command, as
    in the commented-out example line (mcscript.module) below.

    Generate table of contents on front end:

       qsubm mfdn00 --toc

    Before you can run h2utils or mfdn, you need to do some setup.
    You need to make sure you have the requisite h2 interaction data
    files for this run.  You also need to edit mfdn_config.py so that
    the various configuration variables point to where all the
    necessary files (h2 files, mfdn executable, h2utils executables)
    are for *your* account.

    The first phase you might even run on the front end:

        qsubm mfdn00 --pool=Nmax04 --phase=1

    Here are some attempted diagonalization runs on the compute nodes
    at the ND CRC (not sure if these actually ran -- to check and update):

        qsubm mfdn00 short 60              --pool=Nmax04 --phase=1 --width=6 --nodesize=8 --start=0 --limit=1 --opt="-m ae"
        qsubm mfdn00 "*@@dqcneh_253GHz" 60 --pool=Nmax06 --phase=1 --width=6 --nodesize=8 --start=0 --limit=1 --opt="-m ae"
        qsubm mfdn00 "*@@ivybridge" 60     --pool=Nmax08 --phase=1 --width=15 --nodesize=16 --start=0 --limit=1 --opt="-m ae"
 
    Here are example runs on NERSC on Edison:

        qsubm mfdn00 debug 10 --pool=Nmax04 --phase=1 --width=15 --opt="-m ae"
    
    Based on run0305.py.

    The required data files for the Nmax04 were originally named:
  
        run0229/r2k2-HO-1.000-HO-1.000-5-6-r2.bin
        run0229/r2k2-HO-1.000-HO-1.000-5-6-r1r2.bin
        run0229/r2k2-HO-1.000-HO-1.000-5-6-k2.bin
        run0229/r2k2-HO-1.000-HO-1.000-5-6-k1k2.bin
        run0177/JISP16-HO-1.000-HO-1.000-ob-13-5-6-20.bin
        run0177/VC-HO-1.000-HO-1.000-ob-13-5-6-20.bin

    These may be found in the directory examples/mfdn-example-data.  This
    subdirectory (or a soft link thereto) should be placed in your h2
    data directory.

    Last modified 5/13/15 (mac).

"""

import math
import sys
import os
import shutil
import subprocess

import mcscript
import ncsm
import ncsm_config
import mfdn_v14_b06

################################################################
# module loads
################################################################

## mcscript.module(["load","mpich/3.0.4-pgi"])

################################################################
# general run configuration
################################################################

ncsm.set_run_search_lists(
    radial = [
        "131114"
    ],
    r2k2 = [
        "mfdn-example-data",  # minimal data needed for this example
        "run0229",  # HO/CS including halo   
        "run0244", "run0250"  # hybrid
    ],
    xform = [
        "mfdn-example-data",  # minimal data needed for this example
        "run0177", # standard HO hw 2.5 mesh   <<<< actually needed for this example
        "run0245", "run0251"  # hybrid
    ]
)

##################################################################
# task list builder
##################################################################

# nuclide parameters
nuclide = (2,2)
Nv = 1 # target Hamiltonian valence shell 

# Hamiltonian parameters
interaction = "JISP16" 
coulomb = True
aLawson = 20
hwLawson_list = [ None ]

# basis parameters
hw_int_list = None  # None = use hw for hw_int
hw_int_coul = 20.
radial_basis_pair_list = [ ("HO","HO")  ]
traditional_ho = True
## hw_log_range = mcscript(10,40,8)  
## hw_list = mcscript.log_range(*hw_log_range)
##hw_list = mcscript.value_range(10,40,5)
hw_list = [20.]
beta_ratio_log_range = (1.0,1.0,1)
beta_ratio_list = mcscript.log_range(*beta_ratio_log_range,power=0.5)
Nmax_start = 4
Nmax_limit = 12
Nstep = 2
Nmax_list = mcscript.value_range(Nmax_start,Nmax_limit,2)
xform_cutoff_list = [
    ("ob", N1b_cut)
    for N1b_cut in mcscript.value_range(13,13,2)
    ]  

# diagonalization
twice_mj = 0
eigenvectors = 10
initial_vector = -2
lanczos = 500
tolerance = 0

# obdme parameters
## obdme_reference_state_list = [
##     (JJ,0,i)
##     for JJ in mcscript.value_range(1,3,2)
##     for i in mcscript.value_range(1,2,1)
##     ]
obdme_reference_state_list = []
obdme_twice_multipolarity = 4

# version parameters
mfdn_executable = "version14-beta06-newmake/xmfdn-h2-lan"
mfdn_wrapper = mfdn_v14_b06.call_mfdn_h2

# generate task list
tasks = [
    {
        # nuclide parameters
        "nuclide" : nuclide,

        #Hamiltonian parameters
        "interaction" : interaction,
        "coulomb" : coulomb,
        "aLawson" : aLawson,
        "hwLawson" : mcscript.auto_value(hwLawson,hw),
        
        # basis parameters
        "hw_int" : hw_int,  # hw of source interaction
        "hw_int_coul" : hw_int_coul,  # hw of coulomb interaction
        "hw" : hw,  # logical hw, for scaling basis
        "basis" :  # logical basis, to be scaled by hw
        (
            radial_basis_p,
            1.,
            radial_basis_n,
            beta_ratio
            ),
        "scaled_basis" :  # deduced basis used in task descriptor, etc.
        (
            radial_basis_p,
            ncsm.beta_for_hw(hw_int,hw),
            radial_basis_n,
            ncsm.beta_for_hw(hw_int,hw)*beta_ratio
            ),
        "xform_cutoff" : xform_cutoff,
        "xform_cutoff_coul" : xform_cutoff,
        "Nmax" : Nmax,
        "Nstep" : Nstep,
        "Nv" : Nv,

        # diagonalization parameters
        "2mj" : twice_mj,
        "eigenvectors" : eigenvectors,
        "initial_vector" : initial_vector,   
        "lanczos" : lanczos,
        "tolerance" : tolerance,

        # obdme parameters
        "obdme_reference_state_list" : obdme_reference_state_list,
        "obdme_twice_multipolarity" : obdme_twice_multipolarity,
        "traditional_ho" : traditional_ho,

        # version parameters
        "mfdn_executable" : mfdn_executable,
        "mfdn_wrapper" : mfdn_wrapper

        }    
    # many-body-truncation
    for Nmax in Nmax_list
    # unit basis
    for (radial_basis_p, radial_basis_n) in radial_basis_pair_list
    for beta_ratio in beta_ratio_list
    # scaling
    for hw in hw_list
    # Lawson
    for hwLawson in hwLawson_list 
    # source xform
    for hw_int in mcscript.auto_value(hw_int_list,[hw])
    for xform_cutoff in xform_cutoff_list
]

##################################################################
# task postprocessing functions
##################################################################

def task_pool (current_task):
    return "Nmax{Nmax:02d}".format(**current_task)

def task_mask (current_task):
    ##    return (
    ##        mcscript.approx_gtr_equal(current_task["hw"],10.,0.1)
    ##        and
    ##        (
    ##            ( current_task["Nmax"] <= 8 )
    ##            or
    ##            (
    ##                ( current_task["xform_cutoff"] == ("ob", 13) )
    ##                ## and
    ##                ## ( current_task["basis"][3] < 1.4 )
    ##                )
    ##            )
    ##        )
    return True

##################################################################
# master loop
##################################################################

mcscript.task.set_task_list(
    tasks,
    task_descriptor=ncsm.task_descriptor_format_5,
    task_pool=task_pool,
    task_mask=task_mask
    )
mcscript.task.set_phase_handlers(
    phase_handler_list=[
        ncsm.task_handler_h2mixer,
        ncsm.task_handler_mfdn_h2
        ],
    archive_handler_list=[
        ncsm.archive_handler_mfdn_res_only,
        ncsm.archive_handler_mfdn_archive
        ]
    )
mcscript.task.task_master()

################################################################
# termination
################################################################

mcscript.termination()
