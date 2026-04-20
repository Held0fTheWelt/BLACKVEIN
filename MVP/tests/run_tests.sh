#!/usr/bin/env bash
# Thin wrapper: forwards all arguments to run_tests.py (cross-platform entry point).
# Default --suite all runs backend (e.g. tests/test_writers_room_routes.py), ai_stack
# (LangGraph Writers-Room / improvement seed graphs under ai_stack/tests/), and other trees.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
exec python3 run_tests.py "$@"
