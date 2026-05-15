"""ADR-0041 Langfuse evidence surfaces (optional, parent-trace gated).

Emits a dedicated nested observation plus numeric scores **only** when Langfuse is
enabled and an active parent observation exists (``get_active_span()`` or root trace).
Never fabricates live/staging proof: this path keeps ``live_or_staging_evidence`` false;
``langfuse_trace_id`` / ``langfuse_observation_id`` are diagnostics only when the SDK returns them.

Contract version: ``adr0041_langfuse_evidence.v1``
"""

from __future__ import annotations

from typing import Any

ADR0041_LANGFUSE_EVIDENCE_SCHEMA_VERSION = "adr0041_langfuse_evidence.v1"
WOS_ADR0041_RUNTIME_INTELLIGENCE_OBSERVATION_NAME = "wos.adr0041.runtime_intelligence"

# Semantic score names (numeric 0.0–1.0); MCP / fetch_langfuse_trace_scores can surface them.
ADR0041_LANGFUSE_SCORE_PLAN_ENFORCED = "adr0041_plan_enforced_projection"
ADR0041_LANGFUSE_SCORE_READINESS_AGG = "adr0041_readiness_aggregation_emitted"
ADR0041_LANGFUSE_SCORE_READINESS_PREVIEW = "adr0041_readiness_co_authority_preview_emitted"
ADR0041_LANGFUSE_SCORE_PARENT_PRESENT = "adr0041_langfuse_parent_observation_present"


def build_adr0041_langfuse_evidence_payload(
    *,
    projection: dict[str, Any],
    story_session_id: str = "",
) -> dict[str, Any]:
    """Deterministic, JSON-safe summary for Langfuse span input/output (no SDK)."""
    vdr = projection.get("validator_dispatch_report")
    vdr = vdr if isinstance(vdr, dict) else {}
    mode = str(vdr.get("mode") or "").strip()
    feat = bool(vdr.get("feature_flag_enabled"))
    agg = projection.get("readiness_aggregation_decision")
    agg = agg if isinstance(agg, dict) else {}
    preview = projection.get("readiness_co_authority_preview")
    preview = preview if isinstance(preview, dict) else {}
    enforcement = projection.get("readiness_co_authority_enforcement")
    enforcement = enforcement if isinstance(enforcement, dict) else {}
    return {
        "schema_version": ADR0041_LANGFUSE_EVIDENCE_SCHEMA_VERSION,
        "story_session_id": str(story_session_id or "").strip() or None,
        "validator_dispatch_mode": mode or None,
        "validator_dispatch_feature_flag_enabled": feat,
        "readiness_aggregation_present": bool(agg),
        "readiness_aggregation_aggregated": str(agg.get("aggregated_readiness") or "").strip() or None,
        "readiness_co_authority_preview_present": bool(preview),
        "readiness_co_authority_enforcement_present": bool(enforcement),
        "proof_level": "local_only",
        "live_or_staging_evidence": False,
    }


def try_emit_adr0041_langfuse_runtime_intelligence_evidence(
    *,
    projection: dict[str, Any],
    story_session_id: str = "",
) -> dict[str, Any]:
    """Best-effort nested Langfuse span + scores for ADR-0041 runtime intelligence.

    Returns a JSON-safe diagnostics dict stored on ``runtime_intelligence_projection``.
    """
    payload = build_adr0041_langfuse_evidence_payload(
        projection=projection, story_session_id=story_session_id
    )
    out: dict[str, Any] = {
        "schema_version": ADR0041_LANGFUSE_EVIDENCE_SCHEMA_VERSION,
        "observation_name": WOS_ADR0041_RUNTIME_INTELLIGENCE_OBSERVATION_NAME,
        "proof_level": "local_only",
        "live_or_staging_evidence": False,
        "emitted": False,
        "langfuse_trace_id": None,
        "langfuse_observation_id": None,
        "payload_echo": payload,
    }
    try:
        from app.observability.langfuse_adapter import LangfuseAdapter
    except ImportError:
        out["reason"] = "langfuse_adapter_not_importable"
        return out

    adapter = LangfuseAdapter.get_instance()
    if not adapter.is_enabled():
        out["reason"] = "langfuse_disabled_or_not_ready"
        return out

    parent = adapter.resolve_parent_observation_for_nested_span()
    if parent is None:
        out["reason"] = "no_active_langfuse_parent_observation"
        return out

    meta = {
        **payload,
        "langfuse_evidence_contract": ADR0041_LANGFUSE_EVIDENCE_SCHEMA_VERSION,
        "observation_kind": "adr0041_runtime_intelligence",
    }
    diag = adapter.record_wos_nested_span_observation(
        name=WOS_ADR0041_RUNTIME_INTELLIGENCE_OBSERVATION_NAME,
        metadata=meta,
        input_data={"projection_summary": payload},
        output_data={"projection_keys": sorted(str(k) for k in projection.keys() if isinstance(k, str))[:40]},
    )
    out.update(diag)
    if not out.get("emitted"):
        return out

    # Numeric scores on root trace when available (Langfuse score API).
    vdr = projection.get("validator_dispatch_report")
    vdr = vdr if isinstance(vdr, dict) else {}
    mode = str(vdr.get("mode") or "").strip().lower()
    plan_enforced = 1.0 if mode == "plan_enforced" else 0.0
    agg = projection.get("readiness_aggregation_decision")
    has_agg = 1.0 if isinstance(agg, dict) and bool(agg) else 0.0
    prev = projection.get("readiness_co_authority_preview")
    has_prev = 1.0 if isinstance(prev, dict) and bool(prev) else 0.0

    score_diag = adapter.record_adr0041_langfuse_scores(
        scores=[
            (ADR0041_LANGFUSE_SCORE_PARENT_PRESENT, 1.0),
            (ADR0041_LANGFUSE_SCORE_PLAN_ENFORCED, plan_enforced),
            (ADR0041_LANGFUSE_SCORE_READINESS_AGG, has_agg),
            (ADR0041_LANGFUSE_SCORE_READINESS_PREVIEW, has_prev),
        ],
        comment="ADR-0041 runtime_intelligence projection evidence (local-only unless trace ids confirmed)",
    )
    out["score_emission"] = score_diag
    # IDs are for cross-checking with ``fetch_langfuse_trace`` / MCP tools only — not a live claim.
    out["live_or_staging_evidence"] = False
    out["proof_level"] = "local_only"
    return out
