################################################################
# local customization hooks
################################################################

class LocalCustomizations(object):
    """ Object to bundle local customizations into common name space.

    Defaults defined here will normally be redefined by a local module
    file.
    
    Members for qsubm:
    
        serial_prefix: prefix for serial invocation
        parallel_prefix: command prefixes for parallel invocation

    Members for mcscript:

    """

    def __init__(self):
        serial_prefix = []
        parallel_prefix = []

local = LocalCustomizations()

# converting redirection to possibly more robust (and certainly more
# pythonic) scheme

    ## sys.stdout = open(output_filename, "w")
    ## try:
    ##     phase_handlers[phase](task)
    ## except mcscript.ScriptError as err:
    ##     # on failure, flag failure and propagate exception so script terminates
    ##     print ("ScriptError:", err)
    ##     os.rename(flag_base+".lock",flag_base+".fail")
    ##     raise
    ## sys.stdout.close()
    ## sys.stdout = saved_stdout

import sys

# encompassing with, with exception raised through it
with open("t1.out", "w") as sys.stdout:
    try:
        print ("Hello err")
        raise ValueError("Bad!")
    except ValueError as err:
        print ("ValueError:", err)
        raise

# problem is, this apparently closes stdout to future use?

    sys.stdout = saved_stdout
    saved_stdout = sys.stdout
    with open(output_filename, "w") as sys.stdout:
        try:
            phase_handlers[phase](task)
        except mcscript.ScriptError as err:
            # on failure, flag failure and propagate exception so script terminates
            print ("ScriptError:", err)
            os.rename(flag_base+".lock",flag_base+".fail")
            raise
    sys.stodout = saved_stdout




    ## print(flag_base,file=lock_stream)
    ## print(task["pool"], task["descriptor"],file=lock_stream)
    ## print(mcscript.run.job_id, mcscript.run.epar_rank,file=lock_stream)
    ## print(time.asctime(),file=lock_stream)

    if (sys.version_info[0] < 3):
        # result of process.communicate was string
        stdout_string = stdout_bytes
        stderr_string = stderr_bytes
    else:
        # result of process.communicate was bytes
        stdout_string = stdout_bytes.decode("utf-8")
        stderr_string = stderr_bytes.decode("utf-8")
