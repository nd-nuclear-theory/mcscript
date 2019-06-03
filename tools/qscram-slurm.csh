#!/bin/csh
# 09/12/17 (mac): Created.
# 03/31/18 (mac): Add search text.
# 06/02/19 (mac): Add full option handling and --hold option.


#
# Argument parsing and validation
#

if (($1 == "") || ($1 == "-h") || ($1 == "--help")) then
  echo "--------------------------------------------------------------"
  echo ""
  echo "  Syntax: qscram [--hold|--release] <search_text> ..."
  echo "          qscram [--hold|--release] --all"
  echo ""
  echo "--------------------------------------------------------------"
  echo ""

  exit
endif

set all = 0
set hold = 0
set release = 0

while ($1 =~ "-*")

  if ($1 == "--all") then
    set all = 1
  else if ($1 == "--hold") then
    echo gh
    set hold = 1
  else if ($1 == "--release") then
    set release = 1
  else 
    echo "Unrecognized option $1."
    exit
  endif

  shift

end

#
# Implementation
#

if ($hold) then
  set scram_command = "scontrol hold"
else if ($release) then
  set scram_command = "scontrol release"
else
  set scram_command = "scancel"
endif

if ($all) then
  echo "Full scram..."
  ${scram_command} -v `squeue --noheader -u $user -o "%.18i"`
else
  while ($1 != "")

    set text = $1
    echo "Filtered scram: ${text}"
    ${scram_command} -v `squeue --noheader -u $user -o "%.18i,%j,%q" | grep ${text} | cut --delimiter=, --fields=1`

    shift

  end
endif
