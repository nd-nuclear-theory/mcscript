#!/bin/bash
# select_gpu_device wrapper script
# based on https://docs.nersc.gov/jobs/affinity/#perlmutter
export CUDA_VISIBLE_DEVICES=$SLURM_LOCALID
exec $*
