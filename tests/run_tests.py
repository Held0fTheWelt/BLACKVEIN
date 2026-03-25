#!/usr/bin/env python3
"""
World of Shadows — Complete Test Suite Runner (All Suites)

Cross-platform test runner for backend, administration-tool, and world-engine
with multiple modes and detailed reporting.

Usage:
    python run_tests.py                           # All suites (default)
    python run_tests.py --suite backend           # Backend only
    python run_tests.py --suite administration    # Administration-tool only
    python run_tests.py --suite engine            # World-engine only
    python run_tests.py --suite all               # All suites (explicit)
    python run_tests.py --suite backend --quick   # Backend quick tests
    python run_tests.py --help                    # Show this help
"""

import sys
import subprocess
import os
from pathlib import Path
import argparse
from datetime import datetime

# Setup
TESTS_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = TESTS_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
ADMIN_TOOL_DIR = PROJECT_ROOT / "administration-tool"
WORLD_ENGINE_DIR = PROJECT_ROOT / "world-engine"
REPORTS_DIR = PROJECT_ROOT / "tests" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ANSI colors
class Colors:
    HEADER = '\033[94m'
    OKBLUE = '\033[0;34m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """Print a formatted header."""
    line = "━" * 70
    print(f"{Colors.OKBLUE}{line}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{line}{Colors.ENDC}")

def print_success(text):
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text):
    """Print an info message."""
    print(f"{Colors.WARNING}ℹ {text}{Colors.ENDC}")

def check_environment():
    """Verify test environment is ready."""
    print_header("Environment Check")

    try:
        import pytest
        print_success(f"pytest: {pytest.__version__}")
    except ImportError:
        print_error("pytest not installed. Run: pip install -r backend/requirements-dev.txt")
        return False

    try:
        import coverage
        print_success(f"coverage: {coverage.__version__}")
    except ImportError:
        print_info("coverage not installed (optional). Run: pip install coverage")

    print()
    return True

def show_test_stats(suites):
    """Display test discovery statistics for selected suites."""
    print_header("Test Suite Statistics")

    for suite_name, suite_dir in suites.items():
        if not (suite_dir / "tests").exists():
            print_info(f"{suite_name}: No tests directory found")
            continue

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(suite_dir)
            )
            output = result.stdout + result.stderr
            # Extract test count from output
            for line in output.split('\n'):
                if 'test' in line.lower() and any(c.isdigit() for c in line):
                    print_info(f"{suite_name}: {line.strip()}")
                    break
        except Exception as e:
            print_info(f"{suite_name}: Could not get test count ({e})")

    print()

def run_pytest(suite_name, suite_dir, args, description):
    """Run pytest for a specific suite."""
    print_header(description)

    if not (suite_dir / "tests").exists():
        print_error(f"Test directory not found: {suite_dir / 'tests'}")
        return False

    # Add JUnit XML report generation
    junit_report = REPORTS_DIR / f"pytest_{suite_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"

    # Ensure tests path is correct
    cmd = [sys.executable, "-m", "pytest"] + args + [f"--junit-xml={junit_report}"]

    try:
        result = subprocess.run(cmd, cwd=str(suite_dir))
        return result.returncode == 0
    except Exception as e:
        print_error(f"Failed to run tests: {e}")
        return False

def get_suite_configs(suite_names):
    """Get configuration for selected suites."""
    all_suites = {
        'backend': BACKEND_DIR,
        'administration': ADMIN_TOOL_DIR,
        'engine': WORLD_ENGINE_DIR,
    }

    if 'all' in suite_names:
        return all_suites

    result = {}
    for suite in suite_names:
        if suite in all_suites:
            result[suite] = all_suites[suite]
        else:
            print_error(f"Unknown suite: {suite}")

    return result if result else all_suites

def run_tests_for_suites(suites, args):
    """Run tests for multiple suites."""
    all_passed = True
    results = {}

    for suite_name, suite_dir in suites.items():
        suite_display = {
            'backend': 'Backend Test Suite',
            'administration': 'Administration Tool Test Suite',
            'engine': 'World Engine Test Suite'
        }.get(suite_name, f'{suite_name} Test Suite')

        success = run_pytest(suite_name, suite_dir, args, f"Running {suite_display}")
        results[suite_name] = success
        all_passed = all_passed and success

        if not success:
            print_error(f"{suite_name} tests failed")
        else:
            print_success(f"{suite_name} tests passed!")
        print()

    return all_passed, results

def main():
    parser = argparse.ArgumentParser(
        description="World of Shadows — Complete Test Suite Runner (All Suites)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                        # All suites (default)
  python run_tests.py --suite backend        # Backend only
  python run_tests.py --suite administration # Administration-tool only
  python run_tests.py --suite engine         # World-engine only
  python run_tests.py --suite all            # All suites (explicit)
  python run_tests.py --suite backend --quick # Backend quick tests
        """
    )

    parser.add_argument(
        "--suite",
        nargs="+",
        default=["all"],
        choices=["backend", "administration", "engine", "all"],
        help="Test suite(s) to run (default: all)"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick tests without coverage"
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with detailed coverage report"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Run with full debug output"
    )

    args = parser.parse_args()

    # Check environment
    if not check_environment():
        return 1

    # Get suite configs
    suites = get_suite_configs(args.suite)

    if not suites:
        print_error("No valid suites specified")
        return 1

    # Show stats
    show_test_stats(suites)

    # Prepare pytest arguments
    if args.quick:
        pytest_args = [
            "-v", "--tb=short",
            "--no-cov",
            "-x",  # Stop on first failure
            "tests"
        ]
        description_suffix = "Quick Tests (no coverage)"
    elif args.coverage:
        pytest_args = [
            "-v", "--tb=short",
            "--cov=app" if "backend" in suites else "--cov=.",
            "--cov-report=term-missing:skip-covered",
            "--cov-report=html",
            "--cov-fail-under=80",
            "tests"
        ]
        description_suffix = "Tests with Detailed Coverage"
    elif args.verbose:
        pytest_args = [
            "-vv", "--tb=long",
            "-s",  # No capture
            "--cov=app" if "backend" in suites else "--cov=.",
            "--cov-report=term-missing",
            "tests"
        ]
        description_suffix = "Verbose Tests with Debug Output"
    else:
        # Default: full tests with coverage
        pytest_args = [
            "-v", "--tb=short",
            "--cov=app" if "backend" in suites else "--cov=.",
            "--cov-report=term-missing",
            "--cov-fail-under=80",
            "tests"
        ]
        description_suffix = "Full Tests with Coverage"

    # Run tests
    all_passed, results = run_tests_for_suites(suites, pytest_args)

    # Summary
    print_header("Test Summary")
    for suite, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        symbol = Colors.OKGREEN if passed else Colors.FAIL
        print(f"{symbol}{status}{Colors.ENDC} - {suite}")

    print()
    if all_passed:
        print_success("All test suites passed!")
        return 0
    else:
        print_error("Some test suites failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
