#!/bin/bash
# this wrapper provides a bash script as the submitted job file (to keep some variants of qsub happy, e.g., Univa)
# then invokes run script through bash (which will recognize shebang line) so execute permission is not necessary

echo "bash_job_wrapper"
echo

if [[ -f "${MCSCRIPT_SOURCE}" ]]
then
  echo "Sourcing file: ${MCSCRIPT_SOURCE}"
  source ${MCSCRIPT_SOURCE}
  echo
fi

echo "Running command: ${*}"
${*}
