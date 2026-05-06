"""Used by setup-test-environment.bat — avoids CMD parsing issues with inline -c strings."""
from __future__ import annotations

from pathlib import Path
import sys

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import langchain_core  # noqa: E402, F401
import ai_stack  # noqa: E402, F401 — Reviver patch runs in ai_stack package init
import langgraph  # noqa: E402, F401
from ai_stack import RuntimeTurnGraphExecutor

assert ai_stack.LANGGRAPH_RUNTIME_EXPORT_AVAILABLE
assert RuntimeTurnGraphExecutor is not None
print("  [OK] ai_stack graph lane")
