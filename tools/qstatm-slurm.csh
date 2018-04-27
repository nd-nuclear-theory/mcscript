#!/bin/csh
# qstatm-slurm.csh
#
# Mark A. Caprio
# University of Notre Dame
#
# 11/18/11 (mac): created from qstatu and qstatloop
# 11/07/17 (mac): [adaptation for slurm committed]
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
   ## qstat -u $user
   # long = "%.18i %.9P %q %.8j %.8u %.25 %.10M %.9l %.6D %R"
   squeue -u $user -o "%.18i %.9P %.9q %.25j %.8u %.8T %.10M %.14l %.6D %R" $argv
   if ($loop) sleep 5
end
