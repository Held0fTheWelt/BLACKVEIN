"""Package-level exports: LangGraph runtime is optional at import time by design."""

from __future__ import annotations

import importlib.util

import pytest

import ai_stack


def test_langgraph_exports_deferred_without_langchain_core() -> None:
    """Minimal environments (MCP / audit stubs) must not load ``langchain_core`` via this module."""
    if importlib.util.find_spec("langchain_core") is not None:
        pytest.skip("langchain_core installed; full export contract is checked in the companion test.")
    assert ai_stack.LANGGRAPH_RUNTIME_EXPORT_AVAILABLE is False
    assert isinstance(ai_stack.LANGGRAPH_RUNTIME_EXPORT_ERROR, str)
    assert "RuntimeTurnGraphExecutor" not in ai_stack.__all__


def test_langgraph_export_flag_matches_runtime_import() -> None:
    """When LangChain / LangGraph deps are installed, ``__init__`` re-exports the graph executor (CI merge bar)."""
    pytest.importorskip(
        "langchain_core",
        reason='graph lane: pip install -e "./story_runtime_core" -e "./ai_stack[test]" (see ai_stack/requirements-test.txt)',
    )
    pytest.importorskip(
        "langgraph",
        reason='graph lane: pip install -e "./ai_stack[test]"',
    )
    from ai_stack.langgraph.langgraph_runtime import RuntimeTurnGraphExecutor

    assert ai_stack.LANGGRAPH_RUNTIME_EXPORT_AVAILABLE is True
    assert ai_stack.LANGGRAPH_RUNTIME_EXPORT_ERROR is None
    assert "RuntimeTurnGraphExecutor" in ai_stack.__all__
    assert ai_stack.RuntimeTurnGraphExecutor is RuntimeTurnGraphExecutor
