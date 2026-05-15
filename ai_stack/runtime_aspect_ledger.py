"""Backend-owned runtime aspect ledger for story turns.

The ledger is not a frontend display contract.  Authority-relevant aspects are
designed to be consumed by validation and commit before being emitted to
diagnostics or Langfuse.
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from typing import Any


RUNTIME_ASPECT_LEDGER_VERSION = "runtime_aspect_ledger.v1"
TURN_ASPECT_LEDGER_SCHEMA_VERSION = "turn_aspect_ledger.v1"
RUNTIME_ASPECT_RECORD_VERSION = "runtime_aspect_record.v1"

ASPECT_INPUT = "input"
ASPECT_ACTION_RESOLUTION = "action_resolution"
ASPECT_BEAT = "beat"
ASPECT_SCENE_ENERGY = "scene_energy"
ASPECT_PACING_RHYTHM = "pacing_rhythm"
ASPECT_CAPABILITY_SELECTION = "capability_selection"
ASPECT_NARRATOR_AUTHORITY = "narrator_authority"
ASPECT_NPC_AUTHORITY = "npc_authority"
ASPECT_NPC_AGENCY = "npc_agency"
ASPECT_DRAMATIC_IRONY = "dramatic_irony"
ASPECT_VOICE_CONSISTENCY = "voice_consistency"
ASPECT_NARRATIVE_ASPECT = "narrative_aspect"
ASPECT_INFORMATION_DISCLOSURE = "information_disclosure"
ASPECT_HIERARCHICAL_MEMORY = "hierarchical_memory"
ASPECT_CALLBACK_WEB = "callback_web"
ASPECT_VALIDATION = "validation"
ASPECT_COMMIT = "commit"
ASPECT_VISIBLE_PROJECTION = "visible_projection"

ASPECT_KEYS: tuple[str, ...] = (
    ASPECT_INPUT,
    ASPECT_ACTION_RESOLUTION,
    ASPECT_BEAT,
    ASPECT_SCENE_ENERGY,
    ASPECT_PACING_RHYTHM,
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_NARRATOR_AUTHORITY,
    ASPECT_NPC_AUTHORITY,
    ASPECT_NPC_AGENCY,
    ASPECT_DRAMATIC_IRONY,
    ASPECT_VOICE_CONSISTENCY,
    ASPECT_NARRATIVE_ASPECT,
    ASPECT_INFORMATION_DISCLOSURE,
    ASPECT_HIERARCHICAL_MEMORY,
    ASPECT_CALLBACK_WEB,
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


@dataclass(frozen=True)
class RuntimeAspectLedger:
    """JSON-safe canonical per-turn runtime intelligence envelope."""

    schema_version: str = TURN_ASPECT_LEDGER_SCHEMA_VERSION
    record_version: str = RUNTIME_ASPECT_LEDGER_VERSION
    module_id: str | None = None
    runtime_profile_id: str | None = None
    canonical_turn_id: str | None = None
    story_session_id: str | None = None
    turn_number: int = 0
    turn_kind: str = "player"
    turn_aspect_ledger: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


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
    runtime_profile_id: str | None = None,
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
    src["schema_version"] = str(src.get("schema_version") or TURN_ASPECT_LEDGER_SCHEMA_VERSION)
    if not src.get("story_session_id") and src.get("session_id"):
        src["story_session_id"] = src.get("session_id")
    if not src.get("canonical_turn_id") and src.get("turn_id"):
        src["canonical_turn_id"] = src.get("turn_id")
    src["turn_aspect_ledger"] = ordered_aspects
    src["runtime_intelligence_projection"] = build_runtime_intelligence_projection(src)
    return _json_safe(src)


def _first_text(values: list[Any]) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def _record_block(record: dict[str, Any], key: str) -> dict[str, Any]:
    block = record.get(key) if isinstance(record, dict) else {}
    return block if isinstance(block, dict) else {}


def _record_nested_value(record: dict[str, Any], key: str, nested_key: str) -> Any:
    nested = record.get(nested_key) if isinstance(record.get(nested_key), dict) else {}
    return record.get(key) or nested.get(key)


def _record_reasons(record: dict[str, Any]) -> list[str]:
    reasons = record.get("reasons") if isinstance(record, dict) else []
    return [str(reason) for reason in reasons if str(reason).strip()] if isinstance(reasons, list) else []


def build_runtime_intelligence_projection(ledger: dict[str, Any] | None) -> dict[str, Any]:
    """Project aspect-record storage into the requested turn-ledger design shape.

    The canonical storage format remains the per-aspect record map above. This
    projection is intentionally redundant and JSON-safe so backend, Langfuse,
    and MCP consumers can ask the direct implementation questions without
    learning the internal record layout.
    """
    src = ledger if isinstance(ledger, dict) else {}
    aspects = src.get("turn_aspect_ledger") if isinstance(src.get("turn_aspect_ledger"), dict) else {}
    input_rec = aspects.get(ASPECT_INPUT) if isinstance(aspects.get(ASPECT_INPUT), dict) else {}
    action_rec = (
        aspects.get(ASPECT_ACTION_RESOLUTION)
        if isinstance(aspects.get(ASPECT_ACTION_RESOLUTION), dict)
        else {}
    )
    beat_rec = aspects.get(ASPECT_BEAT) if isinstance(aspects.get(ASPECT_BEAT), dict) else {}
    scene_energy_rec = (
        aspects.get(ASPECT_SCENE_ENERGY)
        if isinstance(aspects.get(ASPECT_SCENE_ENERGY), dict)
        else {}
    )
    pacing_rhythm_rec = (
        aspects.get(ASPECT_PACING_RHYTHM)
        if isinstance(aspects.get(ASPECT_PACING_RHYTHM), dict)
        else {}
    )
    cap_rec = (
        aspects.get(ASPECT_CAPABILITY_SELECTION)
        if isinstance(aspects.get(ASPECT_CAPABILITY_SELECTION), dict)
        else {}
    )
    narr_rec = (
        aspects.get(ASPECT_NARRATOR_AUTHORITY)
        if isinstance(aspects.get(ASPECT_NARRATOR_AUTHORITY), dict)
        else {}
    )
    npc_rec = aspects.get(ASPECT_NPC_AUTHORITY) if isinstance(aspects.get(ASPECT_NPC_AUTHORITY), dict) else {}
    npc_agency_rec = (
        aspects.get(ASPECT_NPC_AGENCY)
        if isinstance(aspects.get(ASPECT_NPC_AGENCY), dict)
        else {}
    )
    dramatic_irony_rec = (
        aspects.get(ASPECT_DRAMATIC_IRONY)
        if isinstance(aspects.get(ASPECT_DRAMATIC_IRONY), dict)
        else {}
    )
    voice_rec = (
        aspects.get(ASPECT_VOICE_CONSISTENCY)
        if isinstance(aspects.get(ASPECT_VOICE_CONSISTENCY), dict)
        else {}
    )
    narrative_rec = (
        aspects.get(ASPECT_NARRATIVE_ASPECT)
        if isinstance(aspects.get(ASPECT_NARRATIVE_ASPECT), dict)
        else {}
    )
    disclosure_rec = (
        aspects.get(ASPECT_INFORMATION_DISCLOSURE)
        if isinstance(aspects.get(ASPECT_INFORMATION_DISCLOSURE), dict)
        else {}
    )
    memory_rec = (
        aspects.get(ASPECT_HIERARCHICAL_MEMORY)
        if isinstance(aspects.get(ASPECT_HIERARCHICAL_MEMORY), dict)
        else {}
    )
    callback_rec = (
        aspects.get(ASPECT_CALLBACK_WEB)
        if isinstance(aspects.get(ASPECT_CALLBACK_WEB), dict)
        else {}
    )
    validation_rec = (
        aspects.get(ASPECT_VALIDATION)
        if isinstance(aspects.get(ASPECT_VALIDATION), dict)
        else {}
    )
    commit_rec = aspects.get(ASPECT_COMMIT) if isinstance(aspects.get(ASPECT_COMMIT), dict) else {}
    visible_rec = (
        aspects.get(ASPECT_VISIBLE_PROJECTION)
        if isinstance(aspects.get(ASPECT_VISIBLE_PROJECTION), dict)
        else {}
    )
    branching_forecast = src.get("branching_forecast") if isinstance(src.get("branching_forecast"), dict) else {}

    input_actual = _record_block(input_rec, "actual")
    action_actual = _record_block(action_rec, "actual")
    beat_expected = _record_block(beat_rec, "expected")
    beat_selected = _record_block(beat_rec, "selected")
    beat_actual = _record_block(beat_rec, "actual")
    scene_energy_expected = _record_block(scene_energy_rec, "expected")
    scene_energy_selected = _record_block(scene_energy_rec, "selected")
    scene_energy_actual = _record_block(scene_energy_rec, "actual")
    pacing_rhythm_expected = _record_block(pacing_rhythm_rec, "expected")
    pacing_rhythm_selected = _record_block(pacing_rhythm_rec, "selected")
    pacing_rhythm_actual = _record_block(pacing_rhythm_rec, "actual")
    cap_expected = _record_block(cap_rec, "expected")
    cap_selected = _record_block(cap_rec, "selected")
    cap_actual = _record_block(cap_rec, "actual")
    narr_expected = _record_block(narr_rec, "expected")
    narr_actual = _record_block(narr_rec, "actual")
    npc_expected = _record_block(npc_rec, "expected")
    npc_actual = _record_block(npc_rec, "actual")
    npc_agency_expected = _record_block(npc_agency_rec, "expected")
    npc_agency_selected = _record_block(npc_agency_rec, "selected")
    npc_agency_actual = _record_block(npc_agency_rec, "actual")
    dramatic_irony_expected = _record_block(dramatic_irony_rec, "expected")
    dramatic_irony_selected = _record_block(dramatic_irony_rec, "selected")
    dramatic_irony_actual = _record_block(dramatic_irony_rec, "actual")
    voice_expected = _record_block(voice_rec, "expected")
    voice_actual = _record_block(voice_rec, "actual")
    narrative_expected = _record_block(narrative_rec, "expected")
    narrative_selected = _record_block(narrative_rec, "selected")
    narrative_actual = _record_block(narrative_rec, "actual")
    disclosure_expected = _record_block(disclosure_rec, "expected")
    disclosure_selected = _record_block(disclosure_rec, "selected")
    disclosure_actual = _record_block(disclosure_rec, "actual")
    memory_expected = _record_block(memory_rec, "expected")
    memory_selected = _record_block(memory_rec, "selected")
    memory_actual = _record_block(memory_rec, "actual")
    callback_expected = _record_block(callback_rec, "expected")
    callback_selected = _record_block(callback_rec, "selected")
    callback_actual = _record_block(callback_rec, "actual")
    visible_actual = _record_block(visible_rec, "actual")
    commit_actual = _record_block(commit_rec, "actual")

    selected_beat_id = _first_text(
        [
            beat_selected.get("selected_beat_id"),
            beat_selected.get("selected_scene_function"),
            beat_rec.get("selected_beat"),
        ]
    )
    selected_capabilities = cap_selected.get("selected_capabilities")
    required_capabilities = cap_expected.get("required_capabilities")
    blocked_capabilities = cap_selected.get("blocked_capabilities") or cap_actual.get(
        "blocked_capabilities"
    )
    realized_capabilities = cap_actual.get("realized_capabilities")
    violated_capabilities = cap_actual.get("violated_capabilities") or cap_actual.get(
        "missing_required_capabilities"
    )

    return _json_safe(
        {
            "schema_version": TURN_ASPECT_LEDGER_SCHEMA_VERSION,
            "module_id": src.get("module_id"),
            "runtime_profile_id": src.get("runtime_profile_id"),
            "canonical_turn_id": src.get("canonical_turn_id"),
            "story_session_id": src.get("story_session_id") or src.get("session_id"),
            "turn_number": src.get("turn_number"),
            "input": {
                "player_input_kind": input_actual.get("player_input_kind")
                or input_actual.get("input_kind")
                or action_actual.get("input_kind"),
                "semantic_move": action_actual.get("semantic_move")
                or action_actual.get("semantic_move_kind")
                or action_actual.get("action_kind"),
                "player_action_frame": action_actual.get("player_action_frame") or {},
                "affordance_resolution": action_actual.get("affordance_resolution") or {},
                "local_context_transition": action_actual.get("local_context_transition") or {},
            },
            "beat": {
                "beat_state_before": beat_expected.get("beat_state_before") or {},
                "candidate_beats": beat_expected.get("candidate_beats") or [],
                "selected_beat": {"id": selected_beat_id} if selected_beat_id else {},
                "selection_source": beat_selected.get("selection_source")
                or beat_rec.get("source")
                or None,
                "selection_reason": beat_selected.get("selection_reason"),
                "expected_visible_functions": beat_expected.get("expected_realization")
                or beat_expected.get("expected_visible_functions")
                or [],
                "realized": beat_actual.get("realized"),
                "realization_evidence": beat_actual.get("realization_evidence") or [],
                "failure_reason": beat_rec.get("failure_reason")
                or (_record_reasons(beat_rec)[0] if _record_reasons(beat_rec) else None),
                "beat_state_after": beat_actual.get("beat_state_after") or {},
                "status": beat_rec.get("status"),
            },
            "scene_energy": {
                "schema_version": scene_energy_expected.get("schema_version")
                or scene_energy_selected.get("schema_version")
                or scene_energy_actual.get("schema_version"),
                "policy_present": bool(scene_energy_expected.get("policy_present")),
                "policy_enabled": bool(scene_energy_expected.get("policy_enabled")),
                "energy_level": _record_nested_value(
                    scene_energy_selected, "energy_level", "target"
                ),
                "pressure_vector": _record_nested_value(
                    scene_energy_selected, "pressure_vector", "target"
                ),
                "tempo": _record_nested_value(scene_energy_selected, "tempo", "target"),
                "density": _record_nested_value(scene_energy_selected, "density", "target"),
                "volatility": _record_nested_value(
                    scene_energy_selected, "volatility", "target"
                ),
                "target_transition": scene_energy_selected.get("target_transition")
                or _record_nested_value(scene_energy_selected, "transition_intent", "transition"),
                "minimum_actor_response_count": int(
                    scene_energy_selected.get("minimum_actor_response_count")
                    or (
                        scene_energy_selected.get("target", {}).get("minimum_actor_response_count")
                        if isinstance(scene_energy_selected.get("target"), dict)
                        else 0
                    )
                    or 0
                ),
                "actual_actor_response_count": int(
                    scene_energy_actual.get("actual_actor_response_count") or 0
                ),
                "visible_density_count": int(scene_energy_actual.get("visible_density_count") or 0),
                "transition_allowed": scene_energy_actual.get("transition_allowed"),
                "failure_codes": scene_energy_actual.get("failure_codes") or _record_reasons(scene_energy_rec),
                "contract_pass": scene_energy_actual.get("contract_pass"),
                "failure_reason": scene_energy_rec.get("failure_reason")
                or (_record_reasons(scene_energy_rec)[0] if _record_reasons(scene_energy_rec) else None),
                "status": scene_energy_rec.get("status"),
            },
            "pacing_rhythm": {
                "schema_version": pacing_rhythm_expected.get("schema_version")
                or pacing_rhythm_selected.get("schema_version")
                or pacing_rhythm_actual.get("schema_version"),
                "policy_present": bool(pacing_rhythm_expected.get("policy_present")),
                "policy_enabled": bool(pacing_rhythm_expected.get("policy_enabled")),
                "cadence": _record_nested_value(
                    pacing_rhythm_selected, "cadence", "target"
                ),
                "tempo_arc": _record_nested_value(
                    pacing_rhythm_selected, "tempo_arc", "target"
                ),
                "response_shape": _record_nested_value(
                    pacing_rhythm_selected, "response_shape", "target"
                ),
                "turn_change_policy": _record_nested_value(
                    pacing_rhythm_selected, "turn_change_policy", "target"
                ),
                "min_visible_blocks": int(
                    pacing_rhythm_selected.get("min_visible_blocks")
                    or (
                        pacing_rhythm_selected.get("target", {}).get("min_visible_blocks")
                        if isinstance(pacing_rhythm_selected.get("target"), dict)
                        else 0
                    )
                    or 0
                ),
                "max_visible_blocks": int(
                    pacing_rhythm_selected.get("max_visible_blocks")
                    or (
                        pacing_rhythm_selected.get("target", {}).get("max_visible_blocks")
                        if isinstance(pacing_rhythm_selected.get("target"), dict)
                        else 0
                    )
                    or 0
                ),
                "visible_block_count": int(
                    pacing_rhythm_actual.get("visible_block_count") or 0
                ),
                "actor_turn_count": int(pacing_rhythm_actual.get("actor_turn_count") or 0),
                "requires_pause": bool(
                    pacing_rhythm_selected.get("requires_pause")
                    or (
                        pacing_rhythm_selected.get("target", {}).get("requires_pause")
                        if isinstance(pacing_rhythm_selected.get("target"), dict)
                        else False
                    )
                ),
                "blocks_forced_speech": bool(
                    pacing_rhythm_selected.get("blocks_forced_speech")
                    or (
                        pacing_rhythm_selected.get("target", {}).get("blocks_forced_speech")
                        if isinstance(pacing_rhythm_selected.get("target"), dict)
                        else False
                    )
                ),
                "contract_pass": pacing_rhythm_actual.get("contract_pass"),
                "failure_codes": pacing_rhythm_actual.get("failure_codes")
                or _record_reasons(pacing_rhythm_rec),
                "failure_reason": pacing_rhythm_rec.get("failure_reason")
                or (
                    _record_reasons(pacing_rhythm_rec)[0]
                    if _record_reasons(pacing_rhythm_rec)
                    else None
                ),
                "status": pacing_rhythm_rec.get("status"),
            },
            "capability": {
                "selected_capabilities": selected_capabilities
                if isinstance(selected_capabilities, list)
                else [],
                "blocked_capabilities": blocked_capabilities
                if isinstance(blocked_capabilities, list)
                else [],
                "required_capabilities": required_capabilities
                if isinstance(required_capabilities, list)
                else [],
                "realized_capabilities": realized_capabilities
                if isinstance(realized_capabilities, list)
                else [],
                "violated_capabilities": violated_capabilities
                if isinstance(violated_capabilities, list)
                else [],
                "status": cap_rec.get("status"),
            },
            "authority": {
                "narrator": {
                    "required": bool(narr_expected.get("required")),
                    "expected_owner": narr_rec.get("expected_owner")
                    or narr_expected.get("expected_owner")
                    or "narrator",
                    "actual_owners": narr_actual.get("actual_owners") or [],
                    "fulfilled": narr_actual.get("fulfilled")
                    if "fulfilled" in narr_actual
                    else narr_actual.get("narrator_block_present")
                    or narr_actual.get("consequence_realized"),
                    "evidence_blocks": narr_actual.get("evidence_blocks") or [],
                    "failure_reason": narr_rec.get("failure_reason")
                    or (_record_reasons(narr_rec)[0] if _record_reasons(narr_rec) else None),
                },
                "npc": {
                    "policy": npc_expected.get("policy"),
                    "allowed_actors": npc_expected.get("allowed_actors") or [],
                    "actual_actors": npc_actual.get("actual_actors") or [],
                    "takeover_detected": bool(npc_actual.get("npc_takeover_detected")),
                    "offending_blocks": npc_actual.get("offending_blocks") or [],
                    "status": npc_rec.get("status"),
                },
                "player": {
                    "selected_human_actor_id": narr_expected.get("selected_human_actor_id")
                    or npc_expected.get("selected_human_actor_id"),
                    "forced_speech_detected": bool(npc_actual.get("forced_speech_detected")),
                    "forced_decision_detected": bool(npc_actual.get("forced_decision_detected")),
                    "agency_violation_detected": bool(npc_actual.get("agency_violation_detected")),
                },
            },
            "npc_agency": {
                "contract_status": npc_agency_expected.get("contract_status")
                or npc_agency_actual.get("contract_status"),
                "not_full_multi_agent_simulation": bool(
                    npc_agency_expected.get("not_full_multi_agent_simulation")
                    or npc_agency_actual.get("not_full_multi_agent_simulation")
                ),
                "independent_planning_used": bool(
                    npc_agency_actual.get("independent_planning_used")
                    or npc_agency_expected.get("independent_planning_expected")
                ),
                "planner_scope": npc_agency_actual.get("planner_scope"),
                "candidate_actor_ids": npc_agency_actual.get("candidate_actor_ids")
                or npc_agency_expected.get("candidate_actor_ids")
                or [],
                "planned_actor_ids": npc_agency_actual.get("planned_actor_ids") or [],
                "realized_actor_ids": npc_agency_actual.get("realized_actor_ids") or [],
                "missing_required_actor_ids": npc_agency_actual.get("missing_required_actor_ids")
                or [],
                "carry_forward_actor_ids": npc_agency_actual.get("carry_forward_actor_ids") or [],
                "closure_status": npc_agency_actual.get("closure_status"),
                "long_horizon_state_present": bool(
                    npc_agency_actual.get("long_horizon_state_present")
                    or npc_agency_expected.get("long_horizon_state_present")
                ),
                "intention_threads_active": int(npc_agency_actual.get("intention_threads_active") or 0),
                "intention_threads_carried_forward": int(
                    npc_agency_actual.get("intention_threads_carried_forward") or 0
                ),
                "private_plan_resolution_present": bool(
                    npc_agency_actual.get("private_plan_resolution_present")
                    or npc_agency_expected.get("private_plan_resolution_present")
                ),
                "private_plan_visibility_respected": bool(
                    npc_agency_actual.get("private_plan_visibility_respected")
                ),
                "selected_private_plan_ids": npc_agency_actual.get("selected_private_plan_ids")
                or npc_agency_selected.get("selected_private_plan_ids")
                or [],
                "selected_private_plan_actor_ids": npc_agency_actual.get("selected_private_plan_actor_ids")
                or npc_agency_selected.get("selected_private_plan_actor_ids")
                or [],
                "withheld_private_plan_ids": npc_agency_actual.get("withheld_private_plan_ids") or [],
                "unrealized_selected_private_plan_actor_ids": npc_agency_actual.get(
                    "unrealized_selected_private_plan_actor_ids"
                )
                or [],
                "error_codes": npc_agency_actual.get("error_codes") or [],
                "multi_npc_initiative_realized": bool(
                    npc_agency_actual.get("multi_npc_initiative_realized")
                ),
                "failure_reason": npc_agency_rec.get("failure_reason")
                or (_record_reasons(npc_agency_rec)[0] if _record_reasons(npc_agency_rec) else None),
                "status": npc_agency_rec.get("status"),
            },
            "dramatic_irony": {
                "schema_version": dramatic_irony_expected.get("schema_version"),
                "policy_present": bool(dramatic_irony_expected.get("policy_present")),
                "policy_enabled": bool(dramatic_irony_expected.get("policy_enabled")),
                "allowed_sources": dramatic_irony_expected.get("allowed_sources") or [],
                "allowed_surface_modes": dramatic_irony_expected.get("allowed_surface_modes") or [],
                "direct_reveal_allowed": bool(
                    dramatic_irony_expected.get("direct_reveal_allowed")
                ),
                "selected_opportunity_ids": dramatic_irony_selected.get("selected_opportunity_ids")
                or [],
                "selected_fact_ids": dramatic_irony_selected.get("selected_fact_ids") or [],
                "fact_count": int(dramatic_irony_actual.get("fact_count") or 0),
                "opportunity_count": int(dramatic_irony_actual.get("opportunity_count") or 0),
                "selected_opportunity_count": int(
                    dramatic_irony_actual.get("selected_opportunity_count") or 0
                ),
                "realization_status": dramatic_irony_actual.get("realization_status"),
                "realized_opportunity_ids": dramatic_irony_actual.get("realized_opportunity_ids")
                or [],
                "leak_blocked": bool(dramatic_irony_actual.get("leak_blocked")),
                "violation_codes": dramatic_irony_actual.get("violation_codes") or [],
                "contract_pass": dramatic_irony_actual.get("contract_pass"),
                "failure_reason": dramatic_irony_rec.get("failure_reason")
                or (
                    _record_reasons(dramatic_irony_rec)[0]
                    if _record_reasons(dramatic_irony_rec)
                    else None
                ),
                "status": dramatic_irony_rec.get("status"),
            },
            "visible_projection": {
                "blocks_have_origin_aspect": bool(visible_actual.get("blocks_have_origin_aspect")),
                "required_blocks_present": bool(visible_actual.get("required_blocks_present")),
                "lost_required_narrator_block": bool(
                    visible_actual.get("lost_required_narrator_block")
                ),
                "visible_block_origins": visible_actual.get("visible_block_origins") or [],
            },
            "voice_consistency": {
                "policy_present": bool(voice_expected.get("policy_present")),
                "semantic_classification_enabled": bool(
                    voice_expected.get("semantic_classification_enabled")
                ),
                "profiles_checked": int(voice_actual.get("profiles_checked") or 0),
                "spoken_line_count": int(voice_actual.get("spoken_line_count") or 0),
                "finding_count": int(voice_actual.get("finding_count") or 0),
                "blocking_finding_count": int(voice_actual.get("blocking_finding_count") or 0),
                "semantic_classification_count": int(
                    voice_actual.get("semantic_classification_count") or 0
                ),
                "semantic_cross_actor_confusion_count": int(
                    voice_actual.get("semantic_cross_actor_confusion_count") or 0
                ),
                "semantic_mixed_signature_count": int(
                    voice_actual.get("semantic_mixed_signature_count") or 0
                ),
                "semantic_ambiguous_signature_count": int(
                    voice_actual.get("semantic_ambiguous_signature_count") or 0
                ),
                "semantic_weak_alignment_count": int(
                    voice_actual.get("semantic_weak_alignment_count") or 0
                ),
                "semantic_classifications": voice_actual.get("semantic_classifications")
                or [],
                "failure_reason": voice_rec.get("failure_reason")
                or (_record_reasons(voice_rec)[0] if _record_reasons(voice_rec) else None),
                "status": voice_rec.get("status"),
            },
            "narrative_aspect": {
                "policy_present": bool(narrative_expected.get("policy_present")),
                "candidate_aspects": narrative_expected.get("candidate_aspects") or [],
                "semantic_tracking_enabled": bool(narrative_expected.get("semantic_tracking_enabled")),
                "semantic_profile_aspects": narrative_expected.get("semantic_profile_aspects") or [],
                "selected_aspects": narrative_selected.get("selected_aspects") or [],
                "selected_theme_aspects": narrative_selected.get("selected_theme_aspects") or narrative_actual.get("selected_theme_aspects") or [],
                "selection_source": narrative_selected.get("selection_source"),
                "realized_aspects": narrative_actual.get("realized_aspects") or [],
                "realized_theme_aspects": narrative_actual.get("realized_theme_aspects") or [],
                "missing_required_evidence": narrative_actual.get("missing_required_evidence") or [],
                "evidence": narrative_actual.get("evidence") or [],
                "visible_when_required": narrative_actual.get("visible_when_required"),
                "semantic_classification_count": int(narrative_actual.get("semantic_classification_count") or 0),
                "semantic_weak_alignment_count": int(narrative_actual.get("semantic_weak_alignment_count") or 0),
                "semantic_required_weak_alignment_count": int(narrative_actual.get("semantic_required_weak_alignment_count") or 0),
                "semantic_classifications": narrative_actual.get("semantic_classifications") or [],
                "failure_reason": narrative_rec.get("failure_reason")
                or (_record_reasons(narrative_rec)[0] if _record_reasons(narrative_rec) else None),
                "status": narrative_rec.get("status"),
            },
            "information_disclosure": {
                "policy_present": bool(disclosure_expected.get("policy_present")),
                "policy_enabled": bool(disclosure_expected.get("policy_enabled")),
                "commit_impact": disclosure_expected.get("commit_impact"),
                "require_structured_events": bool(
                    disclosure_expected.get("require_structured_events")
                ),
                "max_visible_units_per_turn": int(
                    disclosure_expected.get("max_visible_units_per_turn") or 0
                ),
                "selected_unit_ids": disclosure_selected.get("selected_unit_ids") or [],
                "allowed_unit_ids": disclosure_selected.get("allowed_unit_ids") or [],
                "withheld_unit_ids": disclosure_selected.get("withheld_unit_ids")
                or disclosure_actual.get("withheld_unit_ids")
                or [],
                "forbidden_unit_ids": disclosure_selected.get("forbidden_unit_ids") or [],
                "disclosure_mode": disclosure_selected.get("disclosure_mode"),
                "structured_events_present": bool(
                    disclosure_actual.get("structured_events_present")
                ),
                "event_count": int(disclosure_actual.get("event_count") or 0),
                "visible_unit_ids": disclosure_actual.get("visible_unit_ids") or [],
                "budget_used": int(disclosure_actual.get("budget_used") or 0),
                "contract_pass": disclosure_actual.get("contract_pass"),
                "failure_codes": disclosure_actual.get("failure_codes")
                or _record_reasons(disclosure_rec),
                "failure_reason": disclosure_rec.get("failure_reason")
                or (_record_reasons(disclosure_rec)[0] if _record_reasons(disclosure_rec) else None),
                "status": disclosure_rec.get("status"),
            },
            "callback_web": {
                "policy_present": bool(callback_expected.get("policy_present")),
                "policy_enabled": bool(callback_expected.get("policy_enabled")),
                "callback_web_id": callback_actual.get("callback_web_id"),
                "selected_callback_edge_id": callback_selected.get("selected_callback_edge_id"),
                "selected_callback_kind": callback_selected.get("selected_callback_kind"),
                "selected_continuity_classes": callback_selected.get("selected_continuity_classes")
                or [],
                "selected_thread_ids": callback_selected.get("selected_thread_ids") or [],
                "edge_count": int(callback_actual.get("edge_count") or 0),
                "observation_count": int(callback_actual.get("observation_count") or 0),
                "graph_edge_count": int(callback_actual.get("graph_edge_count") or 0),
                "callback_kind_counts": callback_actual.get("callback_kind_counts") or {},
                "continuity_classes": callback_actual.get("continuity_classes") or [],
                "thread_ids": callback_actual.get("thread_ids") or [],
                "contract_pass": callback_actual.get("contract_pass"),
                "failure_codes": callback_actual.get("failure_codes")
                or _record_reasons(callback_rec),
                "failure_reason": callback_rec.get("failure_reason")
                or (_record_reasons(callback_rec)[0] if _record_reasons(callback_rec) else None),
                "status": callback_rec.get("status"),
            },
            "hierarchical_memory": {
                "policy_present": bool(memory_expected.get("policy_present")),
                "policy_enabled": bool(memory_expected.get("policy_enabled")),
                "selected_tiers": memory_selected.get("selected_tiers") or [],
                "source_canonical_turn_id": memory_selected.get("source_canonical_turn_id"),
                "write_allowed": bool(memory_actual.get("write_allowed")),
                "written_item_count": int(memory_actual.get("written_item_count") or 0),
                "tiers_written": memory_actual.get("tiers_written") or [],
                "memory_present": bool(memory_actual.get("memory_present")),
                "context_item_count": int(memory_actual.get("context_item_count") or 0),
                "context_bounded": bool(memory_actual.get("context_bounded")),
                "uncommitted_write_detected": bool(memory_actual.get("uncommitted_write_detected")),
                "failure_reason": memory_rec.get("failure_reason")
                or (_record_reasons(memory_rec)[0] if _record_reasons(memory_rec) else None),
                "status": memory_rec.get("status"),
            },
            "branching_forecast": {
                "schema_version": branching_forecast.get("schema_version"),
                "status": branching_forecast.get("status"),
                "source": branching_forecast.get("source"),
                "forecast_only": bool(branching_forecast.get("forecast_only")),
                "authoritative": bool(branching_forecast.get("authoritative")),
                "inactive_branches_authoritative": bool(
                    branching_forecast.get("inactive_branches_authoritative")
                ),
                "mutates_canonical_state": bool(branching_forecast.get("mutates_canonical_state")),
                "selection_required_to_commit": bool(
                    branching_forecast.get("selection_required_to_commit")
                ),
                "trigger_reasons": branching_forecast.get("trigger_reasons") or [],
                "option_count": int(branching_forecast.get("option_count") or 0),
                "options": branching_forecast.get("options") or [],
                "path_signature": branching_forecast.get("path_signature"),
                "dominant_thread_kind": branching_forecast.get("dominant_thread_kind"),
                "thread_pressure_level": int(branching_forecast.get("thread_pressure_level") or 0),
            },
            "commit": {
                "committed": bool(
                    commit_actual.get("committed")
                    if "committed" in commit_actual
                    else commit_actual.get("commit_applied")
                ),
                "degraded": bool(commit_actual.get("degraded")),
                "quality_class": commit_actual.get("quality_class"),
                "validation_status": validation_rec.get("status"),
                "fallback_used": bool(commit_actual.get("fallback_used")),
                "status": commit_rec.get("status"),
            },
        }
    )


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
    runtime_profile_id: str | None = None,
) -> dict[str, Any]:
    if isinstance(ledger, dict) and ledger.get("turn_aspect_ledger"):
        normalized = normalize_runtime_aspect_ledger(ledger)
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
        return normalize_runtime_aspect_ledger(normalized)
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
    actual = aspect.get("actual") if isinstance(aspect.get("actual"), dict) else {}
    selected = aspect.get("selected") if isinstance(aspect.get("selected"), dict) else {}
    target = selected.get("target") if isinstance(selected.get("target"), dict) else {}
    transition = selected.get("transition") if isinstance(selected.get("transition"), dict) else {}
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
        "planned_actor_ids": actual.get("planned_actor_ids"),
        "realized_actor_ids": actual.get("realized_actor_ids"),
        "missing_required_actor_ids": actual.get("missing_required_actor_ids"),
        "candidate_actor_ids": actual.get("candidate_actor_ids"),
        "independent_planning_used": actual.get("independent_planning_used"),
        "npc_agency_closure_status": actual.get("closure_status"),
        "scene_energy_level": selected.get("energy_level") or target.get("energy_level"),
        "scene_energy_transition": selected.get("target_transition")
        or transition.get("transition_intent"),
        "scene_energy_contract_pass": actual.get("contract_pass"),
        "scene_energy_failure_codes": actual.get("failure_codes"),
        "information_disclosure_selected_unit_ids": selected.get("selected_unit_ids"),
        "information_disclosure_visible_unit_ids": actual.get("visible_unit_ids"),
        "information_disclosure_contract_pass": actual.get("contract_pass"),
        "information_disclosure_failure_codes": actual.get("failure_codes"),
        "dramatic_irony_selected_opportunity_ids": selected.get("selected_opportunity_ids"),
        "dramatic_irony_selected_fact_ids": selected.get("selected_fact_ids"),
        "dramatic_irony_realization_status": actual.get("realization_status"),
        "dramatic_irony_leak_blocked": actual.get("leak_blocked"),
        "dramatic_irony_violation_codes": actual.get("violation_codes"),
    }
