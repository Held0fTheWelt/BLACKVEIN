#!/usr/bin/env python3
"""
World of Shadows — multi-component test runner.

Runs pytest in each component tree (backend, frontend, administration-tool, world-engine, database)
with a separate working directory per component. Optional scope filters apply only to
the backend suite (pytest markers).

Usage:
    python run_tests.py
    python run_tests.py --suite backend
    python run_tests.py --suite backend --scope contracts
    python run_tests.py --suite all --quick
    python run_tests.py --help
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Paths
TESTS_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = TESTS_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
ADMIN_TOOL_DIR = PROJECT_ROOT / "administration-tool"
WORLD_ENGINE_DIR = PROJECT_ROOT / "world-engine"
DATABASE_DIR = PROJECT_ROOT / "database"
REPORTS_DIR = TESTS_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Human-readable titles for each component (English)
SUITE_DISPLAY_NAMES: dict[str, str] = {
    "backend": "Backend (Flask API and services)",
    "frontend": "Frontend (player/public UI)",
    "administration": "Administration tool (proxy and UI)",
    "engine": "World engine (runtime and HTTP/WS)",
    "database": "Database (migrations and tooling)",
}

# Optional backend-only filter: CLI value -> pytest -m marker name
BACKEND_SCOPE_MARKERS: dict[str, str] = {
    "contracts": "contract",
    "integration": "integration",
    "e2e": "e2e",
    "security": "security",
}

# Matches backend/pytest.ini coverage gate when running backend tests
BACKEND_COV_FAIL_UNDER = "85"
FRONTEND_COV_FAIL_UNDER = "92"
DEFAULT_COV_FAIL_UNDER = "80"


class Colors:
    OKBLUE = "\033[0;34m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str) -> None:
    line = "=" * 70
    print(f"{Colors.OKBLUE}{line}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{line}{Colors.ENDC}")


def print_success(text: str) -> None:
    print(f"{Colors.OKGREEN}[OK] {text}{Colors.ENDC}")


def print_error(text: str) -> None:
    print(f"{Colors.FAIL}[FAIL] {text}{Colors.ENDC}")


def print_info(text: str) -> None:
    print(f"{Colors.WARNING}[INFO] {text}{Colors.ENDC}")


def check_environment() -> bool:
    print_header("Environment check")
    try:
        import pytest

        print_success(f"pytest: {pytest.__version__}")
    except ImportError:
        print_error("pytest is not installed. Install dev dependencies (e.g. backend/requirements-dev.txt).")
        return False
    try:
        import coverage

        print_success(f"coverage: {coverage.__version__}")
    except ImportError:
        print_info("coverage not installed (optional).")
    print()
    return True


def show_test_stats(suites: dict[str, Path]) -> None:
    print_header("Test collection (collect-only)")
    for suite_name, suite_dir in suites.items():
        test_root = suite_dir / "tests"
        if not test_root.is_dir():
            print_info(f"{suite_name}: no tests directory")
            continue
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(suite_dir),
            )
            out = (result.stdout or "") + (result.stderr or "")
            collected_line = None
            for line in out.split("\n"):
                if "collected" in line.lower() and any(c.isdigit() for c in line):
                    collected_line = line.strip()
                    break
            if collected_line:
                print_info(f"{suite_name}: {collected_line}")
            else:
                print_info(f"{suite_name}: (could not parse collection output)")
        except Exception as exc:
            print_info(f"{suite_name}: collect-only failed ({exc})")
    print()


def get_suite_configs(suite_names: list[str]) -> dict[str, Path]:
    all_suites: dict[str, Path] = {
        "backend": BACKEND_DIR,
        "frontend": FRONTEND_DIR,
        "administration": ADMIN_TOOL_DIR,
        "engine": WORLD_ENGINE_DIR,
        "database": DATABASE_DIR,
    }
    if "all" in suite_names:
        return dict(all_suites)
    result: dict[str, Path] = {}
    for name in suite_names:
        if name in all_suites:
            result[name] = all_suites[name]
        else:
            print_error(f"Unknown suite: {name}")
    return result if result else dict(all_suites)


def _cov_fail_under_for_suite(suite_name: str) -> str:
    if suite_name == "backend":
        return BACKEND_COV_FAIL_UNDER
    if suite_name == "frontend":
        return FRONTEND_COV_FAIL_UNDER
    return DEFAULT_COV_FAIL_UNDER


def build_pytest_argv(
    *,
    suite_name: str,
    quick: bool,
    coverage_mode: bool,
    verbose: bool,
    scope: str,
) -> list[str]:
    """Build pytest arguments for one component run (cwd = that component)."""
    cov_target = "app" if suite_name in ("backend", "frontend") else "."
    cov_under = _cov_fail_under_for_suite(suite_name)

    if quick:
        argv = ["-v", "--tb=short", "--no-cov", "-x"]
        if suite_name == "backend" and scope in BACKEND_SCOPE_MARKERS:
            argv.extend(["-m", BACKEND_SCOPE_MARKERS[scope]])
        argv.append("tests")
        return argv

    if coverage_mode:
        argv = [
            "-v",
            "--tb=short",
            f"--cov={cov_target}",
            "--cov-report=term-missing:skip-covered",
            "--cov-report=html",
            f"--cov-fail-under={cov_under}",
        ]
    elif verbose:
        argv = [
            "-vv",
            "--tb=long",
            "-s",
            f"--cov={cov_target}",
            "--cov-report=term-missing",
            f"--cov-fail-under={cov_under}",
        ]
    else:
        argv = [
            "-v",
            "--tb=short",
            f"--cov={cov_target}",
            "--cov-report=term-missing",
            f"--cov-fail-under={cov_under}",
        ]

    # Backend-only marker filter (optional)
    if suite_name == "backend" and scope in BACKEND_SCOPE_MARKERS:
        marker = BACKEND_SCOPE_MARKERS[scope]
        argv.extend(["-m", marker])

    argv.append("tests")
    return argv


def run_pytest(
    suite_name: str,
    suite_dir: Path,
    pytest_argv: list[str],
    run_title: str,
) -> bool:
    print_header(run_title)
    tests_dir = suite_dir / "tests"
    if not tests_dir.is_dir():
        print_error(f"Tests directory not found: {tests_dir}")
        return False

    junit_report = REPORTS_DIR / f"pytest_{suite_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
    cmd = [sys.executable, "-m", "pytest", *pytest_argv, f"--junit-xml={junit_report}"]
    try:
        result = subprocess.run(cmd, cwd=str(suite_dir))
        return result.returncode == 0
    except OSError as exc:
        print_error(f"Failed to run pytest: {exc}")
        return False


def run_tests_for_suites(
    suites: dict[str, Path],
    *,
    quick: bool,
    coverage_mode: bool,
    verbose: bool,
    scope: str,
) -> tuple[bool, dict[str, bool]]:
    all_passed = True
    results: dict[str, bool] = {}

    for suite_name, suite_dir in suites.items():
        display = SUITE_DISPLAY_NAMES.get(suite_name, suite_name)
        if scope in BACKEND_SCOPE_MARKERS:
            if suite_name == "backend":
                marker = BACKEND_SCOPE_MARKERS[scope]
                title = f"{display} — marker '{marker}'"
            else:
                print_info(
                    f"Scope '{scope}' applies only to backend; running full tests for '{suite_name}'."
                )
                title = f"{display} (full)"
        else:
            title = f"{display} (full)"

        argv = build_pytest_argv(
            suite_name=suite_name,
            quick=quick,
            coverage_mode=coverage_mode,
            verbose=verbose,
            scope=scope if suite_name == "backend" else "all",
        )
        ok = run_pytest(suite_name, suite_dir, argv, f"Running: {title}")
        results[suite_name] = ok
        all_passed = all_passed and ok
        if not ok:
            print_error(f"{suite_name} tests failed")
        else:
            print_success(f"{suite_name} tests passed")
        print()

    return all_passed, results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run pytest per component (backend, frontend, administration-tool, world-engine, database).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py
  python run_tests.py --suite backend
  python run_tests.py --suite frontend
  python run_tests.py --suite backend --scope contracts
  python run_tests.py --suite backend database --quick
  python run_tests.py --suite all --coverage
        """,
    )
    parser.add_argument(
        "--suite",
        nargs="+",
        default=["all"],
        choices=["backend", "frontend", "administration", "engine", "database", "all"],
        help="Component test tree to run (default: all)",
    )
    parser.add_argument(
        "--scope",
        default="all",
        choices=["all", "contracts", "integration", "e2e", "security"],
        help=(
            "Backend only: filter tests by pytest marker (contract, integration, e2e, security). "
            "Other components still run their full suite."
        ),
    )
    parser.add_argument("--quick", action="store_true", help="No coverage; stop on first failure")
    parser.add_argument("--coverage", action="store_true", help="Coverage with HTML report")
    parser.add_argument("--verbose", action="store_true", help="Verbose pytest and long tracebacks")

    args = parser.parse_args()

    if not check_environment():
        return 1

    suites = get_suite_configs(args.suite)
    if not suites:
        print_error("No valid suites specified")
        return 1

    show_test_stats(suites)

    all_passed, results = run_tests_for_suites(
        suites,
        quick=args.quick,
        coverage_mode=args.coverage,
        verbose=args.verbose,
        scope=args.scope,
    )

    print_header("Summary")
    for suite, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        symbol = Colors.OKGREEN if passed else Colors.FAIL
        print(f"{symbol}{status}{Colors.ENDC} - {suite}")

    print()
    if all_passed:
        print_success("All selected suites passed.")
        return 0
    print_error("One or more suites failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
