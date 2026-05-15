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

from ai_stack.capability_selector import (
    derive_turn_situation_from_runtime_context,
    select_capabilities,
)
from ai_stack.capability_validator_dispatch import (
    DEFAULT_VALIDATOR_DISPATCH_MODE,
    ValidatorDispatchMode,
    build_validator_dispatch_report,
)
from ai_stack.capability_validator_plan import build_validator_execution_plan


RUNTIME_ASPECT_LEDGER_VERSION = "runtime_aspect_ledger.v1"
TURN_ASPECT_LEDGER_SCHEMA_VERSION = "turn_aspect_ledger.v1"
RUNTIME_ASPECT_RECORD_VERSION = "runtime_aspect_record.v1"

ASPECT_INPUT = "input"
ASPECT_ACTION_RESOLUTION = "action_resolution"
ASPECT_BEAT = "beat"
ASPECT_SCENE_ENERGY = "scene_energy"
ASPECT_PACING_RHYTHM = "pacing_rhythm"
ASPECT_SENSORY_CONTEXT = "sensory_context"
ASPECT_IMPROVISATIONAL_COHERENCE = "improvisational_coherence"
ASPECT_META_NARRATIVE_AWARENESS = "meta_narrative_awareness"
ASPECT_SOCIAL_PRESSURE = "social_pressure"
ASPECT_RELATIONSHIP_STATE = "relationship_state"
ASPECT_CAPABILITY_SELECTION = "capability_selection"
ASPECT_NARRATOR_AUTHORITY = "narrator_authority"
ASPECT_NPC_AUTHORITY = "npc_authority"
ASPECT_NPC_AGENCY = "npc_agency"
ASPECT_DRAMATIC_IRONY = "dramatic_irony"
ASPECT_EXPECTATION_VARIATION = "expectation_variation"
ASPECT_VOICE_CONSISTENCY = "voice_consistency"
ASPECT_NARRATIVE_ASPECT = "narrative_aspect"
ASPECT_INFORMATION_DISCLOSURE = "information_disclosure"
ASPECT_HIERARCHICAL_MEMORY = "hierarchical_memory"
ASPECT_CALLBACK_WEB = "callback_web"
ASPECT_CONSEQUENCE_CASCADE = "consequence_cascade"
ASPECT_TEMPORAL_CONTROL = "temporal_control"
ASPECT_VALIDATION = "validation"
ASPECT_COMMIT = "commit"
ASPECT_VISIBLE_PROJECTION = "visible_projection"

ASPECT_KEYS: tuple[str, ...] = (
    ASPECT_INPUT,
    ASPECT_ACTION_RESOLUTION,
    ASPECT_BEAT,
    ASPECT_SCENE_ENERGY,
    ASPECT_PACING_RHYTHM,
    ASPECT_SENSORY_CONTEXT,
    ASPECT_IMPROVISATIONAL_COHERENCE,
    ASPECT_META_NARRATIVE_AWARENESS,
    ASPECT_SOCIAL_PRESSURE,
    ASPECT_RELATIONSHIP_STATE,
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_NARRATOR_AUTHORITY,
    ASPECT_NPC_AUTHORITY,
    ASPECT_NPC_AGENCY,
    ASPECT_DRAMATIC_IRONY,
    ASPECT_EXPECTATION_VARIATION,
    ASPECT_VOICE_CONSISTENCY,
    ASPECT_NARRATIVE_ASPECT,
    ASPECT_INFORMATION_DISCLOSURE,
    ASPECT_HIERARCHICAL_MEMORY,
    ASPECT_CALLBACK_WEB,
    ASPECT_CONSEQUENCE_CASCADE,
    ASPECT_TEMPORAL_CONTROL,
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


def build_semantic_capability_selection_projection(
    *,
    turn_kind: str | None = None,
    turn_number: int | None = None,
    raw_player_input: str | None = None,
    input_kind: str | None = None,
    active_actor: str | None = None,
    npc_decision_required: bool | None = None,
    action_resolution_required: bool | None = None,
    visible_projection_required: bool | None = None,
    canonical_scene_seed: bool | None = None,
    non_lexical_input_present: bool | None = None,
    knowledge_gap_present: bool | None = None,
    world_state_change_requested: bool | None = None,
) -> dict[str, Any]:
    """Build ADR-0041 local selector evidence for runtime intelligence projection."""
    selection_result, derivation_warnings = _select_semantic_capabilities_from_runtime_context(
        turn_kind=turn_kind,
        turn_number=turn_number,
        raw_player_input=raw_player_input,
        input_kind=input_kind,
        active_actor=active_actor,
        npc_decision_required=npc_decision_required,
        action_resolution_required=action_resolution_required,
        visible_projection_required=visible_projection_required,
        canonical_scene_seed=canonical_scene_seed,
        non_lexical_input_present=non_lexical_input_present,
        knowledge_gap_present=knowledge_gap_present,
        world_state_change_requested=world_state_change_requested,
    )
    payload = selection_result.to_runtime_aspect_projection()[
        ASPECT_CAPABILITY_SELECTION
    ]
    warnings = [
        *(
            payload.get("warnings")
            if isinstance(payload.get("warnings"), list)
            else []
        ),
        *derivation_warnings,
    ]
    payload["warnings"] = [str(warning) for warning in warnings if str(warning).strip()]
    return _json_safe(payload)


def build_semantic_validator_execution_plan_projection(
    *,
    turn_kind: str | None = None,
    turn_number: int | None = None,
    raw_player_input: str | None = None,
    input_kind: str | None = None,
    active_actor: str | None = None,
    npc_decision_required: bool | None = None,
    action_resolution_required: bool | None = None,
    visible_projection_required: bool | None = None,
    canonical_scene_seed: bool | None = None,
    non_lexical_input_present: bool | None = None,
    knowledge_gap_present: bool | None = None,
    world_state_change_requested: bool | None = None,
) -> dict[str, Any]:
    """Build ADR-0041 local validator-plan evidence for runtime projection."""
    selection_result, derivation_warnings = _select_semantic_capabilities_from_runtime_context(
        turn_kind=turn_kind,
        turn_number=turn_number,
        raw_player_input=raw_player_input,
        input_kind=input_kind,
        active_actor=active_actor,
        npc_decision_required=npc_decision_required,
        action_resolution_required=action_resolution_required,
        visible_projection_required=visible_projection_required,
        canonical_scene_seed=canonical_scene_seed,
        non_lexical_input_present=non_lexical_input_present,
        knowledge_gap_present=knowledge_gap_present,
        world_state_change_requested=world_state_change_requested,
    )
    payload = build_validator_execution_plan(selection_result).to_runtime_projection()[
        "validator_execution_plan"
    ]
    warnings = [
        *(
            payload.get("warnings")
            if isinstance(payload.get("warnings"), list)
            else []
        ),
        *derivation_warnings,
    ]
    payload["warnings"] = [str(warning) for warning in warnings if str(warning).strip()]
    return _json_safe(payload)


def _select_semantic_capabilities_from_runtime_context(
    *,
    turn_kind: str | None = None,
    turn_number: int | None = None,
    raw_player_input: str | None = None,
    input_kind: str | None = None,
    active_actor: str | None = None,
    npc_decision_required: bool | None = None,
    action_resolution_required: bool | None = None,
    visible_projection_required: bool | None = None,
    canonical_scene_seed: bool | None = None,
    non_lexical_input_present: bool | None = None,
    knowledge_gap_present: bool | None = None,
    world_state_change_requested: bool | None = None,
) -> tuple[Any, tuple[str, ...]]:
    situation, derivation_warnings = derive_turn_situation_from_runtime_context(
        turn_kind=turn_kind,
        turn_number=turn_number,
        raw_player_input=raw_player_input,
        input_kind=input_kind,
        active_actor=active_actor,
        npc_decision_required=npc_decision_required,
        action_resolution_required=action_resolution_required,
        visible_projection_required=visible_projection_required,
        canonical_scene_seed=canonical_scene_seed,
        non_lexical_input_present=non_lexical_input_present,
        knowledge_gap_present=knowledge_gap_present,
        world_state_change_requested=world_state_change_requested,
    )
    return select_capabilities(situation), derivation_warnings


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
    sensory_context_rec = (
        aspects.get(ASPECT_SENSORY_CONTEXT)
        if isinstance(aspects.get(ASPECT_SENSORY_CONTEXT), dict)
        else {}
    )
    improvisational_rec = (
        aspects.get(ASPECT_IMPROVISATIONAL_COHERENCE)
        if isinstance(aspects.get(ASPECT_IMPROVISATIONAL_COHERENCE), dict)
        else {}
    )
    meta_narrative_rec = (
        aspects.get(ASPECT_META_NARRATIVE_AWARENESS)
        if isinstance(aspects.get(ASPECT_META_NARRATIVE_AWARENESS), dict)
        else {}
    )
    social_pressure_rec = (
        aspects.get(ASPECT_SOCIAL_PRESSURE)
        if isinstance(aspects.get(ASPECT_SOCIAL_PRESSURE), dict)
        else {}
    )
    relationship_state_rec = (
        aspects.get(ASPECT_RELATIONSHIP_STATE)
        if isinstance(aspects.get(ASPECT_RELATIONSHIP_STATE), dict)
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
    expectation_variation_rec = (
        aspects.get(ASPECT_EXPECTATION_VARIATION)
        if isinstance(aspects.get(ASPECT_EXPECTATION_VARIATION), dict)
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
    cascade_rec = (
        aspects.get(ASPECT_CONSEQUENCE_CASCADE)
        if isinstance(aspects.get(ASPECT_CONSEQUENCE_CASCADE), dict)
        else {}
    )
    temporal_control_rec = (
        aspects.get(ASPECT_TEMPORAL_CONTROL)
        if isinstance(aspects.get(ASPECT_TEMPORAL_CONTROL), dict)
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
    sensory_context_expected = _record_block(sensory_context_rec, "expected")
    sensory_context_selected = _record_block(sensory_context_rec, "selected")
    sensory_context_actual = _record_block(sensory_context_rec, "actual")
    improvisational_expected = _record_block(improvisational_rec, "expected")
    improvisational_selected = _record_block(improvisational_rec, "selected")
    improvisational_actual = _record_block(improvisational_rec, "actual")
    meta_narrative_expected = _record_block(meta_narrative_rec, "expected")
    meta_narrative_selected = _record_block(meta_narrative_rec, "selected")
    meta_narrative_actual = _record_block(meta_narrative_rec, "actual")
    social_pressure_expected = _record_block(social_pressure_rec, "expected")
    social_pressure_selected = _record_block(social_pressure_rec, "selected")
    social_pressure_actual = _record_block(social_pressure_rec, "actual")
    relationship_state_expected = _record_block(relationship_state_rec, "expected")
    relationship_state_selected = _record_block(relationship_state_rec, "selected")
    relationship_state_actual = _record_block(relationship_state_rec, "actual")
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
    expectation_variation_expected = _record_block(expectation_variation_rec, "expected")
    expectation_variation_selected = _record_block(expectation_variation_rec, "selected")
    expectation_variation_actual = _record_block(expectation_variation_rec, "actual")
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
    cascade_expected = _record_block(cascade_rec, "expected")
    cascade_selected = _record_block(cascade_rec, "selected")
    cascade_actual = _record_block(cascade_rec, "actual")
    temporal_control_expected = _record_block(temporal_control_rec, "expected")
    temporal_control_selected = _record_block(temporal_control_rec, "selected")
    temporal_control_actual = _record_block(temporal_control_rec, "actual")
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
    npc_decision_required_signal = bool(
        npc_agency_expected.get("candidate_actor_ids")
        or npc_agency_selected.get("selected_private_plan_actor_ids")
        or npc_agency_actual.get("planned_actor_ids")
    )
    knowledge_gap_signal = bool(
        dramatic_irony_selected.get("selected_opportunity_ids")
        or dramatic_irony_selected.get("selected_fact_ids")
        or dramatic_irony_actual.get("opportunity_count")
        or dramatic_irony_actual.get("fact_count")
    )
    world_state_change_signal = bool(
        cascade_selected.get("selected_consequence_ids")
        or cascade_actual.get("event_count")
        or cascade_actual.get("consequence_count")
        or cascade_actual.get("committed_consequences")
    )
    raw_player_input_signal = (
        input_actual.get("raw_player_input")
        if "raw_player_input" in input_actual
        else src.get("raw_player_input")
    )
    capability_context = dict(
        turn_kind=src.get("turn_kind"),
        turn_number=src.get("turn_number"),
        raw_player_input=raw_player_input_signal,
        input_kind=input_actual.get("player_input_kind")
        or input_actual.get("input_kind")
        or action_actual.get("input_kind"),
        active_actor=src.get("active_actor"),
        npc_decision_required=npc_decision_required_signal or None,
        action_resolution_required=False if action_rec.get("applicable") is False else None,
        visible_projection_required=True,
        knowledge_gap_present=knowledge_gap_signal,
        world_state_change_requested=world_state_change_signal,
    )
    semantic_capability_selection = build_semantic_capability_selection_projection(
        **capability_context
    )
    semantic_validator_execution_plan = build_semantic_validator_execution_plan_projection(
        **capability_context
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
            "sensory_context": {
                "schema_version": sensory_context_expected.get("schema_version")
                or sensory_context_selected.get("schema_version")
                or sensory_context_actual.get("schema_version"),
                "policy_present": bool(sensory_context_expected.get("policy_present")),
                "policy_enabled": bool(sensory_context_expected.get("policy_enabled")),
                "intensity": _record_nested_value(
                    sensory_context_selected, "intensity", "target"
                ),
                "location_id": _record_nested_value(
                    sensory_context_selected, "location_id", "target"
                ),
                "object_id": _record_nested_value(
                    sensory_context_selected, "object_id", "target"
                ),
                "mood_key": _record_nested_value(
                    sensory_context_selected, "mood_key", "target"
                ),
                "selected_layer_ids": sensory_context_selected.get("selected_layer_ids")
                or (
                    sensory_context_selected.get("target", {}).get("selected_layer_ids")
                    if isinstance(sensory_context_selected.get("target"), dict)
                    else []
                )
                or [],
                "required_layer_ids": sensory_context_selected.get("required_layer_ids")
                or (
                    sensory_context_selected.get("target", {}).get("required_layer_ids")
                    if isinstance(sensory_context_selected.get("target"), dict)
                    else []
                )
                or sensory_context_actual.get("required_layer_ids")
                or [],
                "event_count": int(sensory_context_actual.get("event_count") or 0),
                "realized_layer_ids": sensory_context_actual.get("realized_layer_ids") or [],
                "contract_pass": sensory_context_actual.get("contract_pass"),
                "failure_codes": sensory_context_actual.get("failure_codes")
                or _record_reasons(sensory_context_rec),
                "failure_reason": sensory_context_rec.get("failure_reason")
                or (
                    _record_reasons(sensory_context_rec)[0]
                    if _record_reasons(sensory_context_rec)
                    else None
                ),
                "status": sensory_context_rec.get("status"),
            },
            "improvisational_coherence": {
                "schema_version": improvisational_expected.get("schema_version")
                or improvisational_selected.get("schema_version")
                or improvisational_actual.get("schema_version"),
                "policy_present": bool(improvisational_expected.get("policy_present")),
                "policy_enabled": bool(improvisational_expected.get("policy_enabled")),
                "commit_impact": improvisational_expected.get("commit_impact"),
                "require_structured_events": bool(
                    improvisational_expected.get("require_structured_events")
                ),
                "contribution_id": improvisational_selected.get("contribution_id"),
                "contribution_kind": improvisational_selected.get("contribution_kind"),
                "acceptance_mode": improvisational_selected.get("acceptance_mode")
                or improvisational_actual.get("acceptance_mode"),
                "advance_class": improvisational_actual.get("advance_class"),
                "selected_scene_function": improvisational_selected.get(
                    "selected_scene_function"
                ),
                "visible_actor_ids": improvisational_selected.get("visible_actor_ids") or [],
                "required_anchor_refs": improvisational_selected.get("required_anchor_refs")
                or [],
                "min_anchor_refs": int(
                    improvisational_selected.get("min_anchor_refs")
                    or improvisational_expected.get("min_anchor_refs")
                    or 0
                ),
                "anchor_refs": improvisational_actual.get("anchor_refs") or [],
                "anchor_sources": improvisational_actual.get("anchor_sources") or [],
                "requires_playable_boundary_reason": bool(
                    improvisational_selected.get("requires_playable_boundary_reason")
                ),
                "boundary_reason_code": improvisational_actual.get("boundary_reason_code")
                or improvisational_selected.get("boundary_reason_code"),
                "structured_events_present": bool(
                    improvisational_actual.get("structured_events_present")
                ),
                "event_count": int(improvisational_actual.get("event_count") or 0),
                "contribution_acknowledged": bool(
                    improvisational_actual.get("contribution_acknowledged")
                ),
                "contract_pass": improvisational_actual.get("contract_pass"),
                "failure_codes": improvisational_actual.get("failure_codes")
                or _record_reasons(improvisational_rec),
                "failure_reason": improvisational_rec.get("failure_reason")
                or (
                    _record_reasons(improvisational_rec)[0]
                    if _record_reasons(improvisational_rec)
                    else None
                ),
                "status": improvisational_rec.get("status"),
            },
            "meta_narrative_awareness": {
                "schema_version": meta_narrative_expected.get("schema_version")
                or meta_narrative_selected.get("schema_version")
                or meta_narrative_actual.get("schema_version"),
                "policy_present": bool(meta_narrative_expected.get("policy_present")),
                "policy_enabled": bool(meta_narrative_expected.get("policy_enabled")),
                "opt_in_required": bool(meta_narrative_expected.get("opt_in_required")),
                "opt_in_enabled": bool(meta_narrative_selected.get("opt_in_enabled")),
                "active": bool(meta_narrative_selected.get("active")),
                "awareness_tier": meta_narrative_selected.get("awareness_tier"),
                "intensity": meta_narrative_selected.get("intensity"),
                "trigger_frequency": meta_narrative_selected.get("trigger_frequency"),
                "supported_actor_ids": meta_narrative_selected.get("supported_actor_ids")
                or [],
                "configured_actor_ids": meta_narrative_selected.get("configured_actor_ids")
                or [],
                "selected_actor_ids": meta_narrative_selected.get("selected_actor_ids")
                or [],
                "allowed_awareness_modes": meta_narrative_expected.get(
                    "allowed_awareness_modes"
                )
                or [],
                "forbidden_awareness_modes": meta_narrative_expected.get(
                    "forbidden_awareness_modes"
                )
                or [],
                "allowed_fourth_wall_levels": meta_narrative_expected.get(
                    "allowed_fourth_wall_levels"
                )
                or [],
                "max_events_per_turn": int(
                    meta_narrative_selected.get("max_events_per_turn") or 0
                ),
                "max_direct_addresses_per_turn": int(
                    meta_narrative_selected.get("max_direct_addresses_per_turn") or 0
                ),
                "direct_player_address_allowed": bool(
                    meta_narrative_selected.get("direct_player_address_allowed")
                ),
                "narrator_negotiation_allowed": bool(
                    meta_narrative_selected.get("narrator_negotiation_allowed")
                ),
                "cross_session_memory_allowed": bool(
                    meta_narrative_selected.get("cross_session_memory_allowed")
                ),
                "selected_memory_ref_ids": meta_narrative_selected.get(
                    "selected_memory_ref_ids"
                )
                or [],
                "adaptive_signal_codes": meta_narrative_selected.get(
                    "adaptive_signal_codes"
                )
                or [],
                "structured_events_present": bool(
                    meta_narrative_actual.get("structured_events_present")
                ),
                "event_count": int(meta_narrative_actual.get("event_count") or 0),
                "realized_actor_ids": meta_narrative_actual.get("realized_actor_ids")
                or [],
                "awareness_modes": meta_narrative_actual.get("awareness_modes") or [],
                "fourth_wall_levels": meta_narrative_actual.get("fourth_wall_levels")
                or [],
                "direct_address_count": int(
                    meta_narrative_actual.get("direct_address_count") or 0
                ),
                "realized_memory_ref_ids": meta_narrative_actual.get(
                    "realized_memory_ref_ids"
                )
                or [],
                "cross_session_memory_ref_count": int(
                    meta_narrative_actual.get("cross_session_memory_ref_count") or 0
                ),
                "contract_pass": meta_narrative_actual.get("contract_pass"),
                "failure_codes": meta_narrative_actual.get("failure_codes")
                or _record_reasons(meta_narrative_rec),
                "failure_reason": meta_narrative_rec.get("failure_reason")
                or (
                    _record_reasons(meta_narrative_rec)[0]
                    if _record_reasons(meta_narrative_rec)
                    else None
                ),
                "status": meta_narrative_rec.get("status"),
            },
            "social_pressure": {
                "schema_version": social_pressure_expected.get("schema_version")
                or social_pressure_selected.get("schema_version")
                or social_pressure_actual.get("schema_version"),
                "policy_present": bool(social_pressure_expected.get("policy_present")),
                "policy_enabled": bool(social_pressure_expected.get("policy_enabled")),
                "target_score": float(
                    social_pressure_selected.get("target_score")
                    or (
                        social_pressure_selected.get("target", {}).get("target_score")
                        if isinstance(social_pressure_selected.get("target"), dict)
                        else 0.0
                    )
                    or 0.0
                ),
                "target_band": social_pressure_selected.get("target_band")
                or (
                    social_pressure_selected.get("target", {}).get("target_band")
                    if isinstance(social_pressure_selected.get("target"), dict)
                    else None
                ),
                "trend": social_pressure_selected.get("trend")
                or (
                    social_pressure_selected.get("target", {}).get("trend")
                    if isinstance(social_pressure_selected.get("target"), dict)
                    else None
                )
                or social_pressure_actual.get("trend"),
                "current_score": float(social_pressure_actual.get("current_score") or 0.0),
                "current_band": social_pressure_actual.get("current_band"),
                "velocity": float(social_pressure_actual.get("velocity") or 0.0),
                "requires_visible_pressure": bool(
                    social_pressure_selected.get("requires_visible_pressure")
                    or (
                        social_pressure_selected.get("target", {}).get("requires_visible_pressure")
                        if isinstance(social_pressure_selected.get("target"), dict)
                        else False
                    )
                ),
                "contract_pass": social_pressure_actual.get("contract_pass"),
                "failure_codes": social_pressure_actual.get("failure_codes")
                or _record_reasons(social_pressure_rec),
                "failure_reason": social_pressure_rec.get("failure_reason")
                or (
                    _record_reasons(social_pressure_rec)[0]
                    if _record_reasons(social_pressure_rec)
                    else None
                ),
                "status": social_pressure_rec.get("status"),
            },
            "relationship_state": {
                "schema_version": relationship_state_expected.get("schema_version")
                or relationship_state_selected.get("schema_version")
                or relationship_state_actual.get("schema_version"),
                "policy_present": bool(relationship_state_expected.get("policy_present")),
                "policy_enabled": bool(relationship_state_expected.get("policy_enabled")),
                "target_axis_ids": relationship_state_selected.get("target_axis_ids")
                or (
                    relationship_state_selected.get("target", {}).get("target_axis_ids")
                    if isinstance(relationship_state_selected.get("target"), dict)
                    else []
                )
                or [],
                "target_relationship_ids": relationship_state_selected.get("target_relationship_ids")
                or (
                    relationship_state_selected.get("target", {}).get("target_relationship_ids")
                    if isinstance(relationship_state_selected.get("target"), dict)
                    else []
                )
                or [],
                "pressure_band": relationship_state_selected.get("pressure_band")
                or (
                    relationship_state_selected.get("target", {}).get("pressure_band")
                    if isinstance(relationship_state_selected.get("target"), dict)
                    else None
                ),
                "requires_visible_relationship_beat": bool(
                    relationship_state_selected.get("requires_visible_relationship_beat")
                    or (
                        relationship_state_selected.get("target", {}).get("requires_visible_relationship_beat")
                        if isinstance(relationship_state_selected.get("target"), dict)
                        else False
                    )
                ),
                "pair_count": int(relationship_state_actual.get("pair_count") or 0),
                "axis_count": int(relationship_state_actual.get("axis_count") or 0),
                "transition_event_count": int(
                    relationship_state_actual.get("transition_event_count") or 0
                ),
                "contract_pass": relationship_state_actual.get("contract_pass"),
                "failure_codes": relationship_state_actual.get("failure_codes")
                or _record_reasons(relationship_state_rec),
                "failure_reason": relationship_state_rec.get("failure_reason")
                or (
                    _record_reasons(relationship_state_rec)[0]
                    if _record_reasons(relationship_state_rec)
                    else None
                ),
                "status": relationship_state_rec.get("status"),
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
            "capability_selection": semantic_capability_selection,
            "validator_execution_plan": semantic_validator_execution_plan,
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
            "expectation_variation": {
                "schema_version": expectation_variation_expected.get("schema_version")
                or expectation_variation_actual.get("schema_version"),
                "policy_present": bool(expectation_variation_expected.get("policy_present")),
                "policy_enabled": bool(expectation_variation_expected.get("policy_enabled")),
                "commit_impact": expectation_variation_expected.get("commit_impact"),
                "require_structured_events": bool(
                    expectation_variation_expected.get("require_structured_events")
                ),
                "max_variation_units_per_turn": int(
                    expectation_variation_expected.get("max_variation_units_per_turn")
                    or 0
                ),
                "cooldown_turns": int(
                    expectation_variation_expected.get("cooldown_turns") or 0
                ),
                "allowed_variation_types": expectation_variation_expected.get(
                    "allowed_variation_types"
                )
                or [],
                "selected_variation_ids": expectation_variation_selected.get(
                    "selected_variation_ids"
                )
                or [],
                "selected_variation_types": expectation_variation_selected.get(
                    "selected_variation_types"
                )
                or [],
                "withheld_variation_ids": expectation_variation_selected.get(
                    "withheld_variation_ids"
                )
                or [],
                "required_setup_refs": expectation_variation_selected.get(
                    "required_setup_refs"
                )
                or [],
                "budget_remaining": int(
                    expectation_variation_selected.get("budget_remaining")
                    or expectation_variation_actual.get("budget_remaining")
                    or 0
                ),
                "structured_events_present": bool(
                    expectation_variation_actual.get("structured_events_present")
                ),
                "event_count": int(expectation_variation_actual.get("event_count") or 0),
                "realized_variation_ids": expectation_variation_actual.get(
                    "realized_variation_ids"
                )
                or [],
                "realized_variation_types": expectation_variation_actual.get(
                    "realized_variation_types"
                )
                or [],
                "budget_used": int(expectation_variation_actual.get("budget_used") or 0),
                "contract_pass": expectation_variation_actual.get("contract_pass"),
                "failure_codes": expectation_variation_actual.get("failure_codes")
                or _record_reasons(expectation_variation_rec),
                "failure_reason": expectation_variation_rec.get("failure_reason")
                or (
                    _record_reasons(expectation_variation_rec)[0]
                    if _record_reasons(expectation_variation_rec)
                    else None
                ),
                "status": expectation_variation_rec.get("status"),
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
            "consequence_cascade": {
                "policy_present": bool(cascade_expected.get("policy_present")),
                "policy_enabled": bool(cascade_expected.get("policy_enabled")),
                "cascade_id": cascade_actual.get("cascade_id"),
                "selected_consequence_ids": cascade_selected.get("selected_consequence_ids")
                or [],
                "selected_edge_ids": cascade_selected.get("selected_edge_ids") or [],
                "selected_continuity_classes": cascade_selected.get("selected_continuity_classes")
                or [],
                "selected_statuses": cascade_selected.get("selected_statuses") or [],
                "atom_count": int(cascade_actual.get("atom_count") or 0),
                "edge_count": int(cascade_actual.get("edge_count") or 0),
                "active_atom_count": int(cascade_actual.get("active_atom_count") or 0),
                "graph_item_count": int(cascade_actual.get("graph_item_count") or 0),
                "status_counts": cascade_actual.get("status_counts") or {},
                "edge_kind_counts": cascade_actual.get("edge_kind_counts") or {},
                "continuity_classes": cascade_actual.get("continuity_classes") or [],
                "contract_pass": cascade_actual.get("contract_pass"),
                "failure_codes": cascade_actual.get("failure_codes")
                or _record_reasons(cascade_rec),
                "failure_reason": cascade_rec.get("failure_reason")
                or (_record_reasons(cascade_rec)[0] if _record_reasons(cascade_rec) else None),
                "status": cascade_rec.get("status"),
            },
            "temporal_control": {
                "schema_version": temporal_control_expected.get("schema_version")
                or temporal_control_selected.get("schema_version")
                or temporal_control_actual.get("schema_version"),
                "policy_present": bool(temporal_control_expected.get("policy_present")),
                "policy_enabled": bool(temporal_control_expected.get("policy_enabled")),
                "commit_impact": temporal_control_expected.get("commit_impact"),
                "require_structured_events": bool(
                    temporal_control_expected.get("require_structured_events")
                ),
                "allowed_operations": temporal_control_expected.get("allowed_operations")
                or [],
                "operation": temporal_control_selected.get("operation")
                or _record_nested_value(temporal_control_selected, "operation", "target")
                or temporal_control_actual.get("operation"),
                "anchor_turn_id": temporal_control_selected.get("anchor_turn_id")
                or _record_nested_value(temporal_control_selected, "anchor_turn_id", "target"),
                "anchor_turn_number": temporal_control_selected.get("anchor_turn_number")
                or _record_nested_value(
                    temporal_control_selected, "anchor_turn_number", "target"
                ),
                "recalled_turn_ids": temporal_control_selected.get("recalled_turn_ids")
                or (
                    temporal_control_selected.get("target", {}).get("recalled_turn_ids")
                    if isinstance(temporal_control_selected.get("target"), dict)
                    else []
                )
                or [],
                "recalled_consequence_ids": temporal_control_selected.get(
                    "recalled_consequence_ids"
                )
                or (
                    temporal_control_selected.get("target", {}).get(
                        "recalled_consequence_ids"
                    )
                    if isinstance(temporal_control_selected.get("target"), dict)
                    else []
                )
                or [],
                "max_recalled_turns": int(
                    temporal_control_expected.get("max_recalled_turns") or 0
                ),
                "max_elapsed_turns": int(
                    temporal_control_expected.get("max_elapsed_turns") or 0
                ),
                "elapsed_turns": int(
                    temporal_control_actual.get("elapsed_turns")
                    or temporal_control_selected.get("elapsed_turns")
                    or (
                        temporal_control_selected.get("state", {}).get("elapsed_turns")
                        if isinstance(temporal_control_selected.get("state"), dict)
                        else 0
                    )
                    or 0
                ),
                "structured_events_present": bool(
                    temporal_control_actual.get("structured_events_present")
                ),
                "event_count": int(temporal_control_actual.get("event_count") or 0),
                "realized_operations": temporal_control_actual.get(
                    "realized_operations"
                )
                or [],
                "realized_turn_ids": temporal_control_actual.get("realized_turn_ids")
                or [],
                "realized_consequence_ids": temporal_control_actual.get(
                    "realized_consequence_ids"
                )
                or [],
                "contract_pass": temporal_control_actual.get("contract_pass"),
                "failure_codes": temporal_control_actual.get("failure_codes")
                or _record_reasons(temporal_control_rec),
                "failure_reason": temporal_control_rec.get("failure_reason")
                or (
                    _record_reasons(temporal_control_rec)[0]
                    if _record_reasons(temporal_control_rec)
                    else None
                ),
                "status": temporal_control_rec.get("status"),
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
        "sensory_context_intensity": selected.get("intensity") or target.get("intensity"),
        "sensory_context_location_id": selected.get("location_id") or target.get("location_id"),
        "sensory_context_object_id": selected.get("object_id") or target.get("object_id"),
        "sensory_context_selected_layer_ids": selected.get("selected_layer_ids")
        or target.get("selected_layer_ids"),
        "sensory_context_realized_layer_ids": actual.get("realized_layer_ids"),
        "sensory_context_contract_pass": actual.get("contract_pass"),
        "sensory_context_failure_codes": actual.get("failure_codes"),
        "improvisational_coherence_contribution_id": selected.get("contribution_id"),
        "improvisational_coherence_contribution_kind": selected.get("contribution_kind"),
        "improvisational_coherence_acceptance_mode": selected.get("acceptance_mode")
        or actual.get("acceptance_mode"),
        "improvisational_coherence_advance_class": actual.get("advance_class"),
        "improvisational_coherence_acknowledged": actual.get("contribution_acknowledged"),
        "improvisational_coherence_contract_pass": actual.get("contract_pass"),
        "improvisational_coherence_failure_codes": actual.get("failure_codes"),
        "meta_narrative_awareness_active": selected.get("active"),
        "meta_narrative_awareness_tier": selected.get("awareness_tier"),
        "meta_narrative_awareness_intensity": selected.get("intensity"),
        "meta_narrative_awareness_trigger_frequency": selected.get("trigger_frequency"),
        "meta_narrative_awareness_selected_actor_ids": selected.get("selected_actor_ids"),
        "meta_narrative_awareness_direct_address_allowed": selected.get(
            "direct_player_address_allowed"
        ),
        "meta_narrative_awareness_cross_session_memory_allowed": selected.get(
            "cross_session_memory_allowed"
        ),
        "meta_narrative_awareness_selected_memory_ref_ids": selected.get(
            "selected_memory_ref_ids"
        ),
        "meta_narrative_awareness_adaptive_signal_codes": selected.get(
            "adaptive_signal_codes"
        ),
        "meta_narrative_awareness_event_count": actual.get("event_count"),
        "meta_narrative_awareness_direct_address_count": actual.get(
            "direct_address_count"
        ),
        "meta_narrative_awareness_realized_memory_ref_ids": actual.get(
            "realized_memory_ref_ids"
        ),
        "meta_narrative_awareness_contract_pass": actual.get("contract_pass"),
        "meta_narrative_awareness_failure_codes": actual.get("failure_codes"),
        "social_pressure_target_score": selected.get("target_score")
        or target.get("target_score"),
        "social_pressure_target_band": selected.get("target_band")
        or target.get("target_band"),
        "social_pressure_current_score": actual.get("current_score"),
        "social_pressure_current_band": actual.get("current_band"),
        "social_pressure_trend": selected.get("trend")
        or target.get("trend")
        or actual.get("trend"),
        "social_pressure_contract_pass": actual.get("contract_pass"),
        "social_pressure_failure_codes": actual.get("failure_codes"),
        "information_disclosure_selected_unit_ids": selected.get("selected_unit_ids"),
        "information_disclosure_visible_unit_ids": actual.get("visible_unit_ids"),
        "information_disclosure_contract_pass": actual.get("contract_pass"),
        "information_disclosure_failure_codes": actual.get("failure_codes"),
        "expectation_variation_selected_ids": selected.get("selected_variation_ids"),
        "expectation_variation_selected_types": selected.get("selected_variation_types"),
        "expectation_variation_realized_ids": actual.get("realized_variation_ids"),
        "expectation_variation_realized_types": actual.get("realized_variation_types"),
        "expectation_variation_budget_used": actual.get("budget_used"),
        "expectation_variation_contract_pass": actual.get("contract_pass"),
        "expectation_variation_failure_codes": actual.get("failure_codes"),
        "consequence_cascade_selected_consequence_ids": selected.get("selected_consequence_ids"),
        "consequence_cascade_selected_edge_ids": selected.get("selected_edge_ids"),
        "consequence_cascade_selected_continuity_classes": selected.get(
            "selected_continuity_classes"
        ),
        "consequence_cascade_selected_statuses": selected.get("selected_statuses"),
        "consequence_cascade_atom_count": actual.get("atom_count"),
        "consequence_cascade_edge_count": actual.get("edge_count"),
        "consequence_cascade_contract_pass": actual.get("contract_pass"),
        "consequence_cascade_failure_codes": actual.get("failure_codes"),
        "dramatic_irony_selected_opportunity_ids": selected.get("selected_opportunity_ids"),
        "dramatic_irony_selected_fact_ids": selected.get("selected_fact_ids"),
        "dramatic_irony_realization_status": actual.get("realization_status"),
        "dramatic_irony_leak_blocked": actual.get("leak_blocked"),
        "dramatic_irony_violation_codes": actual.get("violation_codes"),
    }
