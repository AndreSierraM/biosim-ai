#!/usr/bin/env bash
# Full acceptance pipeline: boots a throwaway API and runs every spec scenario.
# Usage: ./run-acceptance-tests.sh [001] [003]   (optional spec filters)
set -euo pipefail
cd "$(dirname "$0")"
exec python3 -m acceptance.run_all "$@"
