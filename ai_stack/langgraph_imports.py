"""Single import site for ``langgraph.graph``.

``Reviver`` is patched at ``ai_stack`` package import (see ``langchain_reviver_compat``)
so LangGraph's ``LC_REVIVER = Reviver()`` does not emit pending deprecations.
"""
from __future__ import annotations

LANGGRAPH_IMPORT_ERROR: Exception | None = None
END = None
StateGraph = None

try:
    from langgraph.graph import END as _END, StateGraph as _StateGraph  # noqa: PLC0415

    END = _END
    StateGraph = _StateGraph
except Exception as exc:  # pragma: no cover - missing optional dependency
    LANGGRAPH_IMPORT_ERROR = exc
