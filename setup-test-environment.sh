#!/bin/bash
# Setup test environment - installs all required dependencies
#
# This script MUST be run before running any tests.
# It installs both production and test dependencies.
#
# Usage:
#   ./setup-test-environment.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}World of Shadows: Test Environment Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get repository root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Prefer python3 (common on Debian/Ubuntu); fall back to python (Windows/macOS venvs).
if command -v python3 &> /dev/null; then
    PYTHON_BIN=python3
elif command -v python &> /dev/null; then
    PYTHON_BIN=python
else
    echo -e "${RED}Error: Python not found (tried python3, python)${NC}" >&2
    echo "Please install Python 3.10+ and try again." >&2
    exit 1
fi

echo "Repository: $REPO_ROOT"
echo "Python: $($PYTHON_BIN --version)"
echo ""

# Install backend dependencies
echo -e "${YELLOW}Installing backend dependencies...${NC}"
cd backend

if [[ ! -f "requirements.txt" ]]; then
    echo -e "${RED}Error: backend/requirements.txt not found${NC}" >&2
    exit 1
fi

if [[ ! -f "requirements-test.txt" ]]; then
    echo -e "${RED}Error: backend/requirements-test.txt not found${NC}" >&2
    exit 1
fi

# Single install: requirements-test.txt includes "-r requirements.txt" (same directory).
echo "Installing production + test dependencies (requirements-test.txt)..."
$PYTHON_BIN -m pip install --upgrade pip -q
$PYTHON_BIN -m pip install -r requirements-test.txt -q

cd "$REPO_ROOT"

# Local packages: story runtime core + ai_stack with full test/runtime deps (LangChain / LangGraph).
# Without this, `from ai_stack import RuntimeTurnGraphExecutor` may succeed only when PYTHONPATH
# picks up partial installs; `LANGGRAPH_RUNTIME_EXPORT_AVAILABLE` stays False if imports fail.
if [[ -d "story_runtime_core" ]]; then
    echo -e "${YELLOW}Installing story_runtime_core (editable)...${NC}"
    $PYTHON_BIN -m pip install -e "./story_runtime_core" -q || echo -e "${YELLOW}  (story_runtime_core editable install skipped or failed)${NC}"
fi
if [[ -d "ai_stack" ]]; then
    echo -e "${YELLOW}Installing ai_stack[test] (editable, includes langchain-core / langgraph)...${NC}"
    $PYTHON_BIN -m pip install -e "./ai_stack[test]" -q || echo -e "${YELLOW}  (ai_stack[test] editable install skipped or failed)${NC}"
fi

# Verify critical dependencies
echo ""
echo -e "${YELLOW}Verifying critical dependencies...${NC}"

MISSING=()

packages=("flask" "sqlalchemy" "flask_sqlalchemy" "flask_migrate" "flask_limiter" "pytest" "pytest_asyncio" "langchain_core" "langgraph")

for pkg in "${packages[@]}"; do
    if $PYTHON_BIN -c "import ${pkg}" 2>/dev/null; then
        echo "  ✓ $pkg"
    else
        echo "  ✗ $pkg (MISSING)"
        MISSING+=("$pkg")
    fi
done

echo ""

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo -e "${RED}Error: Missing required packages:${NC}"
    for pkg in "${MISSING[@]}"; do
        echo "  - $pkg"
    done
    echo ""
    echo "Try running pip install again:"
    echo "  pip install -r backend/requirements.txt -r backend/requirements-test.txt"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All dependencies installed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "You can now run tests:"
echo "  python -m pytest tests/smoke/ -v"
echo "  python -m pytest backend/tests/ -v"
echo "  PYTHONPATH=$REPO_ROOT python -m pytest ai_stack/tests -q"
echo ""
