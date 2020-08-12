# mcscript_init.csh
#
# Initialization code to source from .cshrc.
#
# Mark A. Caprio
# University of Notre Dame
#
# 12/30/16 (mac): Created.

setenv PATH ${MCSCRIPT_DIR}/tools:${PATH}
# setenv PYTHONPATH ${MCSCRIPT_DIR}:${PYTHONPATH}

alias cdr 'cd ${MCSCRIPT_WORK_HOME}/${MCSCRIPT_RUN_PREFIX}\!*'
