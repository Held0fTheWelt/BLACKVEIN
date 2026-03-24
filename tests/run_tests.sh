#!/bin/bash
################################################################################
# World of Shadows — Complete Test Suite Runner
#
# Usage:
#   ./run_tests.sh                    # Full suite with coverage (default)
#   ./run_tests.sh quick              # Fast tests only (no coverage)
#   ./run_tests.sh coverage           # Full suite with detailed coverage report
#   ./run_tests.sh api                # API tests only
#   ./run_tests.sh security           # Security tests only
#   ./run_tests.sh verbose            # Full output with debugging
#   ./run_tests.sh help               # Show this help
################################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$TESTS_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
COVERAGE_DIR="$BACKEND_DIR/htmlcov"
REPORTS_DIR="$TESTS_DIR/reports"
JUNIT_REPORT="$REPORTS_DIR/pytest_report.xml"

# Create reports directory
mkdir -p "$REPORTS_DIR"

# Defaults
MODE="${1:-full}"
PYTHON_CMD="python3"
PYTEST_ARGS="-v --tb=short"

# Helper functions
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

show_help() {
    head -n 18 "$0" | tail -n +2
}

generate_failure_report() {
    local junit_file="$1"
    local report_file="$REPORTS_DIR/FAILED_TESTS_$(date +%Y%m%d_%H%M%S).txt"

    if [ ! -f "$junit_file" ]; then
        return
    fi

    # Extract failed tests from JUnit XML and generate report
    $PYTHON_CMD << 'PYTHON_EOF'
import xml.etree.ElementTree as ET
import sys
from pathlib import Path

junit_file = sys.argv[1]
report_file = sys.argv[2]

try:
    tree = ET.parse(junit_file)
    root = tree.getroot()

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
        sys.exit(0)

    with open(report_file, 'w') as f:
        f.write("=" * 90 + "\n")
        f.write("FAILED TESTS REPORT\n")
        f.write("=" * 90 + "\n")
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

    print(f"Report: {report_file}")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
PYTHON_EOF

    $PYTHON_CMD -c "
import xml.etree.ElementTree as ET
junit_file = '$junit_file'
report_file = '$report_file'

try:
    tree = ET.parse(junit_file)
    root = tree.getroot()
    failed_tests = [tc for tc in root.findall('.//testcase') if tc.find('failure') is not None]

    if failed_tests:
        with open(report_file, 'w') as f:
            f.write('=' * 90 + '\n')
            f.write('FAILED TESTS REPORT\n')
            f.write('=' * 90 + '\n')
            f.write(f'Total failures: {len(failed_tests)}\n')
            f.write('=' * 90 + '\n\n')

            for i, test in enumerate(failed_tests, 1):
                name = test.get('name')
                cls = test.get('classname')
                failure = test.find('failure')
                msg = failure.get('message', '') if failure is not None else ''
                txt = failure.text if failure is not None else ''

                f.write(f'\n{\"─\" * 90}\n')
                f.write(f'[{i}] {cls}::{name}\n')
                f.write(f'{\"─\" * 90}\n')
                if msg:
                    f.write(f'Message: {msg}\n\n')
                if txt:
                    f.write(f'Details:\n{txt}\n')

            f.write('\n' + '=' * 90 + '\n')
            f.write(f'Summary: {len(failed_tests)} test(s) failed\n')
            f.write('=' * 90 + '\n')
        print('📄 Failed tests report: $report_file')
except:
    pass
" 2>/dev/null
}

check_env() {
    print_header "Environment Check"

    # Check Python
    if ! command -v $PYTHON_CMD &> /dev/null; then
        print_error "Python not found. Install Python 3.10+"
        exit 1
    fi
    print_success "Python: $($PYTHON_CMD --version)"

    # Check pytest
    if ! $PYTHON_CMD -m pytest --version &> /dev/null; then
        print_error "pytest not installed. Run: pip install -r requirements-dev.txt"
        exit 1
    fi
    PYTEST_VERSION=$($PYTHON_CMD -m pytest --version | cut -d' ' -f2)
    print_success "pytest: $PYTEST_VERSION"

    # Check coverage
    if ! $PYTHON_CMD -m coverage --version &> /dev/null; then
        print_info "coverage not installed (optional). Run: pip install coverage"
    else
        COVERAGE_VERSION=$($PYTHON_CMD -m coverage --version | cut -d' ' -f3)
        print_success "coverage: $COVERAGE_VERSION"
    fi

    echo ""
}

run_full_tests() {
    print_header "Running Full Test Suite with Coverage"

    $PYTHON_CMD -m pytest \
        $PYTEST_ARGS \
        --cov=app \
        --cov-report=term-missing \
        --cov-report=html \
        --cov-fail-under=85 \
        --junit-xml="$JUNIT_REPORT" \
        tests

    TEST_EXIT=$?

    if [ $TEST_EXIT -eq 0 ]; then
        print_success "All tests passed!"
        print_info "Coverage report: $COVERAGE_DIR/index.html"
    else
        print_error "Tests failed with exit code $TEST_EXIT"
        echo ""
        generate_failure_report "$JUNIT_REPORT"
    fi

    return $TEST_EXIT
}

run_quick_tests() {
    print_header "Running Quick Test Suite (no coverage)"

    $PYTHON_CMD -m pytest \
        $PYTEST_ARGS \
        --no-cov \
        -x \
        --junit-xml="$JUNIT_REPORT" \
        tests

    TEST_EXIT=$?

    if [ $TEST_EXIT -eq 0 ]; then
        print_success "Quick tests passed!"
    else
        print_error "Tests failed with exit code $TEST_EXIT"
        echo ""
        generate_failure_report "$JUNIT_REPORT"
    fi

    return $TEST_EXIT
}

run_coverage_tests() {
    print_header "Running Full Test Suite with Detailed Coverage"

    $PYTHON_CMD -m pytest \
        $PYTEST_ARGS \
        --cov=app \
        --cov-report=term-missing:skip-covered \
        --cov-report=html \
        --cov-report=json \
        --cov-fail-under=85 \
        --junit-xml="$JUNIT_REPORT" \
        tests

    TEST_EXIT=$?

    if [ $TEST_EXIT -eq 0 ]; then
        print_success "All tests passed with coverage!"
        print_info "Detailed coverage report: $COVERAGE_DIR/index.html"

        # Show coverage summary
        echo ""
        print_info "Coverage summary:"
        $PYTHON_CMD -m coverage report --skip-covered
    else
        print_error "Tests failed with exit code $TEST_EXIT"
        echo ""
        generate_failure_report "$JUNIT_REPORT"
    fi

    return $TEST_EXIT
}

run_api_tests() {
    print_header "Running API Tests"

    $PYTHON_CMD -m pytest \
        $PYTEST_ARGS \
        --no-cov \
        -k "api" \
        --junit-xml="$JUNIT_REPORT" \
        tests

    TEST_EXIT=$?

    if [ $TEST_EXIT -eq 0 ]; then
        print_success "API tests passed!"
    else
        print_error "API tests failed with exit code $TEST_EXIT"
        echo ""
        generate_failure_report "$JUNIT_REPORT"
    fi

    return $TEST_EXIT
}

run_security_tests() {
    print_header "Running Security Tests"

    $PYTHON_CMD -m pytest \
        $PYTEST_ARGS \
        --no-cov \
        -k "security or csrf or auth or injection or xss or privilege" \
        --junit-xml="$JUNIT_REPORT" \
        tests

    TEST_EXIT=$?

    if [ $TEST_EXIT -eq 0 ]; then
        print_success "Security tests passed!"
    else
        print_error "Security tests failed with exit code $TEST_EXIT"
        echo ""
        generate_failure_report "$JUNIT_REPORT"
    fi

    return $TEST_EXIT
}

run_verbose_tests() {
    print_header "Running Full Test Suite (Verbose with Debug Output)"

    $PYTHON_CMD -m pytest \
        -vv \
        --tb=long \
        --capture=no \
        --cov=app \
        --cov-report=term-missing \
        --cov-fail-under=85 \
        --junit-xml="$JUNIT_REPORT" \
        tests

    TEST_EXIT=$?

    if [ $TEST_EXIT -eq 0 ]; then
        print_success "All tests passed!"
    else
        print_error "Tests failed with exit code $TEST_EXIT"
        echo ""
        generate_failure_report "$JUNIT_REPORT"
    fi

    return $TEST_EXIT
}

show_test_stats() {
    print_header "Test Suite Statistics"

    TEST_COUNT=$($PYTHON_CMD -m pytest --collect-only -q "$TEST_DIR" 2>/dev/null | tail -1 | grep -oE '[0-9]+' | head -1 || echo "?")
    print_info "Total tests discovered: $TEST_COUNT"

    TEST_FILES=$(find "$TEST_DIR" -name "test_*.py" | wc -l)
    print_info "Test files: $TEST_FILES"

    echo ""
}

# Main
case "$MODE" in
    help|-h|--help)
        show_help
        exit 0
        ;;
    quick)
        check_env
        show_test_stats
        run_quick_tests
        exit $?
        ;;
    coverage)
        check_env
        show_test_stats
        run_coverage_tests
        exit $?
        ;;
    api)
        check_env
        show_test_stats
        run_api_tests
        exit $?
        ;;
    security)
        check_env
        show_test_stats
        run_security_tests
        exit $?
        ;;
    verbose)
        check_env
        show_test_stats
        run_verbose_tests
        exit $?
        ;;
    full|*)
        check_env
        show_test_stats
        run_full_tests
        exit $?
        ;;
esac
