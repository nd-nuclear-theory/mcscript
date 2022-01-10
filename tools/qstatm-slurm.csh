#!/bin/csh
# qstatm-slurm.csh
#
# Mark A. Caprio
# University of Notre Dame
#
# 11/18/11 (mac): Created from qstatu and qstatloop.
# 11/07/17 (mac): [adaptation for slurm committed]
# 04/23/18 (mac): Add pass-through of arguments.
# 01/10/22 (mac): Adjust format to match sqs (but longer job name and sans user).

# Classic qstatm slurm (c. 2017): "%.18i %.9P %.9q %.25j %.8u %.8T %.10M %.14l %.6D %R"
# NERSC sqs uses: "%16i %2t %9u %12j  %5D %.10l %.10M   %20V %15q %20S %14f %15R"
# Follow sqs pattern, but expand job name length and suppress user:
#  "%16i %2t %25j  %5D %.10l %.10M   %20V %15q %20S %14f %15R"

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
   squeue -u $user -o "%16i %2t %25j  %5D %.10l %.10M   %20V %15q %20S %14f %15R" $argv
   if ($loop) sleep 5
end
