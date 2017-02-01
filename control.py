""" control.py -- provide overall scripting control code

  Language: Python 3

  M. A. Caprio
  Department of Physics, University of Notre Dame

  6/13/16 (mac): Extract from mcscript.py.
  1/8/17 (mac): Simplify omp_setup to just set OMP_NUM_THREADS.

"""

import sys
import os
import subprocess

import mcscript.config as config
import mcscript.parameters as parameters
import mcscript.utils as utils


################################################################
# initialization code
################################################################

# force run into namespace before invocation of init()
run = parameters.RunParameters()

def init():
    """ Carry out run setup.

    Global variable:
        run (RunParameters): Record of run parameters from environment.
    """

    ################################################################
    # retrieve job information
    ################################################################

    run.populate()

    if (run.verbose):
        print("")
        print("-"*64),
        print(run.run_data_string())
        print("-"*64),
        print(utils.time_stamp()),
        sys.stdout.flush()

    ################################################################
    # make and cd to scratch directory
    ################################################################

    if (not os.path.exists(run.work_dir)):
        subprocess.call(["mkdir","--parents",run.work_dir])
    os.chdir(run.work_dir)



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
    if (run.verbose):
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

    where the full path to modulecmd must be specified by
    MCSCRIPT_MODULE_CMD.

    Arguments:

        args (list of str): list of intended arguments to 
        "module"

    EX: module(["load", "mpich2"]) # to add mpiexec command to PATH

    """

    print ("module"," ".join(args))
    module_command = os.path.join(os.environ["MODULESHOME"],"bin","modulecmd")
    module_code_string = subprocess.check_output([ module_command, "python" ] + args)
    if (module_code_string != ""):
        print("  Executing module code...")
        module_code = compile(module_code_string,"<string>","exec")
        eval(module_code)  # eval can crash on raw string, so compile first
    else:
        print ("  No module code to execute...")

################################################################
# subprocess execution
################################################################

# exception class for errors in script execution
class ScriptError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def call(
        base,
        mode=0,  # call.local is not yet defined so hard-code value (ugh)
        input_lines=[],
        shell=False,cwd=None,
        print_stdout=True,check_return=True
):
    """Invoke subprocess with simple batch input and output via
    POpen.communicate.  The subprocess arguments are obtained by
    joining the prefix list to the base list.  Input lines and
    captured output are logged to stdout.

    Arguments:

        base (list of str): list of arguments for subprocess invocation

        mode (int): mode of invocation for code

            mcscript.call.local: lightweight code for direct invocation under script
            (e.g., a simple os command)

            mcscript.call.serial: "serial" compute code (may be
            directly invoked under script or shipped to compute node;
            also had special treatment under epar jobs); number of OMP
            threads set separately from OMP width for hybrid runs

            mcscript.call.hybrid: code requiring mpi launch
    
        input_lines (list of str): list of lines to be given to the
        subprocess as standard input (i.e., as list of strings, each
        of which is to be treated as one input line)

        print_stdout (boolean): or not to print subprocess's captured
        output to stdout

        check_resturn (boolean): whether or not to check subprocess's return value
        (and raise exception if nonzero)
    
        shell (boolean): whether or not to launch subshell
        (pass-through to POpen)
    
        cwd (str or None): current working directory (pass-through to
        POpen)

    Returns:
        (str): subprocess's captured output

    Exceptions:

        If check_return is set and subprocess return is nonzero,
        raises a ScriptError exception.  Also raises a ScriptError
        exception if subprocess cannot be invoked in the first place.
    
    Limitations:

        All captured output is lost if process crashes.
    
    Examples:

        >>> mcscript.call(["cat"],input_lines=["a","b"]) # basic
        >>> mcscript.call(["catx"],input_lines=["a","b"]) # for execution failure
        >>> mcscript.call(["cat","badfile"],input_lines=["a","b"]) # for nonzero return
        >>> mcscript.call(["cat","badfile"],input_lines=["a","b"],mode=mcscript.call.serial) # specifying run mode

    """

    # set up invocation
    if (mode is call.local):
        invocation = base
    elif (mode==call.serial):
        openmp_setup(run.serial_threads)
        invocation = config.serial_invocation(base)
    elif (mode==call.hybrid):
        openmp_setup(run.parallel_depth)
        invocation = config.hybrid_invocation(base)
    else:
        raise(ValueError("invalid invocation mode"))
    
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

    # log header output
    print ("----------------------------------------------------------------")
    print ("Running %s" % str(invocation))
    print ("Given standard input:")
    print (stdin_string)
    utils.time_stamp()
    print ("----------------------------------------------------------------")
    sys.stdout.flush()
    
    # invoke
    try:
        # launch process
        process = subprocess.Popen(
            invocation,
            stdin=subprocess.PIPE,     # to take input from communicate
            stdout=subprocess.PIPE,    # to send output to communicate
            stderr=subprocess.PIPE,    # separate stderr
            shell=shell,cwd=cwd,       # pass-through arguments 
            close_fds=True             # for extra neatness and protection
            )
    except OSError as err:
        print ("Execution failed:", err)
        raise ScriptError("execution failure")

    # communicate with process
    (stdout_bytes,stderr_bytes) = process.communicate(input=stdin_bytes)

    # process output
    # result of process.communicate was bytes (under Python 3)
    stdout_string = stdout_bytes.decode(encoding="ascii",errors="ignore")
    stderr_string = stderr_bytes.decode(encoding="ascii",errors="ignore")
    if (print_stdout):
        print (stdout_string)
    print (stderr_string)
    # handle return value
    returncode = process.returncode
    print ("Return code:", returncode)

    # finish logging
    print ("----------------------------------------------------------------")
    utils.time_stamp()
    print ("----------------------------------------------------------------")
    sys.stdout.flush()  # just for good measure

    # return (or abort)
    if ( check_return and (returncode != 0) ):
        raise ScriptError("nonzero return")

    return stdout_string

# enumerated type (is this best convention???)
#
# TODO: upgrade to Python 3.4 enum type
call.local = 0
call.serial = 1
call.hybrid = 2

