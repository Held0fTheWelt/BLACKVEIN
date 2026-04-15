#!/usr/bin/env bash
# Full Python test environment for ``python tests/run_tests.py`` (all suites).
# Installs backend, frontend, administration-tool, world-engine deps plus editable
# story_runtime_core and ai_stack[test] — same closure as setup-test-environment.sh.
#
# Usage (from repository root or from scripts/):
#   ./scripts/install-full-test-env.sh
#
# Mirrors: repository root setup-test-environment.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$ROOT/setup-test-environment.sh"
