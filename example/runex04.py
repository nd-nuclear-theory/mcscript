"""runex04.py

  This example calls "env" to dump the current environment as viewed
  by the script and as viewed by the compute codes.  This is useful for
  debugging.

  Language: Python 3

  M. A. Caprio
  Department of Physics
  University of Notre Dame

  3/17/17 (mac): Created.

"""

import os

import mcscript

mcscript.init()

print(64*"-")
print("Python's environment (os.environ):")
for (variable,value) in sorted(os.environ.items()):
    print("{}={}".format(variable,value))
print()

print(64*"-")
print("Local invocation of env:")
mcscript.call(["env"],mode=mcscript.CallMode.kLocal)
print()

print(64*"-")
print("Invocation of env as serial compute code:")
mcscript.call(["env"],mode=mcscript.CallMode.kSerial)
print()

print(64*"-")
print("Invocation of env as hybrid compute code:")
mcscript.call(["env"],mode=mcscript.CallMode.kHybrid)
print()

################################################################
# termination
################################################################

mcscript.termination()
