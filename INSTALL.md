# mcscript installation guide #

Mark A. Caprio, Patrick J. Fasano  
Department of Physics, University of Notre Dame

+ 12/30/16 (mac): Created.
+ 01/18/17 (mac): Remove MFDn environment example.
+ 02/23/17 (mac): Clarify configuration instructions.
+ 02/25/17 (mac): Add note about python availability on compute node.
+ 05/09/17 (mac): Add bash instructions.  Expand discussion of examples.
+ 08/28/17 (pjf): Add environment for mcscript-managed executables.
+ 12/21/17 (pjf): Move to INSTALL.md and update to Markdown.
+ 01/01/18 (pjf): Update for installation with `pip`.
+ 02/06/18 (pjf): Update MCSCRIPT_SOURCE file path.
+ 02/09/18 (mac): Overhaul configuration instructions.

----------------------------------------------------------------

# 1. Retrieving and installing source

  Change to the directory where you want the repository to be installed,
  e.g.,
  ~~~~~~~~~~~~~~~~
  % cd ~/code
  ~~~~~~~~~~~~~~~~

  Clone the `mcscript` repository.
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % git clone https://github.com/nd-nuclear-theory/mcscript.git
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Change your working directory to the repository for the following steps:
  ~~~~~~~~~~~~~~~~
  % cd mcscript
  ~~~~~~~~~~~~~~~~

  If you want the bleeding-edge, potentially broken version, check out the
  `develop` branch:
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % git checkout -t origin/develop
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Set up the package in your `PYTHONPATH` by running `pip` (or `pip3` on Debian):

  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % pip install --user --editable .
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  a. Subsequently updating source:

  ~~~~~~~~~~~~~~~~
  % git pull
  ~~~~~~~~~~~~~~~~

# 2. Local configuration

  The local configuration file provides functions which construct the batch
  submission (qsub, sbatch, etc.) command lines and and serial/parallel
  execution launch (mpiexec, srun, etc.)  invocations appropriate to your
  cluster and running needs.  You need to create a symbolic link `config.py` to
  point to the correct configuration file for the system or cluster you are
  running on.

  If you are only doing *local* runs (i.e., no batch job submission) on your
  laptop/workstation, and if you are using with OpenMPI as your MPI
  implementation, you can use the generic configuration file config-ompi.py in
  mcscript/config:
  
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % ln -s config/config-ompi.py config.py
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Example local configuration files for Univa Grid Engine at the Notre
  Dame Center for Research Computing and SLURM at NERSC are included
  in the mcscript/config directory.

  >#### @NDCRC: ####
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % ln -s config/config-uge-ndcrc.py config.py
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  >#### @NERSC: ####
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % ln -s config/config-slurm-nersc.py config.py
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Otherwise, whenever you move to a new cluster, you will have to
  write such a file, to take into account the pecularities of the
  batch submission software and queue structure of that cluster.
  You can use the above example files as models to define your own configuration
  file appropriate to your own cluster and your own running needs.

# 3. Environment variables

  You will also need to add the `mcscript\tools` directory to your command path.
  Furthermore, the mcscript job submission utility "qsubm" expects certain
  environment variables to be defined at submission time:

  > MCSCRIPT_DIR specifies the directory in which the mcscript package is
  > installed, i.e., the directory where the file qsubm.py is found.  (Note
  > that qsubm uses this information to locate certain auxiliary script files
  > used as part of the job submission process.)

  > MCSCRIPT_INSTALL_HOME specifies the directory in which executables are
  > found.

  > MCSCRIPT_RUN_HOME specifies the directory in which job files are found.

  > MCSCRIPT_WORK_HOME specifies the parent directory in which run scratch
  > directories should be made.  This will normally be on a fast scratch
  > filesystem.

  A few other optional environment variables (which you are not likely to
  need) are defined in the documentation inside `qsubm.py`.

  The easiest way to ensure that these variables are defined is to define them
  in the shell initialization file for your login shell.  That is, if you are a
  tcsh user, you would add something like the following to your .cshrc file:
  
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # mcscript
  setenv MCSCRIPT_DIR ${HOME}/code/mcscript
  setenv MCSCRIPT_INSTALL_HOME ${HOME}/code/install
  setenv MCSCRIPT_RUN_HOME ${HOME}/runs
  setenv MCSCRIPT_WORK_HOME ${SCRATCH}/runs
  setenv PATH ${MCSCRIPT_DIR}/tools:${PATH}
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Alternatively, if you are a bash user, you would add something like the
  following to your .bashrc file:
  
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # mcscript
  export MCSCRIPT_DIR=${HOME}/code/mcscript
  export MCSCRIPT_INSTALL_HOME=${HOME}/code/install
  export MCSCRIPT_RUN_HOME=${HOME}/runs
  export MCSCRIPT_WORK_HOME=${SCRATCH}/runs
  export PATH=${MCSCRIPT_DIR}/tools:${PATH}
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  You may also need to set environment variables expected by the scripting for
  specific application you plan to run under mcscript.  But those should be
  defined in the documentation for the relevant scripting.

  To tell mcscript about this file, make sure you set MCSCRIPT_SOURCE
  at the time you submit the job, i.e., before calling qsubm:

  > MCSCRIPT_SOURCE (optional) should give the full qualified
  > filename (i.e., including path) to any shell code which should
  > be "sourced" at the beginning of the batch job.  This should be
  > sh/bash-compatible code.

  > @NDCRC: For example, if you are using the ND shell tools at the ND CRC, you need to
  > ensure all required runtime libraries (such as the MPI library) are loaded on
  > the compute node at run time.  If you are always using the intel suite, for
  > instance, you can simply include this definition in your .cshrc:
  > 
  > ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  > setenv MCSCRIPT_SOURCE ${HOME}/code/ndconfig/env-intel-ndcrc.csh
  > ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  > 
  > Otherwise, be sure to redefine this environment variable before
  > calling qsubm.

  Availability of Python 3: You will need to make sure that a valid Python 3
  executable can be invoked both (a) on the front end node, for qsubm and for
  local runs by qsubm, and (b) on the compute node, in order for your job script
  to launch on the compute node.  Even if a python3 module is loaded on the
  front end at submission time, the relevant environment variables (PATH, etc.)
  might or might not automatically convey to batch job when it runs on the
  compute node (this depends on your batch system).  The simplest solution,
  which works in most circumstances, is to load a python3 module from your login
  shell initialization file.  Alternatively, you may use the `MCSCRIPT_SOURCE`
  hook to ensure that a python3 module is loaded when your batch job starts.

# 4. Basic tests

  Basic test scripts may be found in `mcscript/example`.  But qsubm will be
  looking for them in your "run" directory.  So you can start by putting
  symbolic links to these example scripts in your "run" directory:

  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % cd ${MCSCRIPT_RUN_HOME}
  % ln -s ${MCSCRIPT_DIR}/example/runex01.py
  % ln -s ${MCSCRIPT_DIR}/example/runex02.py
  % ln -s ${MCSCRIPT_DIR}/example/runex03.py
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  - - - -

  Example 01

  This is a simple "hello world" example.  It does not require any
  special options, e.g.,
  ~~~~~~~~~~~~~~~~
  % qsubm ex01
  ~~~~~~~~~~~~~~~~

  Note: You can invoke qsubm from *any* directory.  It does not care
  about your current working directory.  It will look for the scripts
  in `${MCSCRIPT_RUN_HOME}` regardless.

  - - - -

  Example 02

  This is an expanded "hello world" example, which demonstrates the
  "multi-task" functionality of mcscript.

  Please read the detailed instructions in the docstring at the top of
  `example/runex02.py`.  You will want to try out the various options to
  qsubm, as outlined in the instructions for the example, e.g.,
  ~~~~~~~~~~~~~~~~
  % qsubm ex02 --toc
  ~~~~~~~~~~~~~~~~

  - - - -

  Example 03

  This is a simple test for hybrid parallel (OpenMP/MPI) execution.

  Please read the detailed instructions in the docstring at the top of
  `example/runex03.py`.

  Note that you will first need to compile the example code `hello-hybrid.cpp`,
  as described in the docstring of `example/runex03.py`.

  - - - -

  Example 04

  This is mainly a debugging script to use if you are uncertain which
  environment variables are being passed through to the batch
  environment, in various operating modes.
