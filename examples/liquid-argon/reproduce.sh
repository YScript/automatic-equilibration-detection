#!/bin/bash

# Script to reproduce all results of paper from scratch.
# Note that you must have called `cleanup.sh` script first to clean up old files.
#
# PREREQUISITES
#
# This requires the conda Pythjon package environment management tool.

# Create conda environment with necessary tools.
if [ ! -d conda-env ]; then
    echo "Creating new conda environment ./conda-env containing versions of tools needed for reproducibility..."
    conda config --add channels http://conda.binstar.org/omnia
    conda create --yes --quiet -p conda-env --file environment.yml
fi
source activate ./conda-env

# Run simulations.
python simulate.py

# Analyze simulation data to generate figures.
if [ ! -e figures ]; then
    mkdir figures
fi
echo "Generating figures..."
python analyze-1.py
python analyze-2.py
python analyze-3.py
python analyze-4.py

# Deactivate conda environment.
source deactivate


