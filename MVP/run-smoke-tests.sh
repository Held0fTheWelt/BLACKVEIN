#!/bin/bash
# Canonical smoke test runner for World of Shadows
#
# This script runs the official smoke test suite to validate repository health
# in clean and development environments.
#
# Usage:
#   ./run-smoke-tests.sh              # Run full smoke suite (140 tests)
#   ./run-smoke-tests.sh --quick      # Run fast smoke tests only
#   ./run-smoke-tests.sh --verbose    # Run with detailed output
#
# What it validates:
#   - Backend startup and initialization (no errors)
#   - Database connectivity and schema
#   - Runtime routing bootstrap and initialization
#   - Content module YAML validity and consistency
#   - Core API endpoints (health checks)
#
# Exit codes:
#   0 - All smoke tests passed
#   1 - Some smoke tests failed
#   2 - Missing dependencies or configuration error

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
VERBOSE=""
QUICK=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            VERBOSE="--verbose"
            shift
            ;;
        --quick|-q)
            QUICK="true"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--verbose] [--quick] [--help]"
            echo ""
            echo "Options:"
            echo "  --verbose, -v   Run with detailed output"
            echo "  --quick, -q     Run fast smoke tests only"
            echo "  --help, -h      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 2
            ;;
    esac
done

# Check if pytest is available
if ! command -v python &> /dev/null; then
    echo -e "${RED}Error: Python not found${NC}" >&2
    echo "Please install Python 3.10+ and try again." >&2
    exit 2
fi

if ! python -m pytest --version &> /dev/null; then
    echo -e "${RED}Error: pytest not installed${NC}" >&2
    echo "Run: pip install -r backend/requirements-test.txt" >&2
    exit 2
fi

# Get repository root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo -e "${YELLOW}===============================================${NC}"
echo -e "${YELLOW}World of Shadows: Canonical Smoke Test Suite${NC}"
echo -e "${YELLOW}===============================================${NC}"
echo ""
echo "Repository: $REPO_ROOT"
echo "Python: $(python --version)"
echo "Pytest: $(python -m pytest --version)"
echo ""

# Build pytest command
PYTEST_CMD="python -m pytest tests/smoke/"

if [[ -z "$VERBOSE" ]]; then
    PYTEST_CMD="$PYTEST_CMD -v"
else
    PYTEST_CMD="$PYTEST_CMD -vv"
fi

PYTEST_CMD="$PYTEST_CMD --tb=short"

# Add quick filter if requested
if [[ -n "$QUICK" ]]; then
    PYTEST_CMD="$PYTEST_CMD -m 'not slow'"
    echo -e "${YELLOW}Running fast smoke tests only...${NC}"
    echo ""
else
    echo -e "${YELLOW}Running full smoke test suite...${NC}"
    echo ""
fi

# Run the smoke tests
if eval "$PYTEST_CMD"; then
    echo ""
    echo -e "${GREEN}===============================================${NC}"
    echo -e "${GREEN}✓ Smoke tests PASSED${NC}"
    echo -e "${GREEN}===============================================${NC}"
    echo ""
    echo "Repository health: GOOD"
    echo "All core systems are initialized and responding."
    exit 0
else
    echo ""
    echo -e "${RED}===============================================${NC}"
    echo -e "${RED}✗ Smoke tests FAILED${NC}"
    echo -e "${RED}===============================================${NC}"
    echo ""
    echo "Review the output above for details."
    echo "See docs/testing-setup.md for troubleshooting."
    exit 1
fi
