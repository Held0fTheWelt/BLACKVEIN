#!/usr/bin/env bash
# Thin wrapper: forwards all arguments to run_tests.py (cross-platform entry point).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
exec python3 run_tests.py "$@"
