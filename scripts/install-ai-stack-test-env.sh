#!/usr/bin/env bash
# Minimal, CI-identical install for ai_stack tests (LangChain / LangGraph / GoC regression).
# Use this when you only need `pytest ai_stack/tests` — not the full backend stack.
#
# Usage (from repository root):
#   chmod +x scripts/install-ai-stack-test-env.sh
#   ./scripts/install-ai-stack-test-env.sh
#
# Mirrors: .github/workflows/ai-stack-tests.yml
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if command -v python3 &>/dev/null; then
  PY=python3
elif command -v python &>/dev/null; then
  PY=python
else
  echo "Error: need python3 or python on PATH" >&2
  exit 1
fi

echo "Using: $($PY --version)"
echo "Repo:  $ROOT"

$PY -m pip install --upgrade pip
$PY -m pip install -e "./story_runtime_core"
$PY -m pip install -e "./ai_stack[test]"

echo "Verifying heavy stack (same imports as langgraph_runtime)..."
$PY -c "import langchain_core, langgraph; import ai_stack.langgraph_runtime; print('OK: langchain_core, langgraph, ai_stack.langgraph_runtime')"

echo ""
echo "Run tests (from repo root, PYTHONPATH optional if packages are installed editable):"
echo "  export PYTHONPATH=\"$ROOT\""
echo "  $PY -m pytest ai_stack/tests -q --tb=short"
