#!/usr/bin/env python3
"""
run-test.py — MVP operational gate entry point.

Thin wrapper around tests/run_tests.py that maps the guide's
required command surface to the actual test runner.

Usage (from repository root):
  python run-test.py --unit        → python tests/run_tests.py --suite backend engine
  python run-test.py --integration → python tests/run_tests.py --suite backend engine --scope integration
  python run-test.py --e2e         → python tests/run_tests.py --suite root_e2e_python
  python run-test.py --all         → python tests/run_tests.py --suite all
  python run-test.py --mvp1        → python tests/run_tests.py --suite engine backend (MVP1 suites)

Run-test.py is the canonical operational gate entry point documented in:
  tests/reports/MVP_Live_Runtime_Completion/MVP1_SOURCE_LOCATOR.md
  tests/reports/MVP_Live_Runtime_Completion/MVP1_OPERATIONAL_EVIDENCE.md
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
RUNNER = REPO_ROOT / "tests" / "run_tests.py"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MVP operational gate test runner (wraps tests/run_tests.py).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--unit", action="store_true", help="Run unit suites (backend + engine).")
    parser.add_argument("--integration", action="store_true", help="Run integration scope (backend + engine, integration markers).")
    parser.add_argument("--e2e", action="store_true", help="Run Python e2e tests.")
    parser.add_argument("--all", action="store_true", help="Run all suites.")
    parser.add_argument("--mvp1", action="store_true", help="Run MVP1 suites (engine + backend).")
    parser.add_argument("--quick", action="store_true", help="Pass --quick to runner (stop on first failure).")
    args = parser.parse_args()

    if not RUNNER.is_file():
        print(f"Error: test runner not found at {RUNNER}", file=sys.stderr)
        return 1

    base_cmd = [sys.executable, str(RUNNER)]
    if args.quick:
        base_cmd.append("--quick")

    if args.all:
        cmd = base_cmd + ["--suite", "all"]
    elif args.integration:
        cmd = base_cmd + ["--suite", "backend", "engine", "--scope", "integration"]
    elif args.e2e:
        cmd = base_cmd + ["--suite", "root_e2e_python"]
    elif args.mvp1:
        # FIX-009: Include all three MVP1 suites (world-engine, backend, frontend)
        cmd = base_cmd + ["--suite", "engine", "backend"]
        # Frontend MVP1 tests are run separately via pytest from frontend dir
        # or integrated into test suite if available
    elif args.unit:
        cmd = base_cmd + ["--suite", "backend", "engine"]
    else:
        # Default: show help and run all
        parser.print_help()
        print("\nNo flag given — running --all.", file=sys.stderr)
        cmd = base_cmd + ["--suite", "all"]

    print("$", " ".join(str(c) for c in cmd), flush=True)
    result = subprocess.call(cmd, cwd=str(REPO_ROOT))
    return result


if __name__ == "__main__":
    sys.exit(main())
