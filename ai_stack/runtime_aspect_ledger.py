"""Backend-owned runtime aspect ledger for story turns.

The ledger is not a frontend display contract.  Authority-relevant aspects are
designed to be consumed by validation and commit before being emitted to
diagnostics or Langfuse.
"""

from __future__ import annotations

import copy
import json
from typing import Any


RUNTIME_ASPECT_LEDGER_VERSION = "runtime_aspect_ledger.v1"
RUNTIME_ASPECT_RECORD_VERSION = "runtime_aspect_record.v1"

ASPECT_INPUT = "input"
ASPECT_ACTION_RESOLUTION = "action_resolution"
ASPECT_BEAT = "beat"
ASPECT_CAPABILITY_SELECTION = "capability_selection"
ASPECT_NARRATOR_AUTHORITY = "narrator_authority"
ASPECT_NPC_AUTHORITY = "npc_authority"
ASPECT_VALIDATION = "validation"
ASPECT_COMMIT = "commit"
ASPECT_VISIBLE_PROJECTION = "visible_projection"

ASPECT_KEYS: tuple[str, ...] = (
    ASPECT_INPUT,
    ASPECT_ACTION_RESOLUTION,
    ASPECT_BEAT,
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_NARRATOR_AUTHORITY,
    ASPECT_NPC_AUTHORITY,
    ASPECT_VALIDATION,
    ASPECT_COMMIT,
    ASPECT_VISIBLE_PROJECTION,
)

ASPECT_STATUSES: frozenset[str] = frozenset(
    {"passed", "failed", "partial", "missing", "not_applicable"}
)

ASPECT_FAILURE_CLASSES: frozenset[str] = frozenset(
    {
        "hard_contract_failure",
        "recoverable_dramatic_failure",
        "degradation_only",
        "observability_gap",
        "projection_failure",
    }
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def make_aspect_record(
    *,
    applicable: bool,
    status: str,
    expected: dict[str, Any] | None = None,
    selected: dict[str, Any] | None = None,
    actual: dict[str, Any] | None = None,
    reasons: list[str] | None = None,
    source: str = "runtime",
    record_version: str = RUNTIME_ASPECT_RECORD_VERSION,
    failure_class: str | None = None,
    failure_reason: str | None = None,
    offending_actor_id: str | None = None,
    offending_block_id: str | None = None,
    missing_field: str | None = None,
    expected_owner: str | None = None,
    actual_owner: str | None = None,
    selected_capability: str | None = None,
    realized_capability: str | None = None,
    selected_beat: str | None = None,
    lost_at_stage: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build one stable aspect record."""
    st = str(status or "missing").strip() or "missing"
    if st not in ASPECT_STATUSES:
        st = "missing"
    fc = str(failure_class or "").strip() or None
    if fc and fc not in ASPECT_FAILURE_CLASSES:
        fc = "observability_gap"
    record: dict[str, Any] = {
        "applicable": bool(applicable),
        "status": st,
        "expected": _json_safe(expected or {}),
        "selected": _json_safe(selected or {}),
        "actual": _json_safe(actual or {}),
        "reasons": [str(r) for r in (reasons or []) if str(r).strip()],
        "source": str(source or "runtime"),
        "record_version": record_version,
        "failure_class": fc,
        "failure_reason": failure_reason,
        "offending_actor_id": offending_actor_id,
        "offending_block_id": offending_block_id,
        "missing_field": missing_field,
        "expected_owner": expected_owner,
        "actual_owner": actual_owner,
        "selected_capability": selected_capability,
        "realized_capability": realized_capability,
        "selected_beat": selected_beat,
        "lost_at_stage": lost_at_stage,
    }
    for key, value in extra.items():
        record[str(key)] = _json_safe(value)
    return record


def empty_aspect_record(*, applicable: bool = True, source: str = "runtime") -> dict[str, Any]:
    return make_aspect_record(
        applicable=applicable,
        status="missing" if applicable else "not_applicable",
        source=source,
    )


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
        "contract": RUNTIME_ASPECT_LEDGER_VERSION,
        "record_version": RUNTIME_ASPECT_LEDGER_VERSION,
        "session_id": session_id,
        "module_id": module_id,
        "turn_id": turn_id,
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
    return normalize_runtime_aspect_ledger(ledger)


def normalize_runtime_aspect_ledger(ledger: dict[str, Any] | None) -> dict[str, Any]:
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
    src["turn_aspect_ledger"] = ordered_aspects
    return _json_safe(src)


def ensure_runtime_aspect_ledger(
    ledger: dict[str, Any] | None,
    *,
    session_id: str | None = None,
    module_id: str | None = None,
    turn_number: int | None = None,
    turn_kind: str | None = None,
    raw_player_input: str | None = None,
    input_kind: str | None = None,
    turn_id: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    if isinstance(ledger, dict) and ledger.get("turn_aspect_ledger"):
        return normalize_runtime_aspect_ledger(ledger)
    return initialize_runtime_aspect_ledger(
        session_id=session_id,
        module_id=module_id,
        turn_number=turn_number,
        turn_kind=turn_kind,
        raw_player_input=raw_player_input,
        input_kind=input_kind,
        turn_id=turn_id,
        trace_id=trace_id,
    )


def set_aspect_record(
    ledger: dict[str, Any],
    aspect_name: str,
    record: dict[str, Any],
) -> dict[str, Any]:
    out = normalize_runtime_aspect_ledger(ledger)
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
    return normalize_runtime_aspect_ledger(out)


def get_aspect_record(ledger: dict[str, Any] | None, aspect_name: str) -> dict[str, Any]:
    normalized = normalize_runtime_aspect_ledger(ledger)
    aspect = str(aspect_name or "").strip()
    record = normalized["turn_aspect_ledger"].get(aspect)
    return record if isinstance(record, dict) else empty_aspect_record()


def stable_ledger_json(ledger: dict[str, Any]) -> str:
    return json.dumps(
        normalize_runtime_aspect_ledger(ledger),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def aspect_score_metadata(
    *,
    ledger: dict[str, Any] | None,
    aspect_name: str,
    score_name: str,
) -> dict[str, Any]:
    """Build required reason metadata for deterministic aspect scores."""
    normalized = normalize_runtime_aspect_ledger(ledger)
    aspect = get_aspect_record(normalized, aspect_name)
    reasons = aspect.get("reasons") if isinstance(aspect.get("reasons"), list) else []
    return {
        "score_name": score_name,
        "aspect_name": aspect_name,
        "session_id": normalized.get("session_id"),
        "trace_id": normalized.get("trace_id"),
        "turn_number": normalized.get("turn_number"),
        "status": aspect.get("status"),
        "failure_reason": aspect.get("failure_reason")
        or (reasons[0] if reasons else None),
        "offending_actor_id": aspect.get("offending_actor_id"),
        "offending_block_id": aspect.get("offending_block_id"),
        "missing_field": aspect.get("missing_field"),
        "expected_owner": aspect.get("expected_owner"),
        "actual_owner": aspect.get("actual_owner"),
        "selected_capability": aspect.get("selected_capability"),
        "realized_capability": aspect.get("realized_capability"),
        "selected_beat": aspect.get("selected_beat"),
        "lost_at_stage": aspect.get("lost_at_stage"),
    }
