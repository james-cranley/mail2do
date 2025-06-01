#!/usr/bin/env bash
set -euo pipefail

export HOME=/home/jjc
export PATH="/home/jjc/miniforge3/bin:$PATH"

CONDA_ROOT="/home/jjc/miniforge3"
ENV_NAME="mail2do"
PROJECT_DIR="/home/jjc/mail2do"

echo "DEBUG: ENV before activation" >> "${PROJECT_DIR}/cron.log"
env >> "${PROJECT_DIR}/cron.log"

source "${CONDA_ROOT}/etc/profile.d/conda.sh"
conda info --envs >> "${PROJECT_DIR}/cron.log"
conda activate "${ENV_NAME}"

cd "${PROJECT_DIR}"

which python >> "${PROJECT_DIR}/cron.log"
which mail2do >> "${PROJECT_DIR}/cron.log"

mail2do
