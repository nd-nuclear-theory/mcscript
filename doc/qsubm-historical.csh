#!/bin/csh
# Mark Caprio
# last modified 2/7/13 (mac)

# for NERSC torque submission
# runs job with given mpp width and communicates this width to the job as MPP_WIDTH
#
# Environment: QSUBM_RUN_HOME -- directory in which job files are found and in which
# run subdirs should be made

if (($#argv < 4) || ($1 == "-h") || ($1 == "--help")) then
  echo "qsubm run queue walltime width [variables] <opts>"
  echo "   run as nnnn"
  echo "   walltime as [[dd:]hh:]mm"
  echo "   width as number of cores, or 's' for true serial job (no mppwidth request)"
  exit
endif

set run = $1
set queue = $2
set wall = $3
set width = $4
# shift so can pass on any additional arguments to qsub
shift
shift
shift 
shift

# optional variable list
#    comma delimited: VAR or VAR=VALUE
if ( ${width} == s ) then
   set width_param = 
   set varlist = MPP_WIDTH=1 
else 
   set width_param = "-l mppwidth=${width}"
   set varlist = MPP_WIDTH=${width} 
endif
if ($#argv >= 1) then
   set varlist = "${varlist},$1"
   shift
endif

set runparent = ${QSUBM_RUN_HOME}
set rundir = ${runparent}/run${run}
set runname = run${run}-mpp${width}

cd $runparent
if ( -e run${run}.job ) then
    set job = run${run}.job
else if ( -e run${run}.csh ) then
    set job = run${run}.csh
else if ( -e run${run}.py ) then
    set job = run${run}.py
endif

mkdir -p ${rundir}
cp -v ${job} ${rundir}

echo "run ${run} ==> ${runname}"
echo "queue ${queue}"
echo "walltime ${wall} min ==> ${wall}:00 sec"
echo "width ${width}"
echo "environment ${varlist}"

cd ${rundir}
ls -Fla ${job} 
echo "qsub ${job} -N ${runname} -q ${queue} -l walltime=${wall}:00 ${width_param} -v ${varlist} $argv"
qsub ${job} -N ${runname} -q ${queue} -l walltime=${wall}:00 ${width_param} -v ${varlist} $argv
