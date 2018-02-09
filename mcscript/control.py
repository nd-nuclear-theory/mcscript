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
"""

import enum
import os
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

    if (parameters.run.verbose):
        print("")
        print("-"*64),
        print(parameters.run.run_data_string())
        print("-"*64),
        print(utils.time_stamp()),
        sys.stdout.flush()

    # make and cd to scratch directory

    if (not os.path.exists(parameters.run.work_dir)):
        subprocess.call(["mkdir","--parents",parameters.run.work_dir])
    os.chdir(parameters.run.work_dir)

    # invoke local init

    config.init()

################################################################
# termination code
#   to be invoked explicitly by job file
################################################################

def termination():
    """Do global termination tasks."""

    # invoke local termination
    config.termination()

    # provide verbose ending
    #   only if top-level invocation of job file, not epar daughter
    if (parameters.run.verbose):
        sys.stdout.flush()
        print("-"*64)
        print("End script")
        print(utils.time_stamp())
        print("-"*64)
    sys.stdout.flush()


################################################################
# OpenMP setup
################################################################

def openmp_setup(threads):
    """ Set OpenMP environment variables.

    Arguments:
        threads (int): number of threads
    """

    # set number of threads by global qsubm depth parameter
    print("Setting OMP_NUM_THREADS to {}.".format(threads))
    os.environ["OMP_NUM_THREADS"] = str(threads)


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

    print("module"," ".join(args))
    module_command = os.path.join(os.environ["MODULESHOME"],"bin","modulecmd")
    module_code_string = subprocess.check_output([ module_command, "python" ] + args)
    if (module_code_string != ""):
        print("  Executing module code...")
        module_code = compile(module_code_string,"<string>","exec")
        eval(module_code)  # eval can crash on raw string, so compile first
    else:
        print("  No module code to execute...")

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
        input_lines=[],
        cwd=None,
        check_return=True,
        print_timing=True
):
    """Invoke subprocess.  The subprocess arguments are obtained by
    joining the prefix list to the base list.

    TODO: suport redirection to /dev/null to hide large output

    Programming note: In the future, consider upgrading to Python 3.5
    subprocess.run(...,input=...) interface.

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

        check_return (boolean, optional): whether or not to check subprocess's return value
        (and raise exception if nonzero)

        print_timing (boolean, optional): or not to print wall time

        cwd (str or None): current working directory (pass-through to
        POpen)

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
    if (mode is CallMode.kLocal):
        invocation = base
    elif (mode==CallMode.kSerial):
        openmp_setup(parameters.run.serial_threads)
        invocation = config.serial_invocation(base)
    elif (mode==CallMode.kHybrid):
        openmp_setup(parameters.run.hybrid_threads)
        invocation = config.hybrid_invocation(base)
    else:
        raise(ValueError("invalid invocation mode"))

    # make a single string if running under subshell
    if shell:
        invocation = " ".join(invocation)

    # set up input
    stdin_string = "".join([s + "\n" for s in input_lines])
    # encode as bytes
    #   else communicate complains under Python 3: 'str' does not
    #   support the buffer interface
    # caveat: bytes(stdin_string, "ascii") fails Python 2 backward compatibility,
    # but encoding is required by Python 3
    #
    # "ascii" encoding will choke on newer gnu utilities utf-8 output
    stdin_bytes = bytes(stdin_string,encoding="ascii",errors="ignore")
    ## stdin_stream = io.StringIO(stdin_string)

    # log header output
    print("----------------------------------------------------------------")
    print("Executing external code")
    print("Command line: {:s}".format(str(invocation)))
    print("Call mode: {:s}".format(str(mode)))
    print("Start time: {:s}".format(utils.time_stamp()))
    if (input_lines!=[]):
        print("----------------")
        print("Given standard input:")
        print(stdin_string)
    sys.stdout.flush()

    # POpen.communicate -- "Note: The data read is buffered in memory,
    # so do not use this method if the data size is large or unlimited."

    ## # invoke
    ## subprocess_start_time = time.time()
    ## try:
    ##     # launch process
    ##     process = subprocess.Popen(
    ##         invocation,
    ##         stdin=subprocess.PIPE,     # to take input from communicate
    ##         stdout=subprocess.PIPE,    # to send output to communicate
    ##         stderr=subprocess.PIPE,    # separate stderr
    ##         shell=shell,cwd=cwd,       # pass-through arguments
    ##         close_fds=True             # for extra neatness and protection
    ##         )
    ## except OSError as err:
    ##     print("Execution failed:", err)
    ##     raise exception.ScriptError("execution failure")
    ##
    ## # communicate with process
    ## (stdout_bytes,stderr_bytes) = process.communicate(input=stdin_bytes)

    # head output
    print("----------------")
    print("Output:")

    # invoke
    subprocess_start_time = time.time()
    try:
        # launch process
        process = subprocess.Popen(
            invocation,
            stdin=subprocess.PIPE,     # to take input from communicate
            stdout=sys.stdout,         # to redirect
            stderr=subprocess.STDOUT,  # to redirect via stdout
            shell=shell,cwd=cwd        # pass-through arguments
            ## close_fds=True             # for extra neatness and protection (but may affect redirection on some OS)
            )
    except OSError as err:
        print("Execution failed:", err)
        raise exception.ScriptError("execution failure")

    # launch process
    process.communicate(input=stdin_bytes)
    ## process.stdin.write(stdin_bytes)
    ## process.wait()

    # conclude timing
    subprocess_end_time = time.time()
    subprocess_time = subprocess_end_time - subprocess_start_time

    ## # process output
    ## # result of process.communicate consists of bytes (under Python 3)
    ## stdout_string = stdout_bytes.decode(encoding="ascii",errors="ignore")
    ## stderr_string = stderr_bytes.decode(encoding="ascii",errors="ignore")
    ## if (print_stdout):
    ##     print("----------------")
    ##     print("Standard output:")
    ##     print(stdout_string)
    ##     if (len(stderr_string)>0):
    ##         print("----------------")
    ##         print("Standard error:")
    ##         print(stderr_string)

    print("----------------")
    if (print_timing):
        print("Wall time: {:.2f} sec (={:.2f} min)".format(subprocess_time,subprocess_time/60))
    # handle return value
    returncode = process.returncode
    print("Return code: {}".format(returncode))
    # finish logging
    print("----------------------------------------------------------------")
    sys.stdout.flush()  # just for good measure

    # return (or abort)
    if ( check_return and (returncode != 0) ):
        raise exception.ScriptError("nonzero return")

    ## return stdout_string
