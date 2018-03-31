#!/bin/csh
# 9/12/17 (mac): Created.
# 3/31/18 (mac): Add search text.

if ($1 == "") then
  exit
endif

if ($1 == "--all") then
  echo "Full scram..."
  scancel -v `squeue --noheader -u $user -o "%.18i"`
else
  set text = $1
  echo "Filtered scram: ${text}"
  scancel -v `squeue --noheader -u $user -o "%.18i,%j,%q" | grep ${text} | cut --delimiter=, --fields=1`
endif
