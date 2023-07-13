#!/bin/csh
# this wrapper provides a csh script as the submitted job file (to keep some variants of qsub happy, e.g., Univa)
# then invokes run script through csh (which will recognize shebang line) so execute permission is not necessary

echo "csh_job_wrapper"
echo

if ($?MCSCRIPT_SOURCE) then
  if (${MCSCRIPT_SOURCE} != "") then
    echo "Sourcing file: ${MCSCRIPT_SOURCE}"
    source ${MCSCRIPT_SOURCE}
    echo
  endif
endif

echo "Running command: ${argv}"
${argv}
