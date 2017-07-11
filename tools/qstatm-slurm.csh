#!/bin/csh
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
   ## qstat -u $user
   # long = "%.18i %.9P %.8j %.8u %.25 %.10M %.9l %.6D %R"
   squeue -u $user -o "%.18i %.9P %.25j %.8u %.8T %.10M %.14l %.6D %R"
   if ($loop) sleep 5
end
