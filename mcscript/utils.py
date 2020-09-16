""" utils -- scripting utility functions

    Language: Python 3

    M. A. Caprio
    University of Notre Dame

    2/13/13 (mac): Extracted from job.py.
    5/28/13 (mac): Overhaul of subprocess invocation to use POpen.communicate().
    6/5/13 (mac): Absorbed into mcscript package.
    1/22/14 (mac): Python 3 update.
    5/14/15 (mac):
        + Insert "future" statements for Python 2 legacy support, conditional
            use of decode by Python version.
        + Increased diagnostic output from subpath search utilities.
    6/13/16 (mac): Rename to utils.py as proper subpackage of mcscript.
    11/22/16 (mac): Move call out to control submodule.
    12/27/16 (mac):
        + Rewrite search_in_subdirectories.
        + Change write_input argument from "silent" to "verbose".
        + Coding style updates.
    1/30/17 (mac): Add function dict_union (from spreadsheet.py).
    2/21/17 (pjf): Add CoefficientDict class.
    2/23/17 (mac): Add function mkdir to provide alternative to os.mkdir.
    6/4/17 (mac): Overhaul search_in_directories and add optional custom error message.
    6/8/17 (pjf): Add write_namelist.
    6/27/17 (mac): Add option for search_in_subdirectories to fail gracefully.
    11/03/17 (pjf): Quote strings in namelist output.
    04/07/19 (pjf): Call super().__init__() instead of dict.__init__() in
        CoefficientDict.__init__().
    05/30/19 (pjf):
        + Add exist_ok and parents options to mkdir() to replicate
            os.mkdir() functionality.
        + Add is_compressible() to estimate if a file should be compressed.
    05/06/19 (pjf): Add scrub_ansi().
    09/01/19 (pjf): Add topological_sort().
    08/11/20 (pjf): Add TaskTimer.
    09/02/20 (pjf):
        + Rewrite search_in_subdirectories to allow searching with arbitrary
          subdirectory tree depths.
        + Allow expand_path to take a list of paths to expand.
    09/16/20 (pjf):
        + Fix mutable default arguments to topological_sort().
        + Add custom setter to CoefficientDict to avoid storing zero or 
          non-numerical coefficient.
"""

import collections
import glob
import math
import numbers
import itertools
import os
import re
import subprocess
import time
import zlib

from . import exception

################################################################
# input file generation
################################################################

def write_input(filename,input_lines=[],verbose=True):
    """ Generate text file (typically an input file for a code to be
    invoked by the script), with contents given line-by-line as list
    of strings, and log to stdout.

    Arguments:
        input_lines (list of str): input lines
        verbose (bool, optional): whether or not to provide diagnostic output
          (on by default, but might want to suppress, e.g., for large sets
           of files)
    """

    # set up input
    ##stdin_string = "".join([s + "\n" for s in input_lines])
    stdin_string = "\n".join(input_lines) + "\n"

    # produce diagnotic output
    if (verbose):
        print("----------------------------------------------------------------")
        print("Generating text file %s:" % filename)
        print(stdin_string)
        print("----------------------------------------------------------------")

    # dump contents to file
    data_file = open(filename,"w")
    data_file.write(stdin_string)
    data_file.close()


def write_namelist(filename, input_dict={}, verbose=True):
    """Generate Fortran namelist file from dictionary representation.

    Arguments:
        input_dict (dict of dicts): each key names a namelist, with contents given
            by the inner dictionary
        verbose (bool, optional): whether or not to provide diagnostic output
          (on by default, but might want to suppress, e.g., for large sets
           of files)
    """
    formatters = {
        int:   (lambda n: "{:d}".format(n)),
        float: (lambda x: "{:e}".format(x).replace("e", "d")),
        bool:  (lambda b: ifelse(b, ".true.", ".false.")),
        str:   (lambda s: "'{:s}'".format(s)),
    }

    def format_val(x):
        if type(x) not in formatters.keys():
            raise exception.ScriptError(
                "{} of type {} cannot be written to namelist".format(x, type(x))
                )
        return formatters[type(x)](x)

    lines = []

    for (name, namelist) in input_dict.items():
        # start Fortran namelist
        lines.append("&{:s}".format(name))
        # loop over contents
        for (key, val) in namelist.items():
            # sanity check
            if type(key) is not str:
                raise exception.ScriptError("invalid namelist variable: {}".format(key))

            # loop over lists and map them to arrays
            if type(val) is list:
                for i, item in enumerate(val):
                    lines.append("{key:s}({i:d}) = {value},".format(key=key, i=i+1, value=format_val(item)))
            # write out scalar variables
            else:
                lines.append("{key:s} = {value},".format(key=key, value=format_val(val)))

        # trim last comma and add namelist termination
        lines[-1] = lines[-1].rstrip(',')
        lines.append("/")

    # write file
    return write_input(filename, lines, verbose)


################################################################
# timestamp utilities
################################################################

def time_stamp():
    """Returns time stamp string.

    This is currently just a wrapper to time.asctime, but we are
    keeping it since (a) it saves loading the time module, and (b) it
    allows future flexibility in the preferred logging format.

    Returns:
        (str): text for use as time stamp
    """

    return time.asctime()

def date_tag():
    """ Returns date tag string "YYMMDD".

    Returns:
        (str): date string
    """
    return time.strftime("%y%m%d")

################################################################
# string concatenation utilities
################################################################

def stringify(li,delimiter):
    """ Converts list entries to strings and joins with delimiter."""

    string_list = map(str,li)
    return delimiter.join(string_list)

def dashify(li):
    """ Converts list entries to strings and joins with "-"."""

    return stringify(li,"-")

def spacify(li):
    """ Converts list entries to strings and joins with spaces."""

    return stringify(li," ")

def scrub_ansi(s):
    """Remove ANSI escape sequences from string

    Arguments:
        s (str): string to scrub
    Returns:
        (str): string without ANSI escape sequences
    """
    ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', s)

################################################################
# debug message utilities
################################################################

def type_as_str(x):
    return str(type(x))[7:-1]

################################################################
# range construction utilities
################################################################

def value_range(x1,x2,dx,epsilon=0.00001):
    """ value_range(x1,x2,dx) produces float or integer results [x1, ..., x2] with step dx

    This is meant to emulate Mathematica's Range[x1,x2,x], with a "<=" upper bound, in
    contrast to Python's range, which is limited to integers and has an "<" upper bound.

    Limitations: Currently assumes dx is positive.  Upper cutoff is
    slightly fuzzy due to use of epsilon in floating point comparison.

    epsilon: tolerance for cutoff, as fraction of dx
    """

    value_list = []
    x=x1
    while (x < (x2 + dx * epsilon)):
        value_list.append(x)
        x += dx
    return value_list

def log_range(x1,x2,steps,base=2,power=1,first=True):
    """ log_range (x1,x2,steps,base=2,power=1,first=True) -> values returns a range
    starting from x1 and ending with x2 (inclusive) in logarithmic
    increments, at with steps increments per octave.  The first entry may be omitted by setting first=False.

    An octave refers to a doubling, if base=2 and power=1, or in general multiplication by base**power.

    print log_range(10,40,8)  -> 10..40 in 16 steps (as two octaves)
    print log_range(1,2,8,power=0.5) -> 1..2 in 16 steps (as two sqrt-octaves)
    """

    alpha = power**(-1) * math.log(x2/x1) / math.log(base)

    value_list = [
        x1 * base**(power*p)
        for p in value_range(0,alpha,1/steps)
        ]

    if (not first):
        value_list = value_list[1:]

    return value_list

################################################################
# arithmetic utilities
################################################################

def approx_equal(x,y,tol):
    """ approx_equal(x,y,tol) tests whether or not x==y to within tolerance tol
    """

    return (abs(y-x) <= tol)

def approx_less_equal(x,y,tol):
    """ approx_equal(x,y,tol) tests whether or not x<=y to within tolerance tol
    """

    return (x <= y+tol )

def approx_gtr_equal(x,y,tol):
    """ approx_equal(x,y,tol) tests whether or not x>=y to within tolerance tol
    """

    return (x >= y-tol )

def approx_less(x,y,tol):
    """ approx_equal(x,y,tol) tests whether or not x<y excluding values within tolerance tol
    """

    return not approx_gtr_equal(x,y,tol)

def approx_gtr(x,y,tol):
    """ approx_equal(x,y,tol) tests whether or not x>y excluding values within tolerance tol
    """

    return not approx_less_equal(x,y,tol)

################################################################
# default value utility
################################################################

def auto_value(x,default):
    """ auto_value(x,default) returns x, unless x is None, in which case it returns default
    """

    if x is None:
        return default
    else:
        return x

################################################################
# flow control utilities
################################################################

def ifelse(cond,a,b):
    if (cond):
        return a
    else:
        return b

################################################################
# path search utilities
################################################################

def search_in_subdirectories(
        base_path_or_list, *args,
        base=False, fail_on_not_found=True, error_message=None, verbose=True
):
    """Search for file in a list of subdirectories, beneath a given base
    path (or list of base paths).

    Arguments:
        base_path_or_list (str or list of str): base path in which to search
            subdirectories (may alternatively be list of base paths)
        subdirectory_path_or_list (list of str, optional, repeatable):
            subdirectories to search
        filename (str): file name (or base file name) to match
        base (bool, optional): whether to accept given search string
            as filename root rather than exact match (then just return
            this base in the result)
        fail_on_not_found (bool, optional): whether to raise exception on
            failure to match (else returns None)
        error_message (str, optional): custom error message to display on
            file not found
        verbose (bool, optional): whether to print log messages


    Returns:
        (str): first match

    Raises:
         mcscript.exception.ScriptError: if no match is found

    """

    # process arguments
    if verbose:
        print("----------------------------------------------------------------")
        print("Searching for file name...")
        print("  Base directories:",base_path_or_list)
    if isinstance(base_path_or_list, str):
        base_path_list = [base_path_or_list]
    else:
        base_path_list = list(base_path_or_list)
    if len(args) < 1:
        raise ValueError("not enough arguments:", base_path_or_list, *args)
    subdirectory_lists = []
    for subdirectory_path_or_list in args[:-1]:
        if verbose:
            print("  Subdirectories:",subdirectory_path_or_list)
        if isinstance(subdirectory_path_or_list, str):
            subdirectory_lists.append([subdirectory_path_or_list])
        else:
            subdirectory_lists.append(list(subdirectory_path_or_list))
    filename = args[-1]
    if verbose:
        print("  Filename:",filename)

    # search in successive directories
    success = False
    for directory_list in itertools.product(base_path_list, *subdirectory_lists):
        qualified_name = os.path.join(*directory_list, filename)
        if (base):
            success = len(glob.glob(qualified_name+"*")>0)
        else:
            success = os.path.exists(qualified_name)
        if (success):
            break

    # document success or failure
    if verbose:
        if success:
            print("  ->", qualified_name)
        else:
            if error_message is None:
                print("  ERROR: No matching filename found...")
            else:
                print("  ERROR: {}".format(error_message))
        print("----------------------------------------------------------------")

    # handle return for success or failure
    if (not success):
        if (fail_on_not_found):
            raise exception.ScriptError("no match on filename".format(filename))
        else:
            return None
    return qualified_name


def expand_path(path_or_list):
    """Expand and normalize path.

    This is a wrapper to various os.path functions, which expand inline
    variables and ~, and normalize nestings of separators.

    Arguments:
        path_or_list: (str or list of str) path (or list of paths) as string(s)
    Returns:
        (str or list of str): expanded and normalized path(s)
    """
    if isinstance(path_or_list, (str, bytes, os.PathLike)):
        expanded_path = os.path.expanduser(os.path.expandvars(path_or_list))
        norm_path = os.path.normpath(expanded_path)
        return norm_path
    else:
        return list(map(expand_path, path_or_list))


################################################################
# dictionary management
################################################################

def dict_union(*args):
    """ Generate union of dictionaries.

    This helper function is used to combine dictionaries of keyword
    arguments so that they can be passed to the string format method.

    Arguments:
        *args: zero or more container objects either representing
             a mapping of key-value pairs or list-like iterable representing
             a list of key-value pairs

    Returns:
       (dict): the result of successively updating an initially-empty
           dictionary with the given arguments
    """
    accumulator = dict()
    for dictionary in args:
        accumulator.update(dictionary)
    return accumulator

################################################################
# filesystem
################################################################

def mkdir(dirname, exist_ok=False, parents=False):
    """Create directory, avoiding use of os.mkdir.

    Note: os.mkdir can apparently cause stability issues with parallel
    filesystems (at least NERSC CSCRATCH circa 2/17, where it is
    apparently translated as "lfs mkdir -i"?) and is therefore to be
    avoided in scripting which might encounter such filesystems.

    Arguments:
        dirname (str): name for directory to create
        parents (bool): make parent directories as necessary
    """
    if os.path.exists(dirname):
        if exist_ok:
            return
        else:
            raise FileExistsError(dirname)

    if parents:
        subprocess.call(["mkdir", "--parents", dirname])
    else:
        subprocess.call(["mkdir", dirname])

################################################################
# compression
################################################################

def is_compressible(filename, min_size=1048576, min_ratio=1.5):
    """Estimate if file is compressible.

    Arguments:
        filename (path-like): file to check
        min_size (int): minimum file size (in bytes) to consider
            being worth compressing
        min_ratio (float): minimum compression ratio to consider
            being compressible

    Returns:
        (bool): whether or not file should be compressed
    """
    # don't waste time compressing small files
    uncompressed_size = os.path.getsize(filename)
    if uncompressed_size < min_size:
        return False

    # test 4KB from 100 locations within the file for compressibility
    skip_size = uncompressed_size//100 - 4096
    compressor = zlib.compressobj()
    uncompressed_sample_size = 0
    compressed_sample_size = 0
    with open(filename, 'rb') as fp:
        # discard first 2KB as potential header info
        fp.seek(2048, 1)
        for i in range(100):
            uncompressed_block = fp.read(4096)
            compressed_block = compressor.compress(uncompressed_block)
            uncompressed_sample_size = uncompressed_sample_size + len(uncompressed_block)
            compressed_sample_size = compressed_sample_size + len(compressed_block)
            fp.seek(skip_size, 1)

    if (uncompressed_sample_size/compressed_sample_size) < min_ratio:
        return False
    else:
        return True

################################################################
# graph sorting
################################################################

def topological_sort(
    graph, initial_vertices=None,
    sorted_vertices=None, current_path=None
):
    """Topologically sort a directed graph using depth-first traversal.

    Arguments:
        graph (dict): graph with keys representing vertices and values
            as lists of edges
        initial_vertices (list, optional): starting vertices for depth-first
            traversal; defaults to all vertices
        sorted_vertices (list): internal list, used for recursion on intermediate
            sorted list
        current_path (list): internal list, used for detection of cycles

    Returns:
        (collections.deque): topologically-sorted list of items out-connected
            to initial_vertices

    Example:
        >>> graph = {1:[4,7], 2:[], 3:[4,6], 4:[6], 5:[], 6:[8,9,10], 7:[10], 8:[], 9:[], 10:[]}
        >>> mcscript.utils.topological_sort(graph, [1])
        deque([1, 7, 4, 6, 10, 9, 8])
        >>> mcscript.utils.topological_sort(graph, [1])
        deque([1, 7, 4, 6, 10, 9, 8])
        >>> mcscript.utils.topological_sort(graph, [1,2,3])
        deque([3, 2, 1, 7, 4, 6, 10, 9, 8])
    """
    if initial_vertices is None:
        initial_vertices = graph.keys()
    if sorted_vertices is None:
        sorted_vertices = collections.deque()
    if current_path is None:
        current_path = []
    sorted_vertices = collections.deque(sorted_vertices)
    for vertex in sorted(initial_vertices):
        if vertex in sorted_vertices:
            continue
        if vertex in current_path:
            raise ValueError("graph is not directed-acyclic")
        current_path.append(vertex)
        child_vertices = graph[vertex]
        sorted_vertices = topological_sort(
            graph,
            initial_vertices=child_vertices,
            sorted_vertices=sorted_vertices,
            current_path=current_path
        )
        current_path.pop()
        sorted_vertices.appendleft(vertex)
    return sorted_vertices

################################################################
# timing tracking and estimation
################################################################

class TaskTimer(object):
    """A class for tracking timing statistics of tasks or subtasks.

    Attributes:
        start_time (float): time when class was instantiated
        end_time (float): time when remaining time has expired
        safety_factor (float): safety margin for required time
        minimum_time (float): minimum number of seconds for required time
        timings (list of float): elapsed time for past timings
    """

    def __init__(self, remaining_time, safety_factor=1.1, minimum_time=60):
        """Initialize TaskTimer with timing parameters.

        Arguments:
            remaining_time (float): amount of time (in seconds) remaining
            safety_factor (float, optional): safety margin for required time
            minimum_time (float, optional): minimum number of seconds for required time
        """
        self.start_time = time.time()
        self.end_time = remaining_time + self.start_time
        self.safety_factor = safety_factor
        self.minimum_time = minimum_time
        self.timings = []
        self._task_start_time = None

    @property
    def elapsed_time(self):
        """Time (in seconds) since timer was instantiated."""
        return time.time() - self.start_time

    @property
    def remaining_time(self):
        """Remaining time (in seconds) before InsufficientTime raised."""
        return max(0., self.end_time - time.time())

    @property
    def last_time(self):
        """Time (in seconds) for last timing."""
        if len(self.timings) == 0:
            return 0.
        return self.timings[-1]

    @property
    def average_time(self):
        """Average time (in seconds) of past timings."""
        if len(self.timings) == 0:
            return 0.
        return sum(self.timings)/len(self.timings)

    @property
    def max_time(self):
        """Maximum time (in seconds) for past timings."""
        if len(self.timings) == 0:
            return 0.
        return max(self.timings)

    @property
    def min_time(self):
        """Minimum time (in seconds) for past timings."""
        if len(self.timings) == 0:
            return 0.
        return min(self.timings)

    @property
    def required_time(self):
        """Estimated time (in seconds) for next timing."""
        return max(
            self.average_time*self.safety_factor,
            self.last_time*self.safety_factor,
            self.minimum_time
            )

    def start_timer(self):
        """Start timer.

        Raises:
            (mcscript.exception.InsufficientTime): required time is greater than remaining time
            (RuntimeError): timer already running
        """
        if self.required_time > self.remaining_time:
            raise exception.InsufficientTime(self.required_time)

        if self._task_start_time is not None:
            raise RuntimeError("timer already started")

        self._task_start_time = time.time()

    def cancel_timer(self):
        """Cancel timer without saving current timing information.

        Raises:
            (RuntimeError): timer not already running
        """
        if self._task_start_time is None:
            raise RuntimeError("timer not running")
        self._task_start_time = None

    def stop_timer(self):
        """Stop timer and save timing information.

        Returns:
            (float): current timing information

        Raises:
            (RuntimeError): timer not already running
        """
        if self._task_start_time is None:
            raise RuntimeError("timer not running")
        task_time = time.time() - self._task_start_time
        self.timings.append(task_time)
        self._task_start_time = None
        return task_time

################################################################
# coefficient management
################################################################

class CoefficientDict(collections.UserDict):
    """An extended dictionary which represents the coefficients of an algebraic
    expression.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if not isinstance(value, numbers.Number):
            raise ValueError("non-numeric coefficient: {}".format(value))
        elif value == 0. or value == 0:
            self.pop(key, 0)
        else:
            super().__setitem__(key, value)

    def __add__(self, rhs):
        """Add two CoefficientDicts, matching coefficients.
        """
        if not isinstance(rhs, CoefficientDict):
            raise TypeError("unsupported operand type(s) for +: 'CoefficientDict' and "+type_as_str(rhs))
        out = CoefficientDict()
        # add keys appearing in both dictionaries
        for key in (self.keys() & rhs.keys()):
            out[key] = self[key] + rhs[key]
        # copy keys appearing only on left side
        for key in (self.keys() - rhs.keys()):
            out[key] = self[key]
        # copy keys appearing only on right side
        for key in (rhs.keys() - self.keys()):
            out[key] = rhs[key]
        return out

    def __mul__(self, rhs):
        """Scalar multiply by a number.
        """
        if not (isinstance(rhs, numbers.Number)):
            raise TypeError("unsupported operand type(s) for *: 'CoefficientDict' and "+type_as_str(rhs))
        out = CoefficientDict()
        # return empty dict if multiplied by zero
        if rhs == 0:
            return out
        for key in self.keys():
            out[key] = self[key] * rhs
        return out

    def __sub__(self, rhs):
        """Subtract two CoefficientDicts, matching coefficients.

        Note: equivalent to self + (-1)*rhs.
        """
        if not isinstance(rhs, CoefficientDict):
            raise TypeError("unsupported operand type(s) for -: 'CoefficientDict' and "+type_as_str(rhs))
        return self + (-1)*rhs

    def __rmul__(self, lhs):
        """Left scalar multiply by a number.

        Note: equivalent to self*lhs since scalar multiplication is commutative.
        """
        if not (isinstance(lhs, numbers.Number)):
            raise TypeError("unsupported operand type(s) for *: "+type_as_str(lhs)+" and 'CoefficientDict'")
        return (self * lhs)

    def __truediv__(self, rhs):
        """Scalar divide by a number.

        Note: equivalent to self*(1/rhs).
        """
        if not (isinstance(rhs, numbers.Number)):
            raise TypeError("unsupported operand type(s) for /: 'CoefficientDict' and "+type_as_str(rhs))
        return self * (1/rhs)

    def __floordiv__(self, rhs):
        """Scalar floor divide by a number.

        Note: equivalent to self*(1//rhs).
        """
        if not (isinstance(rhs, numbers.Number)):
            raise TypeError("unsupported operand type(s) for //: 'CoefficientDict' and "+type_as_str(rhs))
        return self * (1//rhs)
