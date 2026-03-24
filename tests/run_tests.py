#!/usr/bin/env python3
"""
World of Shadows — Complete Test Suite Runner (Python)

Cross-platform test runner with multiple modes and detailed reporting.

Usage:
    python run_tests.py                # Full suite with coverage (default)
    python run_tests.py --quick        # Fast tests only
    python run_tests.py --coverage     # Detailed coverage report
    python run_tests.py --api          # API tests only
    python run_tests.py --security     # Security tests only
    python run_tests.py --verbose      # Full debug output
    python run_tests.py --help         # Show this help
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
COVERAGE_DIR = BACKEND_DIR / "htmlcov"
REPORTS_DIR = TESTS_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

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
        print_error("pytest not installed. Run: pip install -r requirements-dev.txt")
        return False

    try:
        import coverage
        print_success(f"coverage: {coverage.__version__}")
    except ImportError:
        print_info("coverage not installed (optional). Run: pip install coverage")

    print()
    return True

def show_test_stats():
    """Display test discovery statistics."""
    print_header("Test Suite Statistics")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", str(TESTS_DIR)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(BACKEND_DIR)
        )
        output = result.stdout + result.stderr
        # Extract test count from last line
        for line in output.split('\n'):
            if 'test' in line.lower() and any(c.isdigit() for c in line):
                print_info(f"Tests discovered: {line.strip()}")
                break
    except Exception as e:
        print_info(f"Could not get test count: {e}")

    test_files = len(list(TESTS_DIR.glob("test_*.py")))
    print_info(f"Test files: {test_files}")
    print()

def parse_and_report_failures(junit_report):
    """Parse pytest JUnit XML report and generate human-readable failure report."""
    if not junit_report.exists():
        return None

    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(junit_report)
        root = tree.getroot()

        # Extract failed tests
        failed_tests = []
        for testcase in root.findall('.//testcase'):
            failure = testcase.find('failure')
            if failure is not None:
                failed_tests.append({
                    'name': testcase.get('name'),
                    'classname': testcase.get('classname'),
                    'message': failure.get('message', ''),
                    'text': failure.text or ''
                })

        if not failed_tests:
            return None

        # Generate human-readable report
        report_file = REPORTS_DIR / f"FAILED_TESTS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        with open(report_file, 'w') as f:
            f.write("=" * 90 + "\n")
            f.write("FAILED TESTS REPORT\n")
            f.write("=" * 90 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total failures: {len(failed_tests)}\n")
            f.write("=" * 90 + "\n\n")

            for i, test in enumerate(failed_tests, 1):
                full_name = f"{test['classname']}::{test['name']}"
                f.write(f"\n{'─' * 90}\n")
                f.write(f"[{i}] {full_name}\n")
                f.write(f"{'─' * 90}\n")

                if test['message']:
                    f.write(f"Message: {test['message']}\n\n")

                if test['text']:
                    f.write(f"Details:\n{test['text']}\n")

            f.write("\n" + "=" * 90 + "\n")
            f.write(f"Summary: {len(failed_tests)} test(s) failed\n")
            f.write("=" * 90 + "\n")

        return report_file
    except Exception as e:
        print_info(f"Could not parse test report: {e}")
        return None

def run_pytest(args, description):
    """Run pytest with given arguments."""
    print_header(description)

    # Add JUnit XML report generation for failure tracking
    junit_report = REPORTS_DIR / "pytest_report.xml"
    # Ensure tests path is correct (run from backend dir, tests are in tests/ subdir)
    args = [arg if arg != "." else "tests" for arg in args]
    cmd = [sys.executable, "-m", "pytest"] + args + [f"--junit-xml={junit_report}"]

    try:
        result = subprocess.run(cmd, cwd=str(BACKEND_DIR))

        # Generate failure report if tests failed
        if result.returncode != 0:
            report_file = parse_and_report_failures(junit_report)
            if report_file:
                print()
                print_info(f"📄 Failed tests report saved to: {report_file}")
                print()

        return result.returncode == 0
    except Exception as e:
        print_error(f"Failed to run tests: {e}")
        return False

def run_full_tests():
    """Run full test suite with coverage."""
    args = [
        "-v", "--tb=short",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-fail-under=85",
        "."
    ]

    success = run_pytest(args, "Running Full Test Suite with Coverage")

    if success:
        print_success("All tests passed!")
        print_info(f"Coverage report: {COVERAGE_DIR}/index.html")
    else:
        print_error("Tests failed")

    return success

def run_quick_tests():
    """Run quick test suite without coverage."""
    args = [
        "-v", "--tb=short",
        "--no-cov",
        "-x",  # Stop on first failure
        "."
    ]

    success = run_pytest(args, "Running Quick Test Suite (no coverage)")

    if success:
        print_success("Quick tests passed!")
    else:
        print_error("Tests failed")

    return success

def run_coverage_tests():
    """Run with detailed coverage reporting."""
    args = [
        "-v", "--tb=short",
        "--cov=app",
        "--cov-report=term-missing:skip-covered",
        "--cov-report=html",
        "--cov-report=json",
        "--cov-fail-under=85",
        "."
    ]

    success = run_pytest(args, "Running Full Test Suite with Detailed Coverage")

    if success:
        print_success("All tests passed with coverage!")
        print_info(f"Coverage report: {COVERAGE_DIR}/index.html")
    else:
        print_error("Tests failed")

    return success

def run_api_tests():
    """Run API tests only."""
    args = [
        "-v", "--tb=short",
        "--no-cov",
        "-k", "api",
        "."
    ]

    success = run_pytest(args, "Running API Tests")

    if success:
        print_success("API tests passed!")
    else:
        print_error("API tests failed")

    return success

def run_security_tests():
    """Run security-related tests."""
    args = [
        "-v", "--tb=short",
        "--no-cov",
        "-k", "security or csrf or auth or injection or xss or privilege",
        "."
    ]

    success = run_pytest(args, "Running Security Tests")

    if success:
        print_success("Security tests passed!")
    else:
        print_error("Security tests failed")

    return success

def run_verbose_tests():
    """Run with full debug output."""
    args = [
        "-vv", "--tb=long",
        "-s",  # No capture
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-fail-under=85",
        "."
    ]

    success = run_pytest(args, "Running Full Test Suite (Verbose with Debug Output)")

    if success:
        print_success("All tests passed!")
    else:
        print_error("Tests failed")

    return success

def main():
    parser = argparse.ArgumentParser(
        description="World of Shadows — Complete Test Suite Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py              # Full suite with coverage
  python run_tests.py --quick      # Fast tests only
  python run_tests.py --coverage   # Detailed coverage
  python run_tests.py --security   # Security tests only
        """
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
        "--api",
        action="store_true",
        help="Run API tests only"
    )
    parser.add_argument(
        "--security",
        action="store_true",
        help="Run security tests only"
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

    # Show stats
    show_test_stats()

    # Run tests based on mode
    if args.quick:
        success = run_quick_tests()
    elif args.coverage:
        success = run_coverage_tests()
    elif args.api:
        success = run_api_tests()
    elif args.security:
        success = run_security_tests()
    elif args.verbose:
        success = run_verbose_tests()
    else:
        success = run_full_tests()

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
