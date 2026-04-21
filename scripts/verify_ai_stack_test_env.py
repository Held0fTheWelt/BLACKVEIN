"""Used by setup-test-environment.bat — avoids CMD parsing issues with inline -c strings."""
from __future__ import annotations

import langchain_core  # noqa: F401
import langgraph  # noqa: F401

import ai_stack
from ai_stack import RuntimeTurnGraphExecutor

assert ai_stack.LANGGRAPH_RUNTIME_EXPORT_AVAILABLE
assert RuntimeTurnGraphExecutor is not None
print("  [OK] ai_stack graph lane")
