#!/bin/bash
# select_cpu_device wrapper script
# based on https://docs.nersc.gov/jobs/affinity/#perlmutter
export CUDA_VISIBLE_DEVICES=$SLURM_LOCALID
exec $*
