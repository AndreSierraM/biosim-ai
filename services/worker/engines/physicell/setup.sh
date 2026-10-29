#!/usr/bin/env bash
# Build the BioSim two-cell PhysiCell binary (pinned 1.14.2).
# Usage: services/worker/engines/physicell/setup.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
VENDOR="$HERE/vendor"
CXX_BIN="${PHYSICELL_CPP:-g++-16}"

if ! command -v "$CXX_BIN" >/dev/null 2>&1; then
  echo "missing $CXX_BIN (brew install gcc, or set PHYSICELL_CPP)" >&2
  exit 1
fi
if [ ! -f "$VENDOR/Makefile" ]; then
  git clone --depth 1 --branch 1.14.2 https://github.com/MathCancer/PhysiCell "$VENDOR"
fi
cp "$HERE/model/custom.cpp" "$VENDOR/custom_modules/custom.cpp"
export PHYSICELL_CPP="$CXX_BIN"
make -C "$VENDOR" -j10
echo "built: $VENDOR/project"
