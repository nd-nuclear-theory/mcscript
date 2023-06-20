# mcscript_init.csh
#
# Initialization code to source from .cshrc.
#
# Mark A. Caprio
# University of Notre Dame
#
# 1/27/16 (pjf): Created (ba)sh version.

export PATH=${MCSCRIPT_DIR}/tools:${PATH}
# export PYTHONPATH=${MCSCRIPT_DIR}:${PYTHONPATH}

#alias cdr='cd ${MCSCRIPT_WORK_HOME}/${MCSCRIPT_RUN_PREFIX}\!*'

cdr() {
    cd ${MCSCRIPT_WORK_HOME}/run$1
}
