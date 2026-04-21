#!/bin/bash
# Setup test environment - installs all required dependencies
#
# This script MUST be run before running any tests.
# It installs both production and test dependencies.
#
# Security / hygiene (automated test suites, ed4815d+):
# - Installs only from requirement files in this repository (relative paths after ``cd``);
#   no remote pipe-to-shell bootstrap (only ``pip install -r`` from this tree).
# - Always invokes pip as ``python -m pip`` to reduce PATH hijack / wrong-interpreter risk.
# - ``set -euo pipefail`` below: fail fast; unset variables and pipe errors are not ignored.
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

# Install backend dependencies (same bar as .github/workflows/backend-tests.yml)
echo -e "${YELLOW}Installing backend dependencies...${NC}"
cd backend

if [[ ! -f "requirements-dev.txt" ]]; then
    echo -e "${RED}Error: backend/requirements-dev.txt not found${NC}" >&2
    exit 1
fi

echo "Installing production + dev/test dependencies (requirements-dev.txt)..."
$PYTHON_BIN -m pip install --upgrade pip -q
$PYTHON_BIN -m pip install -r requirements-dev.txt -q

cd "$REPO_ROOT"

# Local packages: story runtime core + ai_stack with full test/runtime deps (LangChain / LangGraph).
# Without this, `from ai_stack import RuntimeTurnGraphExecutor` may succeed only when PYTHONPATH
# picks up partial installs; `LANGGRAPH_RUNTIME_EXPORT_AVAILABLE` stays False if imports fail.
if [[ -d "story_runtime_core" ]]; then
    echo -e "${YELLOW}Installing story_runtime_core (editable)...${NC}"
    if ! $PYTHON_BIN -m pip install -e "./story_runtime_core" -q; then
        echo -e "${RED}Error: editable install of story_runtime_core failed${NC}" >&2
        exit 1
    fi
fi
if [[ -d "ai_stack" ]]; then
    echo -e "${YELLOW}Installing ai_stack[test] (editable, includes langchain-core / langgraph)...${NC}"
    if ! $PYTHON_BIN -m pip install -e "./ai_stack[test]" -q; then
        echo -e "${RED}Error: editable install of ai_stack[test] failed${NC}" >&2
        exit 1
    fi
fi

# Other components needed for ``python tests/run_tests.py --suite all`` (orchestrator cwd per suite).
if [[ -f "frontend/requirements-dev.txt" ]]; then
    echo -e "${YELLOW}Installing frontend test dependencies...${NC}"
    $PYTHON_BIN -m pip install -r frontend/requirements-dev.txt -q
fi
if [[ -f "administration-tool/requirements-dev.txt" ]]; then
    echo -e "${YELLOW}Installing administration-tool test dependencies...${NC}"
    $PYTHON_BIN -m pip install -r administration-tool/requirements-dev.txt -q
fi
if [[ -f "world-engine/requirements-dev.txt" ]]; then
    echo -e "${YELLOW}Installing world-engine test dependencies...${NC}"
    $PYTHON_BIN -m pip install -r world-engine/requirements-dev.txt -q
fi

echo -e "${YELLOW}Ensuring Python 3.14-safe pytest-asyncio range...${NC}"
$PYTHON_BIN -m pip install --upgrade "pytest-asyncio>=1.3,<2" -q

# Verify critical dependencies
echo ""
echo -e "${YELLOW}Verifying critical dependencies...${NC}"

MISSING=()

packages=("flask" "sqlalchemy" "flask_sqlalchemy" "flask_migrate" "flask_limiter" "pytest" "pytest_asyncio" "langchain_core" "langgraph" "fastapi" "httpx")

for pkg in "${packages[@]}"; do
    if $PYTHON_BIN -c "import ${pkg}" 2>/dev/null; then
        echo "  ✓ $pkg"
    else
        echo "  ✗ $pkg (MISSING)"
        MISSING+=("$pkg")
    fi
done

if $PYTHON_BIN -c 'from importlib.metadata import version; raw=version("pytest-asyncio"); parts=raw.split("+", 1)[0].split(".", 3); major=int(parts[0]); minor=int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0; assert (major == 1 and minor >= 3) or (major > 1 and major < 2), f"pytest-asyncio {raw} is outside required range >=1.3,<2"; print(f"  ✓ pytest-asyncio version {raw} (>=1.3,<2)")'; then
    :
else
    echo -e "${RED}Error: pytest-asyncio must be upgraded to >=1.3,<2.${NC}"
    exit 1
fi

echo ""

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo -e "${RED}Error: Missing required packages:${NC}"
    for pkg in "${MISSING[@]}"; do
        echo "  - $pkg"
    done
    echo ""
    echo "Try running pip install again from repo root (see setup-test-environment.sh)."
    exit 1
fi

# Same surface as tests/run_tests.py ``_probe_ai_stack_langgraph_lane`` / engine CI.
echo -e "${YELLOW}Verifying ai_stack LangGraph export (RuntimeTurnGraphExecutor)...${NC}"
if ! PYTHONPATH="$REPO_ROOT" $PYTHON_BIN -c "
import langchain_core, langgraph, ai_stack
assert ai_stack.LANGGRAPH_RUNTIME_EXPORT_AVAILABLE
from ai_stack import RuntimeTurnGraphExecutor
assert RuntimeTurnGraphExecutor is not None
print('  ✓ ai_stack graph lane OK')
"; then
    echo -e "${RED}Error: ai_stack LangGraph export check failed.${NC}" >&2
    echo "Ensure: pip install -e ./story_runtime_core && pip install -e \"./ai_stack[test]\"" >&2
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All dependencies installed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "You can now run the full Python orchestrator (from repo root):"
echo "  python tests/run_tests.py"
echo "Or component-only:"
echo "  python -m pytest tests/smoke/ -v"
echo "  python -m pytest backend/tests/ -v"
echo "  PYTHONPATH=$REPO_ROOT python -m pytest ai_stack/tests -q"
echo ""
