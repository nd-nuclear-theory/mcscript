# mcscript installation guide #

Mark A. Caprio, Patrick J. Fasano  
Department of Physics, University of Notre Dame

+ 12/30/16 (mac): Created.
+ 1/18/17 (mac): Remove MFDn environment example.
+ 2/23/17 (mac): Clarify configuration instructions.
+ 2/25/17 (mac): Add note about python availability on compute node.
+ 5/9/17 (mac): Add bash instructions.  Expand discussion of examples.
+ 8/28/17 (pjf): Add environment for mcscript-managed executables.
+ 12/21/17 (pjf): Move to INSTALL.md and update to Markdown.
+ 01/01/18 (pjf): Update for installation with `pip`.
+ 02/06/18 (pjf): Update MCSCRIPT_SOURCE file path.
+ 02/09/18 (mac): Update environment description.

----------------------------------------------------------------

# 1. Retrieving and installing source

  Change to the directory where you want the repository to be installed,
  e.g.,
  ~~~~~~~~~~~~~~~~
  % cd ~/code
  ~~~~~~~~~~~~~~~~

  Clone the `mcscript` repository and all submodules.
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

  Setup the package in your `PYTHONPATH` by running `pip` (or `pip3` on Debian):
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % pip install --user --editable .
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  a. Subsequently updating source
  ~~~~~~~~~~~~~~~~
  % git pull
  ~~~~~~~~~~~~~~~~

# 2. Local configuration

  You need to create a symbolic link `config.py` to point to the
  correct configuration file for the system or cluster you are running
  on.

  If you are only doing *local* runs (i.e., no batch job submission)
  on your laptop/workstation with OpenMPI as your MPI implementation,
  you can use the generic configuration file config-ompi.py in
  mcscript/config:
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % ln -s config/config-ompi.py config.py
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Otherwise, whenever you move to a new cluster, you will have to
  write such a file, to take into account the pecularities of the
  batch submission software and queue structure of that cluster.

  Example local configuration files for Univa Grid Engine at the Notre
  Dame Center for Research Computing and SLURM at NERSC are included
  in this directory.

  >#### @NDCRC: ####
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % ln -s config/config-uge-ndcrc.py config.py
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  >#### @NERSC: ####
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % ln -s config/config-slurm-nersc.py config.py
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  You will need to follow these models to define the batch submission
  (qsub, sbatch, etc.) and serial/parallel execution launch (mpiexec,
  srun, etc.) invocations appropriate to your cluster and your running
  needs.

# 3. Environment variables

  The mcscript job submission utility "qsubm" expects certain
  environment variables to be defined at submission time.  The easiest
  way to ensure that these variables are defined is to define them in
  the shell initialization file for you your login shell (e.g., csh or
  bash).

  In your csh initialization file, define initialization as follows
  (adjusting directory names to match your own choices as
  appropriate):
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # mcscript
  setenv MCSCRIPT_DIR ${HOME}/code/mcscript
  setenv MCSCRIPT_INSTALL_DIR ${HOME}/code/install
  setenv MCSCRIPT_RUN_HOME ${HOME}/runs
  setenv MCSCRIPT_WORK_HOME ${SCRATCH}/runs
  setenv MCSCRIPT_PYTHON python3
  setenv MCSCRIPT_RUN_PREFIX run
  source ${MCSCRIPT_DIR}/mcscript_init.csh
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Alternatively, if your default shell is bash (we translate the
  `setenv` statements above into `export` statements and invoke the
  alternative initialization script file `mcscript_init.sh`):
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # mcscript
  export MCSCRIPT_DIR=${HOME}/code/mcscript
  export MCSCRIPT_INSTALL_DIR=${HOME}/code/install
  export MCSCRIPT_RUN_HOME=${HOME}/runs
  export MCSCRIPT_WORK_HOME=${SCRATCH}/runs
  export MCSCRIPT_PYTHON=python3
  export MCSCRIPT_RUN_PREFIX=run
  source ${MCSCRIPT_DIR}/mcscript_init.sh
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  You may also need to set environment variables for specific
  application scripts you plan to use with mcscript.

  A description of the environment variables for qsubm follows:

  > MCSCRIPT_DIR should specify the directory in which the mcscript
  > package is installed, i.e., the directory where the file qsubm.py
  > is found.  (Note that qsubm uses this information to locate
  > certain auxiliary script files used as part of the job submission
  > process.)

  > MCSCRIPT_RUN_HOME must specify the directory in which job files
  > are found.

  > MCSCRIPT_WORK_HOME should specify the parent directory in which
  > run scratch directories should be made.

  > MCSCRIPT_LAUNCH_HOME (optional) should specify the parent
  > directory in which run subdirectories for qsub invocation and
  > output logging should be made.  Otherwise, this will default to
  > MCSCRIPT_WORK_HOME.

  > MCSCRIPT_PYTHON should give the full qualified filename (i.e.,
  > including path) to the Python 3 executable for running run script
  > files.  A typical value will simply be "python3", assuming the
  > Python 3 executable is in the shell's command search PATH.
  > However, see note on "Availability of Python" below.

  > MCSCRIPT_RUN_PREFIX should specify the prefix for run names,
  > e.g., set to "run" if your scripts are to be named
  > run<XXXX>.py.

  If you are running batch jobs, you will typically also need to make
  sure certain modules are loaded or environment variables are set
  before your code executes.  For instance, you may need to load
  modules for certain libraries which your code uses, possibly even
  the compiler's own run-time libraries.  This choice may vary from
  job to job.  You can control this by storing the various definitions
  in a shell file (e.g., csh or bash, depending on which shell your
  jobs are launched under, on your local system or cluster).  Then
  mcscript will ensure that these definitions are "sourced" when your
  job starts on the compute node.

  To tell mcscript about this file, make sure you set MCSCRIPT_SOURCE
  at the time you submit the job, i.e., before calling qsubm:

  > MCSCRIPT_SOURCE (optional) should give the full qualified
  > filename (i.e., including path) to any shell code which should
  > be "sourced" at the beginning of the batch job.

  Availability of Python: You will need to make sure that
  `MCSCRIPT_PYTHON` points to a valid Python 3 executable both (a) on
  the front end node, for qsubm and for local runs by qsubm, and (b)
  on the compute node, in order for your job script to launch on the
  compute node.  Even if a python3 module is loaded on the front end
  at submission time, the relevant environment variables (PATH, etc.)
  typically will *not* automatically convey to batch job when it runs
  on the compute node (this depends on your batch system).  The
  simplest solution, which works in most circumstances, is to load a
  python3 module from your login shell initialization file.
  Alternatively, you may use the `MCSCRIPT_SOURCE` hook to ensure that
  a python3 module is loaded when your batch job starts and/or to
  reset `MCSCRIPT_PYTHON` to give a valid filename for a Python
  executable accessible from the compute node.

  > @NDCRC: We need to load all required runtime libraries are loaded
  > on the compute node at run time (ompi, etc.) and that the python3
  > module is loaded at run time.  If you are always using the intel
  > suite, for instance, you can simply include this definition in
  > your .cshrc:
  > ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  > setenv MCSCRIPT_SOURCE ${HOME}/code/ndconfig/env-intel-ndcrc.csh
  > ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  > Otherwise, be sure to redefine this environment variable before
  > calling qsubm.

# 4. Basic tests

  Basic test scripts may be found in `mcscript/example`.  But qsubm will
  be looking for tem in your "run" directory.  So you can start by
  putting symbolic links to these example scripts in your "run"
  directory:

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

  Note that you will first need to first compile the example code
  `hello-hybrid.cpp`, as described in the docstring of
  `example/runex03.py`.

  - - - -

  Example 04

  This is mainly a debugging script to use if you are uncertain which
  environment variables are being passed through to the batch
  environment, in various operating modes.
