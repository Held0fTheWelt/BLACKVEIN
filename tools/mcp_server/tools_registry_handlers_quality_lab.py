"""MCP handlers for Quality Lab (ADR-0040, Phases 1 & 2).

Phase 1 exposes ``wos.quality_lab.review_judgments`` — semantic
interpretation of categorical LLM-as-a-Judge scores. Composes with the
existing ``fetch_langfuse_trace_scores`` tool: pass its output through
``trace_scores_payload`` to get the same scores enriched with severity
buckets, repair areas, problem clusters, missing-judge detection, and
prioritized improvement candidates.

Phase 2 exposes ``wos.quality_lab.review_trace`` — structural diagnostic
analysis of a Langfuse trace payload. Composes with ``fetch_langfuse_trace``:
pass its output through ``trace_payload`` (or pass ``raw_trace`` directly
for test fixtures) to get metadata coverage, runtime aspect summary,
beat/capability realization, authority clusters, span anomalies, and
prioritized trace-level improvement candidates.

Read-only. Never mutates runtime state, Langfuse evaluators, prompts, or
content. Deterministic runtime gates from ADR-0033 remain authoritative.
"""

from __future__ import annotations

from typing import Any, Callable

from ai_stack.quality_lab.judgment_interpreter import interpret_judgments
from ai_stack.quality_lab.trace_interpreter import interpret_trace
from tools.mcp_server.tools_registry_handlers_langfuse_verify import (
    _extract_metadata,
    _extract_path_summary_from_trace,
    _extract_runtime_aspect_ledger_from_trace,
    _get_observations,
)


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, str):
        if value.lower() in {"true", "1", "yes"}:
            return True
        if value.lower() in {"false", "0", "no"}:
            return False
    return None


def _extract_inputs(arguments: dict[str, Any]) -> tuple[dict[str, Any], bool | None, set[str] | None]:
    """Pull (scores, is_opening, expected_judge_names) out of the request.

    Accepts either:
      - ``scores``: bare ``{judge_name: {...}}`` mapping.
      - ``trace_scores_payload``: the full ``fetch_langfuse_trace_scores``
        response — we extract ``judge_scores`` and ``is_opening_trace``.
    """
    payload = arguments.get("trace_scores_payload")
    if isinstance(payload, dict):
        scores = payload.get("judge_scores") or {}
        is_opening = _coerce_bool(payload.get("is_opening_trace"))
    else:
        scores = arguments.get("scores") or {}
        is_opening = _coerce_bool(arguments.get("is_opening"))
    if not isinstance(scores, dict):
        scores = {}

    explicit = arguments.get("is_opening")
    if explicit is not None:
        coerced = _coerce_bool(explicit)
        if coerced is not None:
            is_opening = coerced

    expected = arguments.get("expected_judge_names")
    expected_names: set[str] | None = None
    if isinstance(expected, list):
        expected_names = {str(n) for n in expected if n}

    return scores, is_opening, expected_names


def _resolve_raw_trace(arguments: dict[str, Any]) -> dict[str, Any] | None:
    """Pull a raw Langfuse trace dict out of ``trace_payload`` or ``raw_trace``."""
    payload = arguments.get("trace_payload")
    if isinstance(payload, dict):
        raw = payload.get("raw_trace")
        if isinstance(raw, dict):
            return raw
    raw_direct = arguments.get("raw_trace")
    if isinstance(raw_direct, dict):
        return raw_direct
    return None


def _flatten_trace_metadata(raw_trace: dict[str, Any]) -> dict[str, Any]:
    """Merge trace.metadata with path_summary keys for analysis convenience."""
    metadata = dict(_extract_metadata(raw_trace) or {})
    metadata.setdefault("environment", raw_trace.get("environment"))
    path_summary = _extract_path_summary_from_trace(raw_trace) or {}
    for field in (
        "trace_origin",
        "execution_tier",
        "canonical_player_flow",
        "session_id",
        "canonical_turn_id",
        "environment",
        "module_id",
        "turn_number",
        "turn_kind",
        "runtime_mode",
        "generation_mode",
        "player_input_kind",
        "semantic_move_kind",
    ):
        value = path_summary.get(field)
        if value not in (None, "", []):
            metadata[field] = value
    return metadata


def _aspects_inner(raw_trace: dict[str, Any]) -> dict[str, Any]:
    """Return the inner aspect-keyed dict of the turn_aspect_ledger."""
    ledger = _extract_runtime_aspect_ledger_from_trace(raw_trace) or {}
    inner = ledger.get("turn_aspect_ledger") if isinstance(ledger, dict) else None
    return inner if isinstance(inner, dict) else {}


def _observation_names(raw_trace: dict[str, Any]) -> list[str]:
    return [
        str(obs.get("name")).strip()
        for obs in (_get_observations(raw_trace) or [])
        if isinstance(obs, dict) and obs.get("name")
    ]


def build_quality_lab_mcp_handlers() -> dict[str, Callable[..., dict[str, Any]]]:
    def wos_quality_lab_review_judgments(arguments: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(arguments, dict):
            return {
                "ok": False,
                "error": {"code": "invalid_input", "message": "arguments must be an object"},
            }
        scores, is_opening, expected_names = _extract_inputs(arguments)
        if not scores:
            return {
                "ok": False,
                "error": {
                    "code": "no_scores_provided",
                    "message": (
                        "Provide either 'scores' (a judge_name → entry mapping) "
                        "or 'trace_scores_payload' (full fetch_langfuse_trace_scores output)."
                    ),
                },
            }
        result = interpret_judgments(
            scores,
            is_opening=is_opening,
            expected_judge_names=expected_names,
        )
        return {"ok": True, **result}

    def wos_quality_lab_review_trace(arguments: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(arguments, dict):
            return {
                "ok": False,
                "error": {"code": "invalid_input", "message": "arguments must be an object"},
            }
        raw_trace = _resolve_raw_trace(arguments)
        if raw_trace is None:
            return {
                "ok": False,
                "error": {
                    "code": "no_trace_provided",
                    "message": (
                        "Provide either 'trace_payload' (full fetch_langfuse_trace output) "
                        "or 'raw_trace' (the raw Langfuse trace dict)."
                    ),
                },
            }
        trace_id = str(raw_trace.get("id") or raw_trace.get("trace_id") or "").strip()
        trace_name = str(raw_trace.get("name") or "").strip() or None
        is_opening_arg = _coerce_bool(arguments.get("is_opening"))
        metadata = _flatten_trace_metadata(raw_trace)
        aspects = _aspects_inner(raw_trace)
        observation_names = _observation_names(raw_trace)
        result = interpret_trace(
            trace_id=trace_id or None,
            trace_name=trace_name,
            trace_metadata=metadata,
            aspects_ledger=aspects,
            observation_names=observation_names,
            is_opening=is_opening_arg,
        )
        return {"ok": True, **result}

    return {
        "wos.quality_lab.review_judgments": wos_quality_lab_review_judgments,
        "wos.quality_lab.review_trace": wos_quality_lab_review_trace,
    }
