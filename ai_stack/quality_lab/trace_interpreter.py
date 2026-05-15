"""Trace-level diagnostic interpretation (ADR-0040 Phase 2).

Pure analysis of a Langfuse trace payload that has already been fetched
and pre-extracted by ``fetch_langfuse_trace`` and the matrix-row builder
in ``tools_registry_handlers_langfuse_verify``. Quality Lab does not call
Langfuse itself — the MCP handler composes with the existing tools and
hands the extracted material to this module.

Read-only. Never mutates runtime state, Langfuse evaluators, prompts, or
content. Deterministic runtime gates from ADR-0033 remain authoritative.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from ai_stack.langfuse_evaluator_catalog import (
    BACKEND_TURN_ROOT_TRACE_NAME,
    WORLD_ENGINE_OPENING_TRACE_NAME,
    WORLD_ENGINE_TURN_TRACE_NAME,
)
from ai_stack.runtime_aspect_ledger import ASPECT_KEYS
from ai_stack.quality_lab.schemas import user_decision_prompt


# Canonical aspect names come from the runtime ledger contract. Keeping this
# as an alias lets Quality Lab inspect traces without creating a second aspect
# taxonomy or a Table-B-shaped oracle list.
ASPECT_NAMES: tuple[str, ...] = tuple(ASPECT_KEYS)

# Metadata fields that should appear on a live-canonical trace. Mirrors
# the fields ``_extract_metadata`` + ``_extract_path_summary_from_trace``
# normally surface for downstream analysis.
EXPECTED_LIVE_METADATA_FIELDS: tuple[str, ...] = (
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
)

# Trace-name → trace-kind mapping. Names come from canonical catalog
# constants in ``ai_stack.langfuse_evaluator_catalog`` so renames stay in
# one place.
OPENING_TRACE_NAMES: frozenset[str] = frozenset({WORLD_ENGINE_OPENING_TRACE_NAME})
TURN_TRACE_NAMES: frozenset[str] = frozenset(
    {WORLD_ENGINE_TURN_TRACE_NAME, BACKEND_TURN_ROOT_TRACE_NAME}
)


def _coerce_str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lo = value.strip().lower()
        if lo in {"true", "1", "yes"}:
            return True
        if lo in {"false", "0", "no"}:
            return False
    return None


def classify_trace_kind(trace_name: str | None) -> str:
    """Return ``"opening"``, ``"turn"``, or ``"unknown"``."""
    n = _coerce_str(trace_name)
    if n in OPENING_TRACE_NAMES:
        return "opening"
    if n in TURN_TRACE_NAMES:
        return "turn"
    return "unknown"


def _present_metadata_fields(metadata: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    present: list[str] = []
    missing: list[str] = []
    for field in EXPECTED_LIVE_METADATA_FIELDS:
        value = metadata.get(field)
        if value is None or value == "" or value == []:
            missing.append(field)
        else:
            present.append(field)
    return present, missing


def _live_evidence_qualified(metadata: Mapping[str, Any]) -> tuple[bool, dict[str, Any]]:
    origin = _coerce_str(metadata.get("trace_origin")).lower()
    tier = _coerce_str(metadata.get("execution_tier")).lower()
    cpf = _coerce_bool(metadata.get("canonical_player_flow"))
    qualified = origin == "live_ui" and tier == "live" and cpf is True
    return qualified, {
        "trace_origin": metadata.get("trace_origin"),
        "execution_tier": metadata.get("execution_tier"),
        "canonical_player_flow": cpf,
        "qualified": qualified,
    }


def _aspect_record(ledger_aspects: Mapping[str, Any], aspect_name: str) -> dict[str, Any]:
    rec = ledger_aspects.get(aspect_name) if isinstance(ledger_aspects, Mapping) else None
    return rec if isinstance(rec, dict) else {}


def _aspect_block(record: Mapping[str, Any], block_name: str) -> dict[str, Any]:
    block = record.get(block_name) if isinstance(record, Mapping) else None
    return block if isinstance(block, dict) else {}


def _build_runtime_aspect_summary(aspects_ledger: Mapping[str, Any]) -> dict[str, Any]:
    states: dict[str, str] = {}
    failed: list[str] = []
    partial: list[str] = []
    not_applicable: list[str] = []
    missing: list[str] = []
    primary_failure: str | None = None
    for name in ASPECT_NAMES:
        rec = _aspect_record(aspects_ledger, name)
        status = _coerce_str(rec.get("status")) if rec else ""
        if not rec:
            states[name] = "missing"
            missing.append(name)
            continue
        states[name] = status or "missing"
        if status == "failed":
            failed.append(name)
            if primary_failure is None:
                primary_failure = _coerce_str(rec.get("failure_reason")) or None
        elif status == "partial":
            partial.append(name)
            if primary_failure is None:
                primary_failure = _coerce_str(rec.get("failure_reason")) or None
        elif status == "not_applicable":
            not_applicable.append(name)
        elif not status:
            missing.append(name)
    return {
        "aspect_states": states,
        "failed_aspects": failed,
        "partial_aspects": partial,
        "not_applicable_aspects": not_applicable,
        "missing_aspects": missing,
        "primary_failure": primary_failure,
    }


def _beat_capability_realization(aspects_ledger: Mapping[str, Any]) -> dict[str, Any]:
    beat_rec = _aspect_record(aspects_ledger, "beat")
    cap_rec = _aspect_record(aspects_ledger, "capability_selection")
    beat_selected = _aspect_block(beat_rec, "selected")
    beat_actual = _aspect_block(beat_rec, "actual")
    cap_selected = _aspect_block(cap_rec, "selected")
    cap_actual = _aspect_block(cap_rec, "actual")
    selected_caps = tuple(cap_selected.get("selected_capabilities") or ())
    realized_caps = tuple(cap_actual.get("realized_capabilities") or ())
    missing_required = tuple(cap_actual.get("missing_required_capabilities") or ())
    missing_from_realized = tuple(c for c in selected_caps if c not in realized_caps)
    extra_realized = tuple(c for c in realized_caps if c not in selected_caps)
    return {
        "selected_beat": beat_selected.get("selected_beat_id")
        or beat_selected.get("selected_scene_function"),
        "beat_realized": beat_actual.get("realized") if "realized" in beat_actual else None,
        "beat_failure_reason": _coerce_str(beat_rec.get("failure_reason")) or None,
        "beat_lost_at_stage": _coerce_str(beat_rec.get("lost_at_stage")) or None,
        "selected_capabilities": list(selected_caps),
        "realized_capabilities": list(realized_caps),
        "missing_required_capabilities": list(missing_required),
        "missing_from_realized": list(missing_from_realized),
        "extra_realized_capabilities": list(extra_realized),
        "forbidden_capability_realized": cap_actual.get("forbidden_capability_realized"),
        "capability_status": _coerce_str(cap_rec.get("status")) or None,
        "beat_status": _coerce_str(beat_rec.get("status")) or None,
    }


def _authority_clusters(aspects_ledger: Mapping[str, Any]) -> dict[str, Any]:
    narr_rec = _aspect_record(aspects_ledger, "narrator_authority")
    npc_rec = _aspect_record(aspects_ledger, "npc_authority")
    narr_expected = _aspect_block(narr_rec, "expected")
    narr_actual = _aspect_block(narr_rec, "actual")
    npc_expected = _aspect_block(npc_rec, "expected")
    npc_actual = _aspect_block(npc_rec, "actual")
    narrator_required = bool(narr_expected.get("required"))
    narrator_present = bool(
        narr_actual.get("narrator_block_present")
        or narr_actual.get("consequence_realized")
    )
    return {
        "narrator": {
            "required": narrator_required,
            "present": narrator_present,
            "fulfilled": (not narrator_required) or narrator_present,
            "status": _coerce_str(narr_rec.get("status")) or None,
            "failure_reason": _coerce_str(narr_rec.get("failure_reason")) or None,
        },
        "npc": {
            "policy": npc_expected.get("policy"),
            "takeover_detected": bool(npc_actual.get("npc_takeover_detected")),
            "policy_fulfilled": _coerce_str(npc_rec.get("status")) == "passed",
            "status": _coerce_str(npc_rec.get("status")) or None,
            "failure_reason": _coerce_str(npc_rec.get("failure_reason")) or None,
        },
    }


def _visible_projection_signals(aspects_ledger: Mapping[str, Any]) -> dict[str, Any]:
    vis_rec = _aspect_record(aspects_ledger, "visible_projection")
    vis_actual = _aspect_block(vis_rec, "actual")
    return {
        "origin_present": vis_actual.get("visible_block_origin_present"),
        "required_origin_preserved": vis_actual.get("required_visible_origin_preserved"),
        "lost_at_stage": _coerce_str(vis_rec.get("lost_at_stage")) or None,
        "status": _coerce_str(vis_rec.get("status")) or None,
        "failure_reason": _coerce_str(vis_rec.get("failure_reason")) or None,
    }


def _detect_span_anomalies(
    *,
    trace_kind: str,
    observation_names: Iterable[str],
    metadata: Mapping[str, Any],
    aspects_present: bool,
) -> list[dict[str, str]]:
    anomalies: list[dict[str, str]] = []
    names = {_coerce_str(n) for n in observation_names if n}

    if "story.graph.path_summary" not in names and trace_kind == "turn":
        anomalies.append(
            {
                "kind": "missing_expected_span",
                "name": "story.graph.path_summary",
                "detail": "turn trace did not emit story.graph.path_summary observation",
            }
        )

    if not aspects_present and trace_kind in ("turn", "opening"):
        anomalies.append(
            {
                "kind": "missing_turn_aspect_ledger",
                "name": "turn_aspect_ledger",
                "detail": "no turn_aspect_ledger present in path_summary or aspect_summary observation",
            }
        )

    gen_mode = _coerce_str(metadata.get("generation_mode")).lower()
    if (
        trace_kind == "turn"
        and gen_mode
        and gen_mode not in {"mock", "ldss_fallback", "ldss_deterministic"}
        and "story.model.generation" not in names
    ):
        anomalies.append(
            {
                "kind": "missing_generation_observation",
                "name": "story.model.generation",
                "detail": (
                    "generation_mode=" + gen_mode + " but no story.model.generation observation found"
                ),
            }
        )

    return anomalies


def _build_improvement_candidates(
    *,
    trace_id: str,
    runtime_aspect_summary: Mapping[str, Any],
    beat_cap: Mapping[str, Any],
    authority: Mapping[str, Any],
    visible: Mapping[str, Any],
    metadata_missing: Iterable[str],
    span_anomalies: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    def _add(*, priority: str, repair_area: str, rationale: str, source_kind: str = "langfuse_trace") -> None:
        candidates.append(
            {
                "priority": priority,
                "repair_area": repair_area,
                "rationale": rationale,
                "evidence_refs": [{"type": source_kind, "ref": trace_id or ""}],
            }
        )

    # Authority violations are highest priority.
    npc = authority.get("npc") or {}
    narrator = authority.get("narrator") or {}
    if npc.get("takeover_detected"):
        _add(
            priority="urgent",
            repair_area="repair_npc_authority_prevent_takeover",
            rationale="npc_takeover_detected=true in npc_authority aspect",
        )
    if narrator.get("required") and not narrator.get("present"):
        _add(
            priority="urgent",
            repair_area="repair_narrator_authority_required_consequence",
            rationale="narrator authority required but no narrator block present",
        )

    # Capability + beat issues are next.
    if beat_cap.get("forbidden_capability_realized"):
        _add(
            priority="urgent",
            repair_area="repair_capability_selection_block_forbidden_realization",
            rationale="forbidden_capability_realized=true in capability_selection aspect",
        )
    if beat_cap.get("missing_required_capabilities"):
        _add(
            priority="high",
            repair_area="repair_capability_selection_realize_required",
            rationale=(
                "missing_required_capabilities: "
                + ", ".join(beat_cap.get("missing_required_capabilities") or [])
            ),
        )
    if beat_cap.get("selected_beat") and beat_cap.get("beat_realized") is False:
        _add(
            priority="high",
            repair_area="repair_beat_realization",
            rationale=(
                f"selected_beat={beat_cap.get('selected_beat')!r} not realized "
                f"(lost_at_stage={beat_cap.get('beat_lost_at_stage')!r})"
            ),
        )

    # Visible projection origin metadata loss.
    if visible.get("origin_present") is False:
        _add(
            priority="medium",
            repair_area="repair_visible_projection_origin_metadata",
            rationale="visible_block_origin_present=false — backend dropped origin metadata before render",
        )

    # Metadata coverage problems block live-evidence claims.
    missing_list = [m for m in metadata_missing if m]
    if missing_list:
        _add(
            priority="medium" if len(missing_list) >= 3 else "low",
            repair_area="repair_trace_metadata_coverage",
            rationale=f"trace missing expected metadata fields: {', '.join(missing_list)}",
            source_kind="metadata",
        )

    # Span anomalies (observation contract).
    for anomaly in span_anomalies:
        kind = _coerce_str(anomaly.get("kind"))
        if kind == "missing_generation_observation":
            _add(
                priority="high",
                repair_area="repair_generation_observation_emission",
                rationale=_coerce_str(anomaly.get("detail")),
            )
        elif kind == "missing_turn_aspect_ledger":
            _add(
                priority="high",
                repair_area="repair_turn_aspect_ledger_emission",
                rationale=_coerce_str(anomaly.get("detail")),
            )
        elif kind == "missing_expected_span":
            _add(
                priority="medium",
                repair_area="repair_expected_span_emission",
                rationale=_coerce_str(anomaly.get("detail")),
            )

    # Stable, deterministic ordering.
    priority_rank = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    candidates.sort(key=lambda c: (priority_rank.get(c["priority"], 99), c["repair_area"]))
    return candidates


def _build_next_user_decision(
    *,
    trace_id: str,
    trace_kind: str,
    live_qualified: bool,
    runtime_aspect_summary: Mapping[str, Any],
    improvement_candidates: list[dict[str, Any]],
    aspects_present: bool,
) -> dict[str, Any] | None:
    """Return a single, focused human-AI decision prompt — or None when the
    trace is healthy enough that no decision is warranted."""
    if not aspects_present:
        return user_decision_prompt(
            question="The trace has no runtime aspect ledger — how should we investigate?",
            context_summary=(
                "fetch_langfuse_trace produced no turn_aspect_ledger. Likely causes: "
                "non-live trace, world-engine span never emitted story.turn.aspect_summary, "
                "or the trace is from an older code revision."
            ),
            options=[
                {
                    "id": "verify_live_evidence_criteria",
                    "label": "Verify live evidence criteria",
                    "description": "Confirm trace_origin/execution_tier/canonical_player_flow match a real live turn.",
                    "ai_action": (
                        "Re-fetch the trace metadata, check trace_origin/execution_tier/canonical_player_flow, "
                        "and report which criterion fails."
                    ),
                    "tradeoff": "Diagnoses non-live traces quickly but does not investigate runtime emission gaps.",
                    "recommended": True,
                },
                {
                    "id": "audit_aspect_emission_code",
                    "label": "Audit aspect-emission code paths",
                    "description": "Search world-engine manager for missing aspect ledger persistence.",
                    "ai_action": (
                        "Use mcp__claude-context__search_code to find where turn_aspect_ledger is written and "
                        "compare against the trace's path."
                    ),
                    "tradeoff": "Slower but catches genuine emission regressions.",
                },
                {
                    "id": "skip_and_pick_another_trace",
                    "label": "Skip and pick another trace",
                    "description": "This trace is likely too sparse to learn from.",
                    "ai_action": "Suggest the user query a recent live trace and re-run review_trace.",
                    "tradeoff": "Cheap but loses signal if the gap is systemic.",
                },
            ],
            evidence_refs=[{"type": "langfuse_trace", "ref": trace_id}],
        )

    if not improvement_candidates:
        return None

    top = improvement_candidates[0]
    repair_area = top["repair_area"]
    rationale = top["rationale"]

    options = [
        {
            "id": "investigate_top_repair_area",
            "label": f"Investigate {repair_area}",
            "description": f"Use trace evidence to locate root cause for {repair_area}.",
            "ai_action": (
                f"Open the trace ({trace_id}) and identify which runtime decision produced the failing aspect; "
                f"then propose a concrete code or content fix."
            ),
            "tradeoff": "Focused, but may miss correlated failures in other aspects.",
            "recommended": True,
        },
        {
            "id": "review_judgments_first",
            "label": "Pull judgments first",
            "description": "Pair this trace's qualitative judges with the structural failure before deciding.",
            "ai_action": (
                "Call wos.quality_lab.review_judgments on this trace's judge scores; combine with the structural "
                "evidence here before picking a repair."
            ),
            "tradeoff": "Slower; sometimes structural failures are unambiguous without qualitative context.",
        },
        {
            "id": "skip_this_trace",
            "label": "Skip this trace",
            "description": "Defer until other traces show the same cluster (avoid acting on one example).",
            "ai_action": "Tell the user how many traces in the recent window show this same repair_area.",
            "tradeoff": "Avoids over-fitting; loses time if the issue is reproducible and isolated.",
        },
    ]

    return user_decision_prompt(
        question=f"Top trace-level issue: {repair_area}. What should we do?",
        context_summary=(
            f"trace_id={trace_id}, kind={trace_kind}, live_evidence_qualified={live_qualified}. "
            f"primary_failure={runtime_aspect_summary.get('primary_failure')!r}. "
            f"rationale: {rationale}"
        ),
        options=options,
        evidence_refs=[{"type": "langfuse_trace", "ref": trace_id}],
    )


def interpret_trace(
    *,
    trace_id: str | None,
    trace_name: str | None,
    trace_metadata: Mapping[str, Any] | None,
    aspects_ledger: Mapping[str, Any] | None,
    observation_names: Iterable[str] = (),
    is_opening: bool | None = None,
) -> dict[str, Any]:
    """Pure analysis of an extracted trace.

    Parameters
    ----------
    trace_id, trace_name :
        From ``raw_trace.id`` / ``raw_trace.name``.
    trace_metadata :
        Flattened metadata dict — accepts both raw-trace ``metadata`` and
        ``path_summary``-derived fields. The caller should merge them with
        ``path_summary`` taking precedence over raw metadata.
    aspects_ledger :
        The ``turn_aspect_ledger`` inner mapping (i.e., the dict whose
        keys are aspect names like ``beat``, ``capability_selection``).
        Pass ``None`` or an empty dict when the trace has no ledger.
    observation_names :
        Iterable of observation/span names on the trace — used for span
        anomaly detection.
    is_opening :
        Optional override; when ``None``, derived from ``trace_name``.
    """
    metadata = dict(trace_metadata or {})
    aspects = dict(aspects_ledger or {})
    obs_names = list(observation_names or ())

    trace_kind = "opening" if is_opening is True else (
        "turn" if is_opening is False else classify_trace_kind(trace_name)
    )
    aspects_present = bool(aspects)

    present_fields, missing_fields = _present_metadata_fields(metadata)
    live_qualified, live_criteria = _live_evidence_qualified(metadata)

    runtime_aspect_summary = _build_runtime_aspect_summary(aspects)
    beat_cap = _beat_capability_realization(aspects)
    authority = _authority_clusters(aspects)
    visible = _visible_projection_signals(aspects)
    span_anomalies = _detect_span_anomalies(
        trace_kind=trace_kind,
        observation_names=obs_names,
        metadata=metadata,
        aspects_present=aspects_present,
    )
    improvement_candidates = _build_improvement_candidates(
        trace_id=_coerce_str(trace_id),
        runtime_aspect_summary=runtime_aspect_summary,
        beat_cap=beat_cap,
        authority=authority,
        visible=visible,
        metadata_missing=missing_fields,
        span_anomalies=span_anomalies,
    )
    next_decision = _build_next_user_decision(
        trace_id=_coerce_str(trace_id),
        trace_kind=trace_kind,
        live_qualified=live_qualified,
        runtime_aspect_summary=runtime_aspect_summary,
        improvement_candidates=improvement_candidates,
        aspects_present=aspects_present,
    )

    return {
        "trace_id": _coerce_str(trace_id) or None,
        "trace_name": _coerce_str(trace_name) or None,
        "trace_kind": trace_kind,
        "is_opening_trace": trace_kind == "opening",
        "live_evidence_qualified": live_qualified,
        "metadata_coverage": {
            "present_fields": present_fields,
            "missing_fields": missing_fields,
            "live_evidence_criteria": live_criteria,
        },
        "runtime_aspect_summary": runtime_aspect_summary,
        "beat_capability_realization": beat_cap,
        "authority_clusters": authority,
        "visible_projection_signals": visible,
        "span_anomalies": span_anomalies,
        "improvement_candidates": improvement_candidates,
        "next_user_decision": next_decision,
        "deterministic_gates_remain_authoritative": True,
        "canonical_evaluator_definition_doc": "docs/llm-as-a-judge/",
    }
