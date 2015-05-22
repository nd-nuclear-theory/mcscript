""" lsu3shell.py -- lsu3shell task handlers for mcscript

  Created by M. A. Caprio, University of Notre Dame.
  6/11/14 (mac): Originated, based on ncsm_task.py.
  Last modified 6/11/14 (mac).

"""

import os
import sys
import subprocess
import glob
import time

import mcscript

################################################################
# model_space utilities
################################################################

def make_model_space_Nmax(nuclide,twice_J,Nmax,step=2):
    """ Makes full Nmax model space.

    nuclide: nuclide (Z,N)
    twice_J: 2J
    Nmax: Nmax
    step: optional, step in Nex

    Returns tuple (name,lines), of model space name and list of lines for model space file.
    """

    (Z,N) = nuclide

    # name
    name = "Nmax{:02d}".format(Nmax)
    
    # lines
    lines = [mcscript.spacify([Z, N, twice_J])]
    for Nex in range(Nmax%step,Nmax+1,step):
        lines.append(mcscript.spacify([Nex,"-1"]))

    return (name,lines)
    

################################################################
# lsu3shell: task descriptor
################################################################

def task_descriptor_lsu3shell_1 (current_task):
    """ Return task descriptor.

    Based on Tomas's naming convention
    EX: 9Be_V_JISP16_bare_Jmax4_sq_10shl_hw20_vxx_r4_PNfmt_SU3_Nmax8_pshell_hw20MeV_Nmax06_7
    """

    return "{nuclide_name}_{interaction_name}_hw{hw}MeV_{model_space[0]}_{twice_J}".format(**current_task)

def task_descriptor_lsu3shell_2 (current_task):
    """ Return task descriptor.

    Uses (Z,N) labeling, abbreviated interaction name.
    
    EX: Z4-N5-JISP16-C-hw20.0-Nmax06-JJ7
    """

    coulomb_flag = mcscript.ifelse(current_task["coulomb"],"C","NC")
    return "Z{nuclide[0]}-N{nuclide[1]}-{interaction_short}-{coulomb_flag}"\
           "-hw{hw:.1f}-{model_space[0]}-JJ{twice_J}".format(
        coulomb_flag=coulomb_flag,
        **current_task
        )


################################################################
# lsu3shell: task pool identifier generator
################################################################

def task_pool_model_space (current_task):
    """ Create task pool identifier.
    """
    
    return  "{model_space[0]}".format(**current_task)

################################################################
# lsu3shell: task handler
################################################################

def task_handler_lsu3shell (current_task):
    """ Invoke lsu3shell given current task parameters.

    Expected dictionary keys:

        # nuclide parameters
        "nuclide" : (Z,N) tuple
        "nuclide_name" : name as string (DEPRECATED)
        "model_space" : tuple (name,lines) of model space name and list of lines for model space file
        "twice_J" : 2J
        # Hamiltonian parameters
        "hw" : hw
        "coulomb" : logical value whether or not to include Coulomb
        "aLawson" : aLawson
        "interaction_short" : short name for interaction (for use in descriptor)
        "interaction_dir" : directory (within  SU3_Interactions_Operators directory) for interaction
        "interaction_name" : filename for interaction (within that directory)
        # diagonalization parameters
        "lsu3shell_executable" : filename (explicit path or path) for lsu3shell executable file
        "eigenvectors" : number of eigenvectors to calculate
        "lanczos" : lanczos iteration
        "ndiag" : number of diagonal processes (may be needed for postprocessing)
    """

    # set filenames
    model_space_file_name = "Z{nuclide[0]}-N{nuclide[1]}-{model_space[0]}-JJ{twice_J}.model_space".format(**current_task)
    hamiltonian_file_name = "Hamiltonian"
    ndiag_file_name = "ndiag"
    interaction_filename = os.path.join(os.environ["SU3SHELL_DATA"],"SU3_Interactions_Operators",current_task["interaction_dir"],current_task["interaction_name"])
    ##eigen_dir = "{descriptor}".format(**current_task)
    archive_filename = "{descriptor}_eigen.tgz".format(**current_task)

    # calculate number of processors
    ndiag = current_task["ndiag"]
    nprocs = ndiag * (ndiag+1) // 2
    if (nprocs != mcscript.run.parallel_width):
        raise mcscript.ScriptError("allocated width does not match ndiag in task dictionary")

    # construct model space file
    mcscript.write_input(model_space_file_name,current_task["model_space"][1])

    # construct Hamiltonian file
    hamiltonian_lines = []
    hamiltonian_lines.append("{hw}".format(**current_task))
    hamiltonian_lines.append("TREL")
    if (current_task["coulomb"]):
        hamiltonian_lines.append("VCOUL")
    hamiltonian_lines.append("NCM {aLawson}".format(**current_task))
    hamiltonian_lines.append("INT {}".format(interaction_filename))
    mcscript.write_input(hamiltonian_file_name,hamiltonian_lines)

    # construct ndiag file
    ndiag_lines = ["{ndiag}".format(**current_task)]
    mcscript.write_input(ndiag_file_name,ndiag_lines)

    # execute lsu3shell
    lsu3shell_invocation = [
        current_task["lsu3shell_executable"],
        model_space_file_name,
        hamiltonian_file_name,
        format(current_task["eigenvectors"]),
        format(current_task["lanczos"])
        ]
    mcscript.parallel_setup()
    mcscript.call_parallel(lsu3shell_invocation,mcscript.run) 

    # test for success
    if (not os.path.exists("mfdn_eigenvalues.dat")):
        raise mcscript.ScriptError("mfdn_eigenvalues.dat not found.")

    # archive data files
    print ("Archiving output files...")
    archive_file_list = [
        hamiltonian_file_name, model_space_file_name, ndiag_file_name,
        "mfdn_eigenvalues.dat"
    ] + glob.glob("eigenvector*.dat")
    mcscript.call(["tar", "zcvf", archive_filename] + archive_file_list)
    mcscript.call(["mv", archive_filename, "--target-directory="+mcscript.task.results_dir])

    # cleanup of wave function files
    scratch_file_list = glob.glob("mfdn_lvectors*") + glob.glob("mfdn_alphabeta") + glob.glob("fort.*")
    mcscript.call(["rm", "-vf"] + scratch_file_list)


################################################################
# subspaces: task descriptor
################################################################

def task_descriptor_subspaces_1 (current_task):
    """ Return task descriptor.
    EX: Z2-N2-Nmax06
    """

    return "Z{nuclide[0]}-N{nuclide[1]}-{model_space[0]}".format(**current_task)

################################################################
# subspaces: task handler
################################################################

def task_handler_subspaces (current_task):
    """ Invoke ListU3xSU2subspaces given current task parameters.

    Expected dictionary keys:

        # nuclide parameters
        "nuclide" : (Z,N) tuple
        "nuclide_name" : name as string (DEPRECATED)
        "model_space" : tuple (name,lines) of model space name and list of lines for model space file
        "twice_J" : 2J
        # code parameters
        "calculator_executable" : filename (explicit path or path) for executable file
        "calculator_mode" : integer mode for calculation (currently supports 1 for irrep listing)
    """

    # set filenames
    model_space_file_name = "{descriptor}.model_space".format(**current_task)
    dimension_file_name = "{descriptor}.dim".format(**current_task)

    # construct model space file
    mcscript.write_input(model_space_file_name,current_task["model_space"][1])

    # execute calculator
    invocation = [
        current_task["calculator_executable"],
        str(current_task["calculator_mode"]),
        model_space_file_name
        ]
    results = mcscript.call_serial(invocation,mcscript.run,print_stdout=False)   # UGLY inelegant: future redirect output directly
    # dump contents to file
    with open(dimension_file_name,"w") as data_file:
        data_file.write(results)
        
    # test for success
    if (not os.path.exists(dimension_file_name)):
        raise mcscript.ScriptError("dimension file not found")

    # archive data files
    print ("Exporting output file...")
    mcscript.call(["mv", dimension_file_name, "--target-directory="+mcscript.task.results_dir])

################################################################
# su3_decomposition: task handler
################################################################

def task_handler_su3_decomposition (current_task):
    """ Invoke ncsmSU3xSU2wfnDecomposition on eigenvectors.

    Expected dictionary keys:

        # nuclide parameters
        "nuclide" : (Z,N) tuple
        "nuclide_name" : name as string (DEPRECATED)
        "model_space" : tuple (name,lines) of model space name and list of lines for model space file
        "twice_J" : 2J
        # code parameters
        "eigenvectors" : number of eigenvectors to calculate
        "ndiag" : number of diagonal processes
        "su3_decomposition_executable" : filename (explicit path or path) for executable file
    """

    # set filenames
    model_space_file_name = "Z{nuclide[0]}-N{nuclide[1]}-{model_space[0]}-JJ{twice_J}.model_space".format(**current_task)
    archive_filename = "{descriptor}_su3-content.tgz".format(**current_task)

    # execute decomposition code
    eigenvectors = current_task["eigenvectors"]
    for eigenvector_index in mcscript.value_range(1,eigenvectors,1):
        eigenvector_file_name = "eigenvector{:02d}.dat".format(eigenvector_index)
        decomposition_file_name = "eigenvector{:02d}_su3-content.txt".format(eigenvector_index)
        invocation = [
            current_task["su3_decomposition_executable"],
            model_space_file_name,
            str(current_task["ndiag"]),
            eigenvector_file_name
            ]
        results = mcscript.call_serial(invocation,mcscript.run,print_stdout=False)   # UGLY inelegant: future redirect output directly
        # dump contents to file
        with open(decomposition_file_name,"w") as data_file:
            data_file.write(results)
        
    # test for success
    # todo

    # archive data files
    print ("Archiving output files...")
    archive_file_list = glob.glob("eigenvector*_su3-content.txt")
    mcscript.call(["tar", "zcvf", archive_filename] + archive_file_list)
    mcscript.call(["mv", archive_filename, "--target-directory="+mcscript.task.results_dir])
