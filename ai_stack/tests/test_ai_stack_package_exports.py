"""Package-level exports: LangGraph runtime is optional at import time by design."""

from __future__ import annotations

import ai_stack


def test_langgraph_export_flag_matches_runtime_import() -> None:
    """When deps are installed, __init__ must re-export the graph executor (MCP uses light imports)."""
    from ai_stack.langgraph_runtime import RuntimeTurnGraphExecutor

    assert ai_stack.LANGGRAPH_RUNTIME_EXPORT_AVAILABLE is True
    assert "RuntimeTurnGraphExecutor" in ai_stack.__all__
    assert ai_stack.RuntimeTurnGraphExecutor is RuntimeTurnGraphExecutor
