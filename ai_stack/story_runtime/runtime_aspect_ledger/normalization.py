"""Ledger normalization and mutation entry points.

Normalization fills missing aspect records, preserves runtime-only ADR sidecars,
and rebuilds the runtime-intelligence projection through an injectable builder
so the public package API can keep monkeypatchable authority hooks.
"""

from __future__ import annotations

import copy
from typing import Any, Callable

from .constants import (
    ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY,
    ASPECT_ACTION_RESOLUTION,
    ASPECT_INPUT,
    ASPECT_KEYS,
    RUNTIME_ASPECT_LEDGER_VERSION,
    TURN_ASPECT_LEDGER_SCHEMA_VERSION,
)
from .records import RuntimeAspectLedger, _json_safe, empty_aspect_record, make_aspect_record

def initialize_runtime_aspect_ledger(
    *,
    session_id: str | None,
    module_id: str | None,
    turn_number: int | None,
    turn_kind: str | None,
    raw_player_input: str | None,
    input_kind: str | None = None,
    turn_id: str | None = None,
    trace_id: str | None = None,
    runtime_profile_id: str | None = None,
    normalizer: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a full ledger with every required aspect key present."""
    tn = int(turn_number or 0)
    kind = str(turn_kind or ("opening" if tn <= 0 else "player")).strip() or "player"
    opening = tn <= 0 or kind in {"opening", "engine_opening"}
    raw = str(raw_player_input or "")
    input_aspect = make_aspect_record(
        applicable=True,
        status="passed" if raw or opening else "missing",
        expected={"turn_number": tn, "turn_kind": kind},
        actual={
            "raw_player_input": raw,
            "input_kind": input_kind,
            "real_player_turn_evidence_lane": not opening,
        },
        reasons=["opening_turn"] if opening else [],
        source="runtime",
    )
    ledger = {
        "schema_version": TURN_ASPECT_LEDGER_SCHEMA_VERSION,
        "contract": RUNTIME_ASPECT_LEDGER_VERSION,
        "record_version": RUNTIME_ASPECT_LEDGER_VERSION,
        "session_id": session_id,
        "story_session_id": session_id,
        "module_id": module_id,
        "runtime_profile_id": runtime_profile_id,
        "turn_id": turn_id,
        "canonical_turn_id": turn_id,
        "trace_id": trace_id,
        "turn_number": tn,
        "turn_kind": kind,
        "turn_aspect_ledger": {
            aspect: empty_aspect_record(
                applicable=not (opening and aspect == ASPECT_ACTION_RESOLUTION),
                source="runtime",
            )
            for aspect in ASPECT_KEYS
        },
    }
    ledger["turn_aspect_ledger"][ASPECT_INPUT] = input_aspect
    if opening:
        ledger["turn_aspect_ledger"][ASPECT_ACTION_RESOLUTION] = make_aspect_record(
            applicable=False,
            status="not_applicable",
            expected={"real_player_turn_evidence_lane": False},
            actual={"raw_player_input": None},
            reasons=["opening_turn_not_player_action_evidence_lane"],
            source="runtime",
        )
    return (normalizer or normalize_runtime_aspect_ledger)(ledger)
def normalize_runtime_aspect_ledger(
    ledger: dict[str, Any] | None,
    *,
    projection_builder: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a JSON-safe ledger with all required aspect keys in stable order."""
    src = copy.deepcopy(ledger) if isinstance(ledger, dict) else {}
    turn_aspects = src.get("turn_aspect_ledger")
    if not isinstance(turn_aspects, dict):
        turn_aspects = {}
    ordered_aspects: dict[str, Any] = {}
    for aspect in ASPECT_KEYS:
        record = turn_aspects.get(aspect)
        ordered_aspects[aspect] = (
            _json_safe(record) if isinstance(record, dict) else empty_aspect_record()
        )
    src["contract"] = str(src.get("contract") or RUNTIME_ASPECT_LEDGER_VERSION)
    src["record_version"] = str(src.get("record_version") or RUNTIME_ASPECT_LEDGER_VERSION)
    src["schema_version"] = str(src.get("schema_version") or TURN_ASPECT_LEDGER_SCHEMA_VERSION)
    if not src.get("story_session_id") and src.get("session_id"):
        src["story_session_id"] = src.get("session_id")
    if not src.get("canonical_turn_id") and src.get("turn_id"):
        src["canonical_turn_id"] = src.get("turn_id")
    src["turn_aspect_ledger"] = ordered_aspects
    if projection_builder is None:
        from .runtime_intelligence_projection import build_runtime_intelligence_projection as projection_builder

    rip = projection_builder(src)
    src["runtime_intelligence_projection"] = rip
    return _json_safe(src)
def ensure_runtime_aspect_ledger(
    ledger: dict[str, Any] | None,
    *,
    normalizer: Callable[[dict[str, Any] | None], dict[str, Any]] | None = None,
    session_id: str | None = None,
    module_id: str | None = None,
    turn_number: int | None = None,
    turn_kind: str | None = None,
    raw_player_input: str | None = None,
    input_kind: str | None = None,
    turn_id: str | None = None,
    trace_id: str | None = None,
    runtime_profile_id: str | None = None,
) -> dict[str, Any]:
    if isinstance(ledger, dict) and ledger.get("turn_aspect_ledger"):
        normalized = (normalizer or normalize_runtime_aspect_ledger)(ledger)
        if session_id and not normalized.get("session_id"):
            normalized["session_id"] = session_id
        if session_id and not normalized.get("story_session_id"):
            normalized["story_session_id"] = session_id
        if module_id and not normalized.get("module_id"):
            normalized["module_id"] = module_id
        if runtime_profile_id and not normalized.get("runtime_profile_id"):
            normalized["runtime_profile_id"] = runtime_profile_id
        if turn_number is not None and not normalized.get("turn_number"):
            normalized["turn_number"] = int(turn_number or 0)
        if turn_kind and not normalized.get("turn_kind"):
            normalized["turn_kind"] = turn_kind
        if turn_id and not normalized.get("turn_id"):
            normalized["turn_id"] = turn_id
        if turn_id and not normalized.get("canonical_turn_id"):
            normalized["canonical_turn_id"] = turn_id
        if trace_id and not normalized.get("trace_id"):
            normalized["trace_id"] = trace_id
        return (normalizer or normalize_runtime_aspect_ledger)(normalized)
    return initialize_runtime_aspect_ledger(
        session_id=session_id,
        module_id=module_id,
        turn_number=turn_number,
        turn_kind=turn_kind,
        raw_player_input=raw_player_input,
        input_kind=input_kind,
        turn_id=turn_id,
        trace_id=trace_id,
        runtime_profile_id=runtime_profile_id,
        normalizer=normalizer,
    )
def set_aspect_record(
    ledger: dict[str, Any],
    aspect_name: str,
    record: dict[str, Any],
    *,
    normalizer: Callable[[dict[str, Any] | None], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    out = (normalizer or normalize_runtime_aspect_ledger)(ledger)
    aspect = str(aspect_name or "").strip()
    if aspect not in ASPECT_KEYS:
        raise KeyError(aspect)
    out["turn_aspect_ledger"][aspect] = make_aspect_record(
        applicable=bool(record.get("applicable", True)),
        status=str(record.get("status") or "missing"),
        expected=record.get("expected") if isinstance(record.get("expected"), dict) else {},
        selected=record.get("selected") if isinstance(record.get("selected"), dict) else {},
        actual=record.get("actual") if isinstance(record.get("actual"), dict) else {},
        reasons=record.get("reasons") if isinstance(record.get("reasons"), list) else [],
        source=str(record.get("source") or "runtime"),
        failure_class=record.get("failure_class"),
        failure_reason=record.get("failure_reason"),
        offending_actor_id=record.get("offending_actor_id"),
        offending_block_id=record.get("offending_block_id"),
        missing_field=record.get("missing_field"),
        expected_owner=record.get("expected_owner"),
        actual_owner=record.get("actual_owner"),
        selected_capability=record.get("selected_capability"),
        realized_capability=record.get("realized_capability"),
        selected_beat=record.get("selected_beat"),
        lost_at_stage=record.get("lost_at_stage"),
        **{
            k: v
            for k, v in record.items()
            if k
            not in {
                "applicable",
                "status",
                "expected",
                "selected",
                "actual",
                "reasons",
                "source",
                "record_version",
                "failure_class",
                "failure_reason",
                "offending_actor_id",
                "offending_block_id",
                "missing_field",
                "expected_owner",
                "actual_owner",
                "selected_capability",
                "realized_capability",
                "selected_beat",
                "lost_at_stage",
            }
        },
    )
    return (normalizer or normalize_runtime_aspect_ledger)(out)
def get_aspect_record(ledger: dict[str, Any] | None, aspect_name: str) -> dict[str, Any]:
    normalized = normalize_runtime_aspect_ledger(ledger)
    aspect = str(aspect_name or "").strip()
    record = normalized["turn_aspect_ledger"].get(aspect)
    return record if isinstance(record, dict) else empty_aspect_record()
