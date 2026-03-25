#!/bin/bash
################################################################################
# World of Shadows — Complete Test Suite Runner (Multi-Suite)
#
# Supports backend, administration-tool, and world-engine test suites
#
# Usage:
#   ./run_tests.sh                                  # All suites (default)
#   ./run_tests.sh --suite backend                  # Backend only
#   ./run_tests.sh --suite administration           # Administration-tool only
#   ./run_tests.sh --suite engine                   # World-engine only
#   ./run_tests.sh --suite backend administration   # Multiple suites
#   ./run_tests.sh --suite backend --quick          # Backend quick tests
#   ./run_tests.sh --suite all --coverage           # All suites with coverage
#   ./run_tests.sh help                             # Show this help
################################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
ADMIN_TOOL_DIR="$PROJECT_ROOT/administration-tool"
WORLD_ENGINE_DIR="$PROJECT_ROOT/world-engine"
REPORTS_DIR="$PROJECT_ROOT/test_reports"
PYTHON_CMD="python3"

# Create reports directory
mkdir -p "$REPORTS_DIR"

# Defaults
SUITES=("all")
MODE="full"
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
    head -n 25 "$0" | tail -n +2
}

# Parse arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --suite)
                shift
                SUITES=()
                while [[ $# -gt 0 ]] && [[ "$1" != --* ]]; do
                    SUITES+=("$1")
                    shift
                done
                continue
                ;;
            --quick)
                MODE="quick"
                shift
                ;;
            --coverage)
                MODE="coverage"
                shift
                ;;
            --verbose)
                MODE="verbose"
                shift
                ;;
            help|-h|--help)
                show_help
                exit 0
                ;;
            *)
                shift
                ;;
        esac
    done
}

# Get suites to run
get_suites() {
    local suite_list=()
    for suite in "${SUITES[@]}"; do
        case "$suite" in
            all)
                suite_list=("backend" "administration" "engine")
                break
                ;;
            backend)
                suite_list+=("backend")
                ;;
            administration)
                suite_list+=("administration")
                ;;
            engine)
                suite_list+=("engine")
                ;;
        esac
    done
    echo "${suite_list[@]}"
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

get_suite_dir() {
    local suite="$1"
    case "$suite" in
        backend)
            echo "$BACKEND_DIR"
            ;;
        administration)
            echo "$ADMIN_TOOL_DIR"
            ;;
        engine)
            echo "$WORLD_ENGINE_DIR"
            ;;
    esac
}

get_cov_target() {
    local suite="$1"
    if [ "$suite" = "backend" ]; then
        echo "app"
    else
        echo "."
    fi
}

run_tests_for_suite() {
    local suite="$1"
    local suite_dir=$(get_suite_dir "$suite")
    local test_dir="$suite_dir/tests"
    local junit_file="$REPORTS_DIR/pytest_${suite}_$(date +%Y%m%d_%H%M%S).xml"
    local cov_target=$(get_cov_target "$suite")

    if [ ! -d "$test_dir" ]; then
        print_error "Test directory not found: $test_dir"
        return 1
    fi

    local suite_display=""
    case "$suite" in
        backend)
            suite_display="Backend Test Suite"
            ;;
        administration)
            suite_display="Administration Tool Test Suite"
            ;;
        engine)
            suite_display="World Engine Test Suite"
            ;;
    esac

    print_header "Running $suite_display"

    local pytest_cmd=("$PYTHON_CMD" "-m" "pytest" "-v" "--tb=short")

    case "$MODE" in
        quick)
            pytest_cmd+=(--no-cov -x)
            ;;
        coverage)
            pytest_cmd+=(--cov="$cov_target" --cov-report=term-missing:skip-covered --cov-report=html --cov-fail-under=80)
            ;;
        verbose)
            pytest_cmd+=(-vv --tb=long -s --cov="$cov_target" --cov-report=term-missing)
            ;;
        *)
            pytest_cmd+=(--cov="$cov_target" --cov-report=term-missing --cov-fail-under=80)
            ;;
    esac

    pytest_cmd+=(--junit-xml="$junit_file" tests)

    cd "$suite_dir" || return 1
    "${pytest_cmd[@]}"
    local test_exit=$?
    cd - > /dev/null || return 1

    if [ $test_exit -eq 0 ]; then
        print_success "$suite tests passed!"
    else
        print_error "$suite tests failed with exit code $test_exit"
        generate_failure_report "$junit_file"
    fi

    echo ""
    return $test_exit
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
