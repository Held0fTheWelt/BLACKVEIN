"""Coarse operational signals for cost/performance awareness (non-financial).

These hints help operators and reviewers compare modes (retrieval route, fallback usage,
prompt size bands) without implying dollar estimates or production latency SLAs.
"""

from __future__ import annotations

from typing import Any

from ai_stack.capabilities import build_retrieval_trace

# Character buckets for prompt_text / model_prompt (honest coarse bands only).
_PROMPT_SMALL_MAX = 4000
_PROMPT_MEDIUM_MAX = 16000


def prompt_length_bucket(char_len: int) -> str:
    if char_len < 0:
        char_len = 0
    if char_len < _PROMPT_SMALL_MAX:
        return "small"
    if char_len < _PROMPT_MEDIUM_MAX:
        return "medium"
    return "large"


def build_operational_cost_hints_for_runtime_graph(
    *,
    retrieval: dict[str, Any] | None,
    generation: dict[str, Any] | None,
    graph_execution_health: str,
    model_prompt: str | None,
    fallback_path_taken: bool,
) -> dict[str, Any]:
    """Hints for LangGraph runtime turn diagnostics (World-Engine story path)."""
    retrieval = retrieval if isinstance(retrieval, dict) else {}
    generation = generation if isinstance(generation, dict) else {}
    meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    plen = len(model_prompt or "")
    return {
        "disclaimer": "coarse_operational_signals_not_financial_estimates",
        "retrieval_route": str(retrieval.get("retrieval_route") or ""),
        "retrieval_status": str(retrieval.get("status") or ""),
        "embedding_model_id": str(retrieval.get("embedding_model_id") or ""),
        "retrieval_hit_count": retrieval.get("hit_count"),
        "graph_execution_health": graph_execution_health,
        "adapter_invocation_mode": meta.get("adapter_invocation_mode"),
        "model_fallback_used": bool(generation.get("fallback_used")),
        "fallback_path_taken": bool(fallback_path_taken),
        "primary_generation_attempted": bool(generation.get("attempted")),
        "primary_generation_success": generation.get("success"),
        "prompt_length_chars": plen,
        "prompt_length_bucket": prompt_length_bucket(plen),
    }


def build_operational_cost_hints_from_retrieval(
    retrieval: dict[str, Any] | None,
) -> dict[str, Any]:
    """Slim hints for backend workflows (Improvement, admin surfaces) using retrieval dict only."""
    retrieval = retrieval if isinstance(retrieval, dict) else {}
    trace = build_retrieval_trace(retrieval)
    return {
        "disclaimer": "coarse_operational_signals_not_financial_estimates",
        "retrieval_route": str(retrieval.get("retrieval_route") or ""),
        "retrieval_status": str(retrieval.get("status") or ""),
        "embedding_model_id": str(retrieval.get("embedding_model_id") or ""),
        "retrieval_hit_count": retrieval.get("hit_count"),
        "retrieval_evidence_tier": trace.get("evidence_tier"),
        "retrieval_readiness_label": trace.get("readiness_label"),
        "evidence_lane_mix": trace.get("evidence_lane_mix"),
        "retrieval_quality_hint": trace.get("retrieval_quality_hint"),
        "retrieval_confidence_posture": trace.get("confidence_posture"),
        "retrieval_posture_summary": trace.get("retrieval_posture_summary"),
        "retrieval_trace_schema_version": trace.get("retrieval_trace_schema_version"),
    }
