#!/bin/csh
# qstatm -- display queue status for current user
# Syntax: qstatm [-]
# With dash, refreshes every 5 seconds.
#
# Mark A. Caprio, University of Notre Dame
# created 11/18/11 (mac) from qstatu and qstatloop



set loop = 0
if ("$1" == "-") then
   set loop = 1
endif

@ i = 0
while (($i == 0) || ($loop))
   @ i++
   clear
   echo "****************************************************************"
   qstat -u $user
   if ($loop) sleep 5
end
