#!/usr/bin/env bash
# Thin wrapper: forwards all arguments to run_tests.py (cross-platform entry point).
# Default --suite all runs all Python suite groups (component suites plus root tests/* groups).
# Optional lanes can be added with --with-playwright and --with-compose-smoke.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
exec python3 run_tests.py "$@"
