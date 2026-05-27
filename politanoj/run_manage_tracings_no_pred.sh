#!/bin/sh
#SBATCH -J run_manage_tracings_no_pred
#SBATCH -c 4
#SBATCH -n 1
#SBATCH --mem 10000
#SBATCH --output=logs/run_manage_tracings_no_pred_out.txt
#SBATCH --error=logs/run_manage_tracings_no_pred_err.txt

# If you need a specific partition, uncomment and adjust the next line.
#SBATCH -p xtreme

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CODE_PATH="${SCRIPT_DIR}"
CONFIG_FILE="${CODE_PATH}/manage_tracings_no_pred.conf"

if [ ! -f "${CONFIG_FILE}" ]; then
  echo "Config file not found: ${CONFIG_FILE}"
  exit 1
fi

. "${CONFIG_FILE}"

for var in RAW_TXT_DIR RENAMED_TXT_DIR METADATA_CSV OUTPUT_CSV; do
  if [ -z "${!var:-}" ]; then
    echo "Missing required config variable: ${var}"
    exit 1
  fi
done

if [ -n "${ENV_ACTIVATE:-}" ] && [ -f "${ENV_ACTIVATE}" ]; then
  # Use a shared or cluster Python environment if configured.
  # shellcheck source=/dev/null
  . "${ENV_ACTIVATE}"
elif [ -f "${REPO_ROOT}/.venv/bin/activate" ]; then
  . "${REPO_ROOT}/.venv/bin/activate"
elif [ -f "${REPO_ROOT}/.venv/Scripts/activate" ]; then
  . "${REPO_ROOT}/.venv/Scripts/activate"
else
  echo "No virtual environment activation script found."
  echo "Set ENV_ACTIVATE in ${CONFIG_FILE} or create ${REPO_ROOT}/.venv."
  exit 1
fi

pip install --quiet --upgrade pip
if [ -f "${REPO_ROOT}/requirements.txt" ]; then
  pip install --quiet -r "${REPO_ROOT}/requirements.txt"
fi

mkdir -p "${CODE_PATH}/logs"
mkdir -p "${RENAMED_TXT_DIR}"
mkdir -p "$(dirname "${OUTPUT_CSV}")"

python "${CODE_PATH}/rename_tracing_files.py" \
  --input_dir "${RAW_TXT_DIR}" \
  --output_dir "${RENAMED_TXT_DIR}"

python "${REPO_ROOT}/manage_tracings_no_pred.py" \
  --txt_dir "${RENAMED_TXT_DIR}" \
  --metadata_csv "${METADATA_CSV}" \
  --output_csv "${OUTPUT_CSV}"
