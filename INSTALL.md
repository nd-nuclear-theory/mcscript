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
+ 07/03/22 (pjf): Rewrite for config-file based approach.

----------------------------------------------------------------

# 1. Installing `mcscript` module #

  If you want the most recent stable release, install the package with `pip`
  (or `pip3` on Debian/Ubuntu):
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % pip install --user git+https://github.com/nd-nuclear-theory/mcscript.git#egg=mcscript
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Repeat this command to update to the latest stable release.

  ## a) Development setup ##
  If you are developing `mcscript` itself or want the bleeding-edge, potentially
  broken version, check out the `develop` branch and install in development
  (editable) mode.

  Change to the directory where you want the repository to be cloned,
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

  Check out the `develop` branch:
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % git checkout -t origin/develop
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Install `mcscript` in "editable" (development) mode:
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % python3 -m pip install --user --editable .
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  To update a development installation:
  ~~~~~~~~~~~~~~~~
  % git pull
  % python3 -m pip install --user --editable .
  ~~~~~~~~~~~~~~~~

# 2. Local configuration module

  The local configuration module provides functions which construct the batch
  submission (qsub, sbatch, etc.) command lines and and serial/parallel
  execution launch (mpiexec, srun, etc.) invocations appropriate to your
  cluster and running needs.

  If you are only doing *local* runs (i.e., no batch job submission) on your
  laptop/workstation, and if you are using with OpenMPI as your MPI
  implementation, you can use the generic configuration module
  `config/config-ompi.py`.

  Local configuration modules are currently provided for the following clusters:
  * `config/config-uge-ndcrc.py` - Univa Grid Engine at the CRC (Notre Dame)
  * `config/config-slurm-nersc.py` - Slurm at NERSC (LBNL)
  * `config/config-cobalt-alcf.py` - Cobalt at ALCF (ANL)
  * `config/config-torque-oak.py` - Torque at UBC ARC (TRIUMF)

  Whenever you move to a new cluster, you will have to write such a module to
  take into account the pecularities of the batch submission software and queue
  structure of that cluster. You can use the above example modules as models to
  define your own configuration modules appropriate to your own cluster and your
  own running needs.

# 3. Configuration file

  You will neeed to create a file containing your user configuration. This is a
  standard `ini`-style file. It needs to be placed in
  `$XDG_CONFIG_HOME/mcscript.conf`, which on most platforms is
  `$HOME/.config/mcscript.conf`, or in `$HOME/.mcscriptrc. The most important
  variables are:

  > `cluster_config` specifies the path to the Python source of the cluster configuration

  > `install_home` specifies the directory in which executables are found.

  > `run_home` specifies the directory in which job files are found.

  > `work_home` specifies the parent directory in which run scratch directories
  > should be made.  This will normally be on a fast scratch filesystem.

  A minimal example is
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  [mcscript]
  # cluster configuration
  cluster_config = $HOME/code/mcscript/config/config-ompi.py

  # install location for executables
  install_home = $HOME/install

  # default location for run scripts
  run_home = $HOME/runs

  # default location for work directories (typically on scratch filesystem)
  work_home = $SCRATCH/runs
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  A few other optional environment variables (which you are not likely to
  need) are defined in the documentation inside `mcscript.config`.

  You may also need to set environment variables expected by the scripting for
  specific application you plan to run under mcscript.  But those should be
  defined in the documentation for the relevant scripting.

  To tell mcscript about this file, make sure you set `env_script`
  in `mcscript.conf`:

  > `env_script` (optional) should give the full qualified filename (i.e.,
  > including path) to any shell code which should be "sourced" at the beginning
  > of the batch job.  This should be sh/bash-compatible code.

  > @NDCRC: For example, if you are using the ND shell tools at the ND CRC, you need to
  > ensure all required runtime libraries (such as the MPI library) are loaded on
  > the compute node at run time.  If you are always using the intel suite, for
  > instance, you can simply include this definition in your .cshrc:
  >
  > ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  > env_script = ${HOME}/code/ndconfig/env-intel-ndcrc.csh
  > ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  >
  > Otherwise, be sure to redefine this environment variable before
  > calling qsubm.

  Availability of Python 3: You will need to make sure that a valid Python 3
  executable can be invoked both (a) on the front end node, for qsubm and for
  local runs by qsubm, and (b) on the compute node, in order for your job script
  to launch on the compute node.

  > `python_executable` specifies the path to the Python 3 interpreter

  Even if a python3 module is loaded on the front end at submission time, the
  relevant environment variables (PATH, etc.) might or might not automatically
  convey to batch job when it runs on the compute node (this depends on your
  batch system).  The simplest solution, which works in most circumstances, is
  to load a python3 module from your login shell initialization file.
  Alternatively, you may use the `env_script` hook to ensure that a python3
  module is loaded when your batch job starts.

# 4. Basic tests

  Basic test scripts may be found in `mcscript/example`.  But qsubm will be
  looking for them in your "run" directory.  So you can start by putting
  symbolic links to these example scripts in your "run" directory:

  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % cd $HOME/runs
  % ln -s $HOME/code/mcscript/example/runex01.py
  % ln -s $HOME/code/mcscript/example/runex02.py
  % ln -s $HOME/code/mcscript/example/runex03.py
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
  in `run_home` regardless.

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
