#!/usr/bin/env bash
# Fail fast on any error or undefined var
set -euo pipefail

# --- CONFIG -------------------------------------------------------------
CONDA_ROOT="/home/jjc/miniforge3"
ENV_NAME="mail2do"
PROJECT_DIR="/home/jjc/mail2do"
# -----------------------------------------------------------------------

# Initialise conda *for this non-interactive shell*
source "${CONDA_ROOT}/etc/profile.d/conda.sh"
conda activate "${ENV_NAME}"

# Jump to project directory so relative paths work
cd "${PROJECT_DIR}"

# Run the tool **once** and let cron/systemd handle repetition
mail2do

