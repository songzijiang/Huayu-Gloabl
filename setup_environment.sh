#!/usr/bin/env bash

set -euo pipefail

ENVIRONMENT_NAME="${1:-huayu-global}"
PYTHON_VERSION="3.11.9"
PIP_VERSION="23.2.1"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REQUIREMENTS_PATH="${SCRIPT_DIR}/requirements.txt"

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "This script supports Linux. Use setup_environment.ps1 on Windows." >&2
    exit 1
fi

if ! command -v conda >/dev/null 2>&1; then
    echo "Conda was not found. Install Miniconda or Anaconda, then reopen the shell." >&2
    exit 1
fi

if [[ ! -f "${REQUIREMENTS_PATH}" ]]; then
    echo "requirements.txt was not found at ${REQUIREMENTS_PATH}" >&2
    exit 1
fi

CONDA_BASE="$(conda info --base)"
CONDA_PYTHON="${CONDA_BASE}/bin/python"

if [[ ! -x "${CONDA_PYTHON}" ]]; then
    echo "The Conda base Python executable was not found at ${CONDA_PYTHON}" >&2
    exit 1
fi

echo "Preparing Conda environment '${ENVIRONMENT_NAME}'..."

ENVIRONMENT_JSON="$(conda env list --json)"

if printf '%s' "${ENVIRONMENT_JSON}" | "${CONDA_PYTHON}" -c \
    'import json, os, sys; name = sys.argv[1]; data = json.load(sys.stdin); raise SystemExit(0 if any(os.path.basename(path.rstrip(os.sep)) == name for path in data["envs"]) else 1)' \
    "${ENVIRONMENT_NAME}"; then
    echo "Environment already exists; pinned packages will be refreshed."
    conda install \
        -n "${ENVIRONMENT_NAME}" \
        "python=${PYTHON_VERSION}" \
        "pip=${PIP_VERSION}" \
        -y
else
    conda create \
        -n "${ENVIRONMENT_NAME}" \
        "python=${PYTHON_VERSION}" \
        "pip=${PIP_VERSION}" \
        -y
fi

echo "Installing compiled geospatial dependencies..."
conda install \
    -n "${ENVIRONMENT_NAME}" \
    -c conda-forge \
    "gdal=3.6.2" \
    "rasterio=1.3.9" \
    "cartopy=0.22.0" \
    "pyproj=3.7.2" \
    "shapely=2.0.5" \
    "h5py=3.10.0" \
    "netcdf4=1.6.4" \
    -y

echo "Installing the pinned Python package snapshot..."
conda run -n "${ENVIRONMENT_NAME}" \
    python -m pip install -r "${REQUIREMENTS_PATH}"

echo "Verifying dependencies and core imports..."
conda run -n "${ENVIRONMENT_NAME}" python -m pip check
conda run -n "${ENVIRONMENT_NAME}" python -c \
    "import jacksung, numpy, scipy, rasterio, PIL, torch; print(f'Python environment OK; PyTorch={torch.__version__}; CUDA={torch.version.cuda}; CUDA available={torch.cuda.is_available()}')"

echo
echo "Environment setup complete."
echo "Run inference with:"
echo "conda run -n ${ENVIRONMENT_NAME} python HuayuGlobal.py"
