""" control.py -- provide overall scripting control code

    Language: Python 3

    M. A. Caprio
    Department of Physics, University of Notre Dame

    - 6/13/16 (mac): Extract from mcscript.py.
    - 1/8/17 (mac): Simplify omp_setup to just set OMP_NUM_THREADS.
    - 3/30/17 (pjf): Use fully-qualified name for mcscript.exception.ScriptError.
    - 5/22/17 (mac):
        + Reformat output from call, including adding wall time.
        + Deprecate aliases to call mode.
    - 6/28/17 (mac):
        + Remove storage of stdout/sterr by POpen.communicate in mcscript.call.
        + Remove deprecated aliases to call mode.
    - 06/07/19 (pjf):
        + Use new (Python 3.5+) subprocess interface subprocess.run.
        + Add FileWatchdog to detect failure-to-launch errors.
    - 07/03/19 (pjf): Have FileWatchdog optionally check repeatedly for file
      modification to detect hung process.
    - 11/05/19 (mac): Allow restarts after FileWatchdog failure.
    - 11/05/19 (pjf): Restore redirection of subprocess output.
    - 02/08/22 (pjf): Add loaded_modules().
    - 02/12/22 (pjf): Add status information to termination().
    - 07/07/22 (pjf): Ensure that termination() actually terminates interpreter.
"""

import enum
import os
import signal
import subprocess
import sys
import time

from . import (
    config,
    parameters,
    utils,
    exception,
)

################################################################
# initialization code
################################################################

def init():
    """ Carry out run setup.

    Global variable:
        run (RunParameters): Record of run parameters from environment.
    """

    # retrieve job information
    parameters.run.populate()
    parameters.run.job_id = config.job_id()

    # make and cd to scratch directory
    if not os.path.exists(parameters.run.work_dir):
        subprocess.call(["mkdir", "--parents", parameters.run.work_dir])
    os.chdir(parameters.run.work_dir)

    # invoke local init
    config.init()

    # print run information
    if parameters.run.verbose:
        print("")
        print("-"*64)
        print(parameters.run.run_data_string())
        print("-"*64)
        print(utils.time_stamp())
        sys.stdout.flush()


################################################################
# termination code
#   to be invoked explicitly by job file
################################################################

def termination(success=True, complete=True):
    """Do global termination tasks.

    Arguments:
        success (bool, optional): whether the job is terminating in a success state
        complete (bool, optional): whether the job completed all assigned work
    """

    # invoke local termination
    config.termination(success, complete)

    # provide verbose ending
    #   only if top-level invocation of job file, not epar daughter
    if parameters.run.verbose:
        sys.stdout.flush()
        print("-"*64)
        print("Termination status: {}".format("success" if success else "failure"))
        print("End script")
        print(utils.time_stamp())
        print("-"*64)
    sys.stdout.flush()

    sys.exit(0 if success else 1)


################################################################
# module operations
################################################################

def module(args):
    """Evaluate module operation.

    Evaluates the code provided by the module command

        modulecmd python arg1 arg2 ...

    Arguments:

        args (list of str): list of intended arguments to
        "module"

    EX: module(["load", "mpich2"]) # to add mpiexec command to PATH

    """

    print("module", " ".join(args))
    module_command = os.path.join(os.environ["MODULESHOME"], "bin", "modulecmd")
    module_code_string = subprocess.check_output([module_command, "python"] + args)
    if module_code_string != "":
        print("  Executing module code...")
        module_code = compile(module_code_string, "<string>", "exec")
        eval(module_code)  # eval can crash on raw string, so compile first
    else:
        print("  No module code to execute...")

def loaded_modules():
    """Get dictionary of loaded modules.

    Returns:
        (dict): loaded module-version mapping
    """
    module_list = os.environ.get("LOADEDMODULES", "").split(":")
    module_dict = {}
    for module_str in module_list:
        m,_,v = module_str.partition('/')
        module_dict[m] = v
    return module_dict

################################################################
# file existence checks
################################################################

class FileWatchdog(object):
    """Provides an interface for checking file existence/modification after timeout.

    This class wraps signal.alarm(), and provides for checking for file
    existence and modification after a certain delay. This can be used to
    detect, e.g., problems with executable startup due to batch system problems,
    etc. This will raise a `TimeoutError` if `filename` does not exist within
    `timeout` seconds after start() is called. If `repeat` is True, file will be
    checked repeatedly at an interval of `timeout`, and will raise a
    `TimeoutError` if `filename` has not been modified within the last `timeout`
    seconds.

    Arguments:
        filename (str or path-like): file to check existence of after timeout
        timeout (int): number of seconds to wait until checking if file exists
        repeat (bool, optional): whether to repeatedly check for file modification
    """

    def __init__(self, filename, timeout=120, repeat=False):
        self.filename = filename
        self.timeout = timeout
        self.repeat = repeat

    def start(self):
        """Start the watchdog timer."""
        signal.signal(signal.SIGALRM, self._handler)
        signal.alarm(self.timeout)

    def stop(self):
        """Stop the watchdog timer."""
        signal.alarm(0)

    def _handler(self, signalnum, frame):
        if not os.path.exists(self.filename):
            raise TimeoutError(
                "file {:s} not found after {:d} seconds".format(self.filename, self.timeout)
            )
        elif (time.time() - os.path.getmtime(self.filename)) > self.timeout:
            raise TimeoutError(
                "file {:s} has not changed for {:d} seconds".format(
                    self.filename, int(time.time() - os.path.getmtime(self.filename))
                    )
            )
        if self.repeat:
            self.start()
        else:
            self.stop()


################################################################
# subprocess execution
################################################################

# enumerated type
class CallMode(enum.Enum):
    kLocal = 0
    kSerial = 1
    kHybrid = 2


def call(
        base,
        shell=False,
        mode=CallMode.kLocal,
        input_lines=(),
        cwd=None,
        check_return=True,
        print_timing=True,
        file_watchdog=None,
        file_watchdog_restarts=0
):
    """Invoke subprocess.  The subprocess arguments are obtained by
    joining the prefix list to the base list.

    TODO: suport redirection to /dev/null to hide large output

    Arguments:

        base (list of str): list of arguments for subprocess invocation

        shell (boolean, optional): whether or not to launch subshell
        (pass-through to POpen)

        mode (CallMode, optional): mode of invocation for code

            CallMode.kLocal: lightweight code for direct invocation under script
            (e.g., a simple os command)

            CallMode.kSerial: "serial" compute code (may be
            directly invoked under script or shipped to compute node;
            also had special treatment under epar jobs); number of OMP
            threads set separately from OMP width for hybrid runs

            CallMode.kHybrid: code requiring mpi launch

        input_lines (list of str, optional): list of lines to be given to the
        subprocess as standard input (i.e., as list of strings, each
        of which is to be treated as one input line)

        cwd (str or None): current working directory (pass-through to
        POpen)

        check_return (boolean, optional): whether or not to check subprocess's return value
        (and raise exception if nonzero)

        print_timing (boolean, optional): or not to print wall time

        file_watchdog (mcscript.control.FileWatchdog): file watchdog for checking
        existence after executable startup

        file_watchdog_restarts (int): number of restarts allowed after watchdog
        failures

    Exceptions:

        If check_return is set and subprocess return is nonzero,
        raises a mcscript.exception.ScriptError exception.  Also
        raises a mcscript.exception.ScriptError exception if
        subprocess cannot be invoked in the first place.

    Examples:

        >>> mcscript.call(["cat"],input_lines=["a","b"]) # basic
        >>> mcscript.call(["catx"],input_lines=["a","b"]) # for execution failure
        >>> mcscript.call(["cat","badfile"],input_lines=["a","b"]) # for nonzero return
        >>> mcscript.call(["cat","badfile"],input_lines=["a","b"],mode=mcscript.CallMode.kSerial) # specifying run mode

    """

    # set up invocation
    if mode is CallMode.kLocal:
        invocation = base
    elif mode is CallMode.kSerial:
        config.openmp_setup(parameters.run.serial_threads)
        invocation = config.serial_invocation(base)
    elif mode is CallMode.kHybrid:
        config.openmp_setup(parameters.run.hybrid_threads)
        invocation = config.hybrid_invocation(base)
    else:
        raise ValueError("invalid invocation mode")

    # make a single string if running under subshell
    if shell:
        invocation = " ".join(invocation)

    # set up input
    stdin_string = "\n".join(input_lines)
    # add trailing newline
    stdin_string += "\n"
    # encode as bytes
    #   else communicate complains under Python 3: 'str' does not
    #   support the buffer interface
    # caveat: bytes(stdin_string, "ascii") fails Python 2 backward compatibility,
    # but encoding is required by Python 3
    #
    # "ascii" encoding will choke on newer gnu utilities utf-8 output
    stdin_bytes = bytes(stdin_string, encoding="ascii", errors="ignore")

    # log header output
    print("----------------------------------------------------------------")
    print("Executing external code")
    print("Command line: {:s}".format(str(invocation)))
    print("Call mode: {:s}".format(str(mode)))
    print("Start time: {:s}".format(utils.time_stamp()))
    if input_lines:
        print("----------------")
        print("Given standard input:")
        print(stdin_string)
    sys.stdout.flush()

    # head output
    print("----------------")
    print("Output:", flush=True)

    # start timing
    subprocess_start_time = time.time()

    # run process
    completed = False
    file_watchdog_failures = 0
    while not completed:

        # start file watchdog
        if file_watchdog is not None:
            file_watchdog.start()

        # call subprocess
        try:
            process = subprocess.run(
                invocation,
                input=stdin_bytes,
                stdout=sys.stdout,
                stderr=subprocess.STDOUT,  # to redirect via stdout
                shell=shell, cwd=cwd,      # pass-through arguments
            )
        except TimeoutError as err:
            file_watchdog_failures += 1
            if file_watchdog_failures > file_watchdog_restarts:
                raise err
            print("File watchdog failure: will attempt restart {:d}/{:d}".format(file_watchdog_failures, file_watchdog_restarts))
        else:
            completed = True

        # stop file watchdog
        if file_watchdog is not None:
            file_watchdog.stop()

    # conclude timing
    subprocess_end_time = time.time()
    subprocess_time = subprocess_end_time - subprocess_start_time

    print("----------------")
    if print_timing:
        print("Wall time: {:.2f} sec (={:.2f} min)".format(subprocess_time, subprocess_time/60))
    # handle return value
    returncode = process.returncode
    print("Return code: {}".format(returncode))
    # finish logging
    print("----------------------------------------------------------------")
    sys.stdout.flush()  # just for good measure

    # return (or abort)
    if check_return and (returncode != 0):
        raise exception.ScriptError("nonzero return")

    ## return stdout_string
