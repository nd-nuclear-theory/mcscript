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
+ 01/01/17 (pjf): Update for installation with `pip`.

----------------------------------------------------------------

# 1. Retrieving and installing source

  Change to the directory where you want the repository to be installed,
  e.g.,
  ~~~~~~~~~~~~~~~~
  % cd ~/code
  ~~~~~~~~~~~~~~~~

  Clone the shell repository and all submodules.  In the following,
  replace "netid" with your ND NetID:
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % git clone ssh://<netid>@crcfe01.crc.nd.edu/afs/crc.nd.edu/group/nuclthy/git/mcscript.git
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Or, from the secondary (public) repository on github:
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % git clone https://github.com/nd-nuclear-theory/mcscript.git
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Setup the package in your `PYTHONPATH` by running `pip` (or `pip3` on Debian):
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % pip install --user --editable mcscript/
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Then change your working directory (`cd`) to the project directory for
  all the following steps.

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

  In your csh initialization file, define initialization as follows
  (adjusting directory names to match your own choices as
  appropriate):
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # mcscript
  setenv MCSCRIPT_DIR ${HOME}/code/mcscript
  setenv MCSCRIPT_INSTALL_DIR ${HOME}/code/install
  setenv MCSCRIPT_RUN_HOME ${HOME}/runs
  setenv MCSCRIPT_WORK_HOME ${SCRATCH}/runs
  setenv MCSCRIPT_RUN_PREFIX run
  setenv MCSCRIPT_PYTHON python3
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
  export MCSCRIPT_RUN_PREFIX=run
  export MCSCRIPT_PYTHON=python3
  source ${MCSCRIPT_DIR}/mcscript_init.sh
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  A description of these (and other) environment variables may be
  found by invoking the qsubm help:
  ~~~~~~~~~~~~~~~~
  % qsubm --help
  ~~~~~~~~~~~~~~~~

  You may also need to set environment variables for specific
  application scripts you plan to use with mcscript.

  Availability of Python: You will need to make sure that
  `MCSCRIPT_PYTHON` points to a valid Python 3 executable both (a) on
  the front end node, for qsubm and for local runs by qsubm, and (b)
  on the compute node, in order for your job script to launch on the
  compute node.  Even if a python3 module is loaded on the front end
  at submission time, the relevant environment variables (PATH, etc.)
  typically will *not* convey to the compute node, depending on your
  batch system.  The simplest solution is to load a python3 module
  from your .cshrc file.

  > @NDCRC: We need to load all required run modules at run time --
  > python, ompi, etc.  We don't have an elegant, general solution
  > yet.  The ad hoc solution is simply to load the relevant modules
  > from your `.cshrc` file:
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  setenv MCSCRIPT_SOURCE ${HOME}/code/shell/config/module-load-ndcrc.csh
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  > Of course, this assumes you always want these modules loaded, for
  > whatever code you might be running.  You may not be so lucky.
  >
  > Future code development: It may therefore be more appropriate to
  > define a per-job module load/swap/unload list to be handled
  > within `mcscript.init`.

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
