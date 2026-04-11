from pathlib import Path

p = Path("ai_stack/langgraph_runtime_executor.py")
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
i0 = next(i for i, l in enumerate(lines) if l.startswith("    def _package_output"))
body_lines = lines[i0:]
rest = body_lines[1:]
dedented = [l[4:] if l.startswith("    ") else l for l in rest]
header = '''"""LangGraph runtime: package_output node logic (extracted from langgraph_runtime_executor)."""

from __future__ import annotations

from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.goc_turn_seams import build_diagnostics_refs, repro_metadata_complete
from ai_stack.langgraph_runtime_state import RuntimeTurnState
from ai_stack.langgraph_runtime_tracking import _dist_version, _track
from ai_stack.operational_profile import build_operational_cost_hints_for_runtime_graph
from ai_stack.runtime_turn_contracts import (
    ADAPTER_INVOCATION_DEGRADED_NO_FALLBACK,
    ADAPTER_INVOCATION_LANGCHAIN_PRIMARY,
    EXECUTION_HEALTH_DEGRADED_GENERATION,
    EXECUTION_HEALTH_GRAPH_ERROR,
    EXECUTION_HEALTH_HEALTHY,
    EXECUTION_HEALTH_MODEL_FALLBACK,
)
from ai_stack.version import AI_STACK_SEMANTIC_VERSION


def package_runtime_graph_output(
    state: RuntimeTurnState,
    *,
    graph_name: str,
    graph_version: str,
) -> RuntimeTurnState:
'''
text = header + "".join(dedented)
text = text.replace("self.graph_name", "graph_name")
text = text.replace("self.graph_version", "graph_version")
Path("ai_stack/langgraph_runtime_package_output.py").write_text(text, encoding="utf-8")
print("ok", len(text))
