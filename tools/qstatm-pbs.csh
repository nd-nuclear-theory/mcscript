#!/bin/csh
# qstatm-pbs.csh -- display queue status for current user
#
# Syntax: qstatm [-] [args]
# With dash, refreshes every 5 seconds.
#
# Mark A. Caprio
# University of Notre Dame
#
# 11/18/11 (mac): created from qstatu and qstatloop
# 4/23/18 (mac): add pass-through of arguments

set loop = 0
if ("$1" == "-") then
   set loop = 1
   shift
endif

@ i = 0
while (($i == 0) || ($loop))
   @ i++
   clear
   echo "****************************************************************"
   qstat -u $user $argv
   if ($loop) sleep 5
end
