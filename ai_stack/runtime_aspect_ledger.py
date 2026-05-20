"""Backend-owned runtime aspect ledger for story turns.

The ledger is not a frontend display contract.  Authority-relevant aspects are
designed to be consumed by validation and commit before being emitted to
diagnostics or Langfuse.
"""

from __future__ import annotations

import copy
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any

from ai_stack.capabilities.capability_selector import (
    CapabilitySelectionResult,
    LastTurnQuality,
    TurnKind,
    TurnSituation,
    derive_turn_situation_from_runtime_context,
    select_capabilities,
    validate_semantic_capability_name,
)
from ai_stack.capabilities.capability_validator_dispatch import (
    ValidatorDispatchMode,
    ValidatorRegistry,
    build_validator_dispatch_report,
    resolve_validator_dispatch_mode,
)
from ai_stack.capabilities.capability_validator_plan import (
    ValidatorExecutionPlan,
    build_validator_execution_plan,
    prepend_goc_seam_mirror_plan_entries,
)
from ai_stack.capabilities.capability_validator_registry import (
    VALIDATOR_REGISTRY_INVENTORY,
    TURN_CLASS_DEGRADED_OR_FALLBACK_TURN,
    TURN_CLASS_NPC_CONFLICT_TURN,
    TURN_CLASS_NORMAL_PLAYER_TURN,
    TURN_CLASS_OPENING_SCENE,
    TURN_CLASS_RECOVERY_TURN,
    TURN_CLASS_SYSTEM_TRANSITION,
    build_available_semantic_validator_registry,
    build_degraded_or_fallback_enforced_semantic_validator_registry,
    build_npc_conflict_enforced_semantic_validator_registry,
    build_opening_enforced_semantic_validator_registry,
    build_player_turn_enforced_semantic_validator_registry,
    build_recovery_turn_enforced_semantic_validator_registry,
    build_system_transition_enforced_semantic_validator_registry,
    goc_seam_mirror_plan_validator_ids_for_turn_class,
)
from ai_stack.story_runtime.turn.validation_authority_bridge import (
    build_readiness_aggregation_decision,
    build_readiness_co_authority_enforcement,
    build_readiness_co_authority_preview,
    build_validation_authority_bridge,
    build_validation_co_authority_decision,
)


RUNTIME_ASPECT_LEDGER_VERSION = "runtime_aspect_ledger.v1"
TURN_ASPECT_LEDGER_SCHEMA_VERSION = "turn_aspect_ledger.v1"
RUNTIME_ASPECT_RECORD_VERSION = "runtime_aspect_record.v1"

ADR0041_HARNESS_PLAN_ENFORCED_REQUIRES_REGISTRY_WARNING = (
    "adr0041_harness_plan_enforced_requires_explicit_validator_registry"
)

ADR0041_PLAN_PROJECTION_ENABLED_ENV = "ADR0041_PLAN_PROJECTION_ENABLED"
ADR0041_PLAN_PROJECTION_SCHEMA_VERSION = "adr0041_plan_projection.v1"
ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV = "ADR0041_SCOPED_CO_AUTHORITY_ENABLED"
ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV = "ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED"
ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV = "ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED"
ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV = "ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED"
ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV = "ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED"

# Ephemeral bundle attached by LangGraph validate_seam when
# ``ADR0041_VALIDATOR_DISPATCH_MODE=plan_enforced``. Retained on the ledger so
# repeated ``normalize_runtime_aspect_ledger`` calls recompute the same sidecar.
ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY = "_adr0041_runtime_graph_dispatch_context"
# Dispatch bundle is runtime-only: not canonical commit truth, not player-facing gameplay state.
# Consumed when building ``runtime_intelligence_projection`` (local-only, diagnostics / Langfuse / MCP).

ADR0041_VALIDATION_AUTHORITY_PREVIEW_SCHEMA_VERSION = "adr0041_validation_authority_preview.v1"
ADR0041_DRIFT_ALIGNED = "aligned"
ADR0041_DRIFT_ADR_STRICTER = "adr0041_stricter"
ADR0041_DRIFT_SEAM_STRICTER = "seam_stricter"
ADR0041_DRIFT_MISSING_CONTEXT = "missing_context"
ADR0041_DRIFT_UNAVAILABLE_VALIDATOR = "unavailable_validator"
ADR0041_DRIFT_CONFLICTING_RESULT = "conflicting_result"

ASPECT_INPUT = "input"
ASPECT_BROAD_NLU_LISTENING = "broad_nlu_listening"
ASPECT_ACTION_RESOLUTION = "action_resolution"
ASPECT_CONVERSATIONAL_MEMORY = "conversational_memory"
ASPECT_PROMPT_AUTHORITY = "prompt_authority"
ASPECT_BEAT = "beat"
ASPECT_SCENE_ENERGY = "scene_energy"
ASPECT_PACING_RHYTHM = "pacing_rhythm"
ASPECT_SENSORY_CONTEXT = "sensory_context"
ASPECT_SYMBOLIC_OBJECT_RESONANCE = "symbolic_object_resonance"
ASPECT_IMPROVISATIONAL_COHERENCE = "improvisational_coherence"
ASPECT_META_NARRATIVE_AWARENESS = "meta_narrative_awareness"
ASPECT_NO_DEAD_END_RECOVERY = "no_dead_end_recovery"
ASPECT_SOCIAL_PRESSURE = "social_pressure"
ASPECT_RELATIONSHIP_STATE = "relationship_state"
ASPECT_CAPABILITY_SELECTION = "capability_selection"
ASPECT_NARRATOR_AUTHORITY = "narrator_authority"
ASPECT_NPC_AUTHORITY = "npc_authority"
ASPECT_NPC_AGENCY = "npc_agency"
ASPECT_DRAMATIC_IRONY = "dramatic_irony"
ASPECT_EXPECTATION_VARIATION = "expectation_variation"
ASPECT_NARRATIVE_MOMENTUM = "narrative_momentum"
ASPECT_VOICE_CONSISTENCY = "voice_consistency"
ASPECT_TONAL_CONSISTENCY = "tonal_consistency"
ASPECT_GENRE_AWARENESS = "genre_awareness"
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
    ASPECT_BROAD_NLU_LISTENING,
    ASPECT_ACTION_RESOLUTION,
    ASPECT_CONVERSATIONAL_MEMORY,
    ASPECT_PROMPT_AUTHORITY,
    ASPECT_BEAT,
    ASPECT_SCENE_ENERGY,
    ASPECT_PACING_RHYTHM,
    ASPECT_SENSORY_CONTEXT,
    ASPECT_SYMBOLIC_OBJECT_RESONANCE,
    ASPECT_IMPROVISATIONAL_COHERENCE,
    ASPECT_META_NARRATIVE_AWARENESS,
    ASPECT_NO_DEAD_END_RECOVERY,
    ASPECT_SOCIAL_PRESSURE,
    ASPECT_RELATIONSHIP_STATE,
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_NARRATOR_AUTHORITY,
    ASPECT_NPC_AUTHORITY,
    ASPECT_NPC_AGENCY,
    ASPECT_DRAMATIC_IRONY,
    ASPECT_EXPECTATION_VARIATION,
    ASPECT_NARRATIVE_MOMENTUM,
    ASPECT_VOICE_CONSISTENCY,
    ASPECT_TONAL_CONSISTENCY,
    ASPECT_GENRE_AWARENESS,
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
    rip = build_runtime_intelligence_projection(src)
    src["runtime_intelligence_projection"] = rip
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


def build_semantic_validator_dispatch_report_projection(
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
    dispatch_mode: ValidatorDispatchMode | str | None = None,
) -> dict[str, Any]:
    """Build ADR-0041 dry-run dispatch evidence for runtime intelligence projection."""
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
    execution_plan = build_validator_execution_plan(selection_result)
    resolved_mode, mode_warnings = resolve_validator_dispatch_mode(explicit_mode=dispatch_mode)
    payload = build_validator_dispatch_report(
        execution_plan,
        mode=resolved_mode,
        feature_flag_enabled=resolved_mode is ValidatorDispatchMode.PLAN_ENFORCED,
    ).to_runtime_projection()["validator_dispatch_report"]
    warnings = [
        *(
            payload.get("warnings")
            if isinstance(payload.get("warnings"), list)
            else []
        ),
        *mode_warnings,
        *derivation_warnings,
    ]
    payload["warnings"] = [str(warning) for warning in warnings if str(warning).strip()]
    return _json_safe(payload)


def adr0041_validator_registry_for_turn_class(turn_class_key: str) -> dict[str, Any]:
    """Return semantic validator callables scoped to one ADR-0041 turn class."""
    key = str(turn_class_key or "").strip()
    if key == TURN_CLASS_OPENING_SCENE:
        return dict(build_opening_enforced_semantic_validator_registry())
    if key == TURN_CLASS_NORMAL_PLAYER_TURN:
        return dict(build_player_turn_enforced_semantic_validator_registry())
    if key == TURN_CLASS_NPC_CONFLICT_TURN:
        return dict(build_npc_conflict_enforced_semantic_validator_registry())
    if key == TURN_CLASS_RECOVERY_TURN:
        return dict(build_recovery_turn_enforced_semantic_validator_registry())
    if key == TURN_CLASS_SYSTEM_TRANSITION:
        return dict(build_system_transition_enforced_semantic_validator_registry())
    if key == TURN_CLASS_DEGRADED_OR_FALLBACK_TURN:
        return dict(build_degraded_or_fallback_enforced_semantic_validator_registry())
    return {}


def classify_adr0041_validation_authority_drift(
    *,
    validator_dispatch_report: dict[str, Any],
    validation_seam_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    """Classify disagreement between ``run_validation_seam`` and ADR-0041 local enforcement."""
    would_run_raw = list(validator_dispatch_report.get("validators_would_run") or [])
    would_run: list[str] = []
    for item in would_run_raw:
        text = str(item or "").strip()
        if not text:
            continue
        would_run.append(validate_semantic_capability_name(text))
    would_run_set = frozenset(would_run)

    unavailable_raw = list(validator_dispatch_report.get("validators_unavailable") or [])
    unavailable: set[str] = set()
    for item in unavailable_raw:
        text = str(item or "").strip()
        if not text:
            continue
        unavailable.add(validate_semantic_capability_name(text))

    seam = validation_seam_summary if isinstance(validation_seam_summary, dict) else {}
    seam_ok = str(seam.get("status") or "").strip().lower() == "approved"

    entries = validator_dispatch_report.get("entries") or []
    evidences: list[dict[str, Any]] = []
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        if not ent.get("actually_executed") or ent.get("unavailable"):
            continue
        ev = ent.get("local_execution_evidence")
        if isinstance(ev, dict):
            evidences.append(ev)

    planned_unavailable = would_run_set & unavailable
    notes: list[str] = []
    classification: str

    if would_run_set and planned_unavailable == would_run_set:
        classification = ADR0041_DRIFT_MISSING_CONTEXT
        notes.append("all_planned_enforced_validators_unavailable")
    elif planned_unavailable and planned_unavailable != would_run_set:
        classification = ADR0041_DRIFT_UNAVAILABLE_VALIDATOR
        notes.append("partial_planned_enforced_unavailable")
    elif not evidences:
        classification = ADR0041_DRIFT_ALIGNED
        notes.append("no_local_execution_evidence_rows")
    else:
        any_fail = any(not bool(e.get("passed")) for e in evidences)
        all_pass = all(bool(e.get("passed")) for e in evidences)

        if seam_ok and any_fail:
            classification = ADR0041_DRIFT_ADR_STRICTER
        elif not seam_ok and all_pass:
            classification = ADR0041_DRIFT_SEAM_STRICTER
        elif not seam_ok and any_fail:
            classification = ADR0041_DRIFT_CONFLICTING_RESULT
            notes.append("seam_rejected_and_adr_local_failures_present")
        else:
            classification = ADR0041_DRIFT_ALIGNED

    return {
        "classification": classification,
        "notes": notes,
        "validation_seam_status": seam.get("status"),
        "validation_seam_reason": seam.get("reason"),
        "planned_enforced_count": len(would_run_set),
        "unavailable_planned_count": len(planned_unavailable),
        "executed_evidence_count": len(evidences),
    }


def build_adr0041_validation_authority_preview(
    *,
    validator_dispatch_report: dict[str, Any],
    validation_seam_summary: dict[str, Any] | None,
    selected_turn_class: str,
) -> dict[str, Any]:
    """Structured preview: ADR-0041 routing/evidence vs seam (never commit/readiness authority)."""
    seam_dict = validation_seam_summary if isinstance(validation_seam_summary, dict) else {}
    drift = classify_adr0041_validation_authority_drift(
        validator_dispatch_report=validator_dispatch_report,
        validation_seam_summary=seam_dict,
    )
    executed_ids = list(validator_dispatch_report.get("actually_executed") or [])
    unavailable = list(validator_dispatch_report.get("validators_unavailable") or [])
    would_run = list(validator_dispatch_report.get("validators_would_run") or [])

    entries = validator_dispatch_report.get("entries") or []
    evidences: list[dict[str, Any]] = []
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        if not ent.get("actually_executed") or ent.get("unavailable"):
            continue
        ev = ent.get("local_execution_evidence")
        if isinstance(ev, dict):
            evidences.append(ev)
    failed_ids = sorted({str(e.get("validator_id") or "") for e in evidences if not e.get("passed")} - {""})
    passed_ids = sorted({str(e.get("validator_id") or "") for e in evidences if e.get("passed")} - {""})

    return _json_safe(
        {
            "schema_version": ADR0041_VALIDATION_AUTHORITY_PREVIEW_SCHEMA_VERSION,
            "authority_mode": "plan_enforced_local_routing_preview",
            "selected_turn_class": str(selected_turn_class or "").strip(),
            "enforced_validators_planned": would_run,
            "executed_validators": executed_ids,
            "unavailable_validators": unavailable,
            "pass_fail_summary": {
                "all_executed_passed": bool(evidences) and not failed_ids,
                "failed_validator_ids": failed_ids,
                "passed_validator_ids": passed_ids,
            },
            "drift_vs_validation_seam": drift,
            "canonical_commitment_seam": "ai_stack.story_runtime.turn.goc_turn_seams.run_validation_seam",
            "affects_commit": False,
            "affects_readiness": False,
            "proof_level": "local_only",
            "live_or_staging_evidence": False,
        }
    )


def resolve_adr0041_scoped_co_authority_enabled(
    *,
    env_value: str | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Resolve the explicit ADR-0041 scoped co-authority feature flag.

    Default ``False`` (fail closed): no co-authority decision payload is emitted.
    Enabling this flag still does not mutate validation, readiness, or commit state.
    """
    warnings: list[str] = []
    raw = env_value if env_value is not None else os.environ.get(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV)
    text = str(raw or "").strip().lower()
    if text in {"", "0", "false", "no", "off"}:
        return False, tuple(warnings)
    if text in {"1", "true", "yes", "on"}:
        return True, tuple(warnings)
    warnings.append(
        f"Unsupported {ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV}={raw!r}; "
        "ADR-0041 scoped co-authority decision disabled."
    )
    return False, tuple(warnings)


def resolve_adr0041_readiness_co_authority_preview_enabled(
    *,
    env_value: str | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Resolve explicit readiness co-authority preview flag.

    Default ``False`` (fail closed): no readiness policy preview payload is emitted.
    """
    warnings: list[str] = []
    raw = (
        env_value
        if env_value is not None
        else os.environ.get(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV)
    )
    text = str(raw or "").strip().lower()
    if text in {"", "0", "false", "no", "off"}:
        return False, tuple(warnings)
    if text in {"1", "true", "yes", "on"}:
        return True, tuple(warnings)
    warnings.append(
        f"Unsupported {ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV}={raw!r}; "
        "ADR-0041 readiness co-authority preview disabled."
    )
    return False, tuple(warnings)


def resolve_adr0041_scoped_readiness_enforcement_enabled(
    *,
    env_value: str | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Resolve explicit scoped readiness enforcement pilot flag (fail closed)."""
    warnings: list[str] = []
    raw = (
        env_value
        if env_value is not None
        else os.environ.get(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV)
    )
    text = str(raw or "").strip().lower()
    if text in {"", "0", "false", "no", "off"}:
        return False, tuple(warnings)
    if text in {"1", "true", "yes", "on"}:
        return True, tuple(warnings)
    warnings.append(
        f"Unsupported {ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV}={raw!r}; "
        "ADR-0041 scoped readiness enforcement disabled."
    )
    return False, tuple(warnings)


def resolve_adr0041_scoped_readiness_aggregation_enabled(
    *,
    env_value: str | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Resolve scoped readiness aggregation pilot flag (fail closed)."""
    warnings: list[str] = []
    raw = (
        env_value
        if env_value is not None
        else os.environ.get(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV)
    )
    text = str(raw or "").strip().lower()
    if text in {"", "0", "false", "no", "off"}:
        return False, tuple(warnings)
    if text in {"1", "true", "yes", "on"}:
        return True, tuple(warnings)
    warnings.append(
        f"Unsupported {ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV}={raw!r}; "
        "ADR-0041 scoped readiness aggregation disabled."
    )
    return False, tuple(warnings)


def resolve_adr0041_runtime_readiness_consumer_enabled(
    *,
    env_value: str | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Resolve ADR-0041 runtime readiness consumer flag (fail closed).

    When disabled, final session readiness fields must match legacy/seam evaluation
    with no silent ADR-0041 overlay.
    """
    warnings: list[str] = []
    raw = (
        env_value
        if env_value is not None
        else os.environ.get(ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV)
    )
    text = str(raw or "").strip().lower()
    if text in {"", "0", "false", "no", "off"}:
        return False, tuple(warnings)
    if text in {"1", "true", "yes", "on"}:
        return True, tuple(warnings)
    warnings.append(
        f"Unsupported {ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV}={raw!r}; "
        "ADR-0041 runtime readiness consumer disabled."
    )
    return False, tuple(warnings)


def _build_adr0041_plan_enforced_runtime_projection_dispatch(
    *,
    capability_context: dict[str, Any],
    graph_bundle: dict[str, Any],
    dispatch_mode_warnings: tuple[str, ...],
) -> dict[str, Any]:
    """Plan-enforced dispatch report for runtime_intelligence (graph runtime path only)."""
    selection_for_sidecar, sidecar_deriv_warnings = _select_semantic_capabilities_from_runtime_context(
        **capability_context
    )
    turn_class_key, turn_class_hints = _infer_adr0041_turn_class_from_situation(
        selection_for_sidecar.situation
    )
    execution_plan_sidecar = build_validator_execution_plan(selection_for_sidecar)
    execution_plan_sidecar = prepend_goc_seam_mirror_plan_entries(
        execution_plan_sidecar,
        seam_mirror_validator_ids=goc_seam_mirror_plan_validator_ids_for_turn_class(turn_class_key),
    )
    registry_sidecar = adr0041_validator_registry_for_turn_class(turn_class_key)
    dispatch_ctx_raw = graph_bundle.get("dispatch_context")
    dispatch_ctx: dict[str, Any] = (
        dict(dispatch_ctx_raw) if isinstance(dispatch_ctx_raw, dict) else {}
    )

    report_obj = build_validator_dispatch_report(
        execution_plan_sidecar,
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=registry_sidecar,
        dispatch_context=dispatch_ctx,
        feature_flag_enabled=True,
    )
    semantic_validator_dispatch_report = report_obj.to_runtime_projection()["validator_dispatch_report"]
    seam_summary = graph_bundle.get("validation_seam_summary")
    visibility: dict[str, Any] = {
        "canonical_commitment_seam": "ai_stack.story_runtime.turn.goc_turn_seams.run_validation_seam",
        "adr0041_runtime_sidecar": (
            "ai_stack.runtime_aspect_ledger / ADR-0041 plan_enforced local validators"
        ),
        "relationship_note": (
            "run_validation_seam remains the canonical commitment seam for validation_outcome; "
            "ADR-0041 performs plan-enforced local validator routing by turn class; "
            "see adr0041_authority_preview / validation_authority_preview (projection) for drift classification."
        ),
        "validation_seam_status": seam_summary.get("status") if isinstance(seam_summary, dict) else None,
        "validation_seam_reason": seam_summary.get("reason") if isinstance(seam_summary, dict) else None,
        "plan_enforced_actually_executed": list(
            semantic_validator_dispatch_report.get("actually_executed") or []
        ),
        "plan_enforced_validators_unavailable": list(
            semantic_validator_dispatch_report.get("validators_unavailable") or []
        ),
        "selected_turn_class": turn_class_key,
    }
    semantic_validator_dispatch_report["run_validation_seam_outcome_echo"] = (
        _json_safe(seam_summary) if isinstance(seam_summary, dict) else {}
    )
    semantic_validator_dispatch_report["adr0041_selected_turn_class"] = turn_class_key
    semantic_validator_dispatch_report["adr0041_turn_class_hints"] = _json_safe(turn_class_hints)
    semantic_validator_dispatch_report["seam_vs_adr0041_sidecar_drift_visibility"] = _json_safe(
        visibility
    )
    preview = build_adr0041_validation_authority_preview(
        validator_dispatch_report=semantic_validator_dispatch_report,
        validation_seam_summary=seam_summary if isinstance(seam_summary, dict) else {},
        selected_turn_class=turn_class_key,
    )
    semantic_validator_dispatch_report["adr0041_authority_preview"] = preview
    bridge = build_validation_authority_bridge(
        validation_seam_summary=seam_summary if isinstance(seam_summary, dict) else {},
        validator_dispatch_report=semantic_validator_dispatch_report,
        validation_authority_preview=preview,
        selected_turn_class=turn_class_key,
    )
    semantic_validator_dispatch_report["validation_authority_bridge"] = _json_safe(bridge)
    co_authority_enabled, co_authority_warnings = resolve_adr0041_scoped_co_authority_enabled()
    co_authority_decision: dict[str, Any] | None = None
    if co_authority_enabled:
        co_authority_decision = build_validation_co_authority_decision(
            validation_authority_bridge=bridge,
            validator_dispatch_report=semantic_validator_dispatch_report,
            selected_turn_class=turn_class_key,
            feature_flag_name=ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV,
            feature_flag_enabled=True,
        )
        if isinstance(co_authority_decision, dict):
            semantic_validator_dispatch_report["validation_co_authority_decision"] = _json_safe(
                co_authority_decision
            )
    readiness_preview_enabled, readiness_preview_warnings = (
        resolve_adr0041_readiness_co_authority_preview_enabled()
    )
    if readiness_preview_enabled:
        readiness_preview = build_readiness_co_authority_preview(
            validation_authority_bridge=bridge,
            validator_dispatch_report=semantic_validator_dispatch_report,
            selected_turn_class=turn_class_key,
            validation_co_authority_decision=co_authority_decision,
            feature_flag_name=ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV,
            feature_flag_enabled=True,
        )
        semantic_validator_dispatch_report["readiness_co_authority_preview"] = _json_safe(
            readiness_preview
        )
    enforcement_enabled, enforcement_warnings = (
        resolve_adr0041_scoped_readiness_enforcement_enabled()
    )
    if enforcement_enabled:
        readiness_enforcement = build_readiness_co_authority_enforcement(
            readiness_co_authority_preview=(
                semantic_validator_dispatch_report.get("readiness_co_authority_preview")
                if isinstance(semantic_validator_dispatch_report.get("readiness_co_authority_preview"), dict)
                else None
            ),
            validator_dispatch_report=semantic_validator_dispatch_report,
            selected_turn_class=turn_class_key,
            feature_flag_name=ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV,
            feature_flag_enabled=True,
        )
        semantic_validator_dispatch_report["readiness_co_authority_enforcement"] = _json_safe(
            readiness_enforcement
        )
    aggregation_enabled, aggregation_warnings = (
        resolve_adr0041_scoped_readiness_aggregation_enabled()
    )
    prereq_aggregation = (
        co_authority_enabled
        and readiness_preview_enabled
        and enforcement_enabled
    )
    policy_for_agg = semantic_validator_dispatch_report.get("readiness_co_authority_enforcement")
    if aggregation_enabled:
        if prereq_aggregation and isinstance(policy_for_agg, dict):
            semantic_validator_dispatch_report["readiness_aggregation_decision"] = _json_safe(
                build_readiness_aggregation_decision(
                    validation_seam_summary=seam_summary if isinstance(seam_summary, dict) else {},
                    readiness_policy_input=policy_for_agg,
                )
            )
        elif not prereq_aggregation:
            merged_pre = semantic_validator_dispatch_report.get("warnings")
            merged_list = list(merged_pre) if isinstance(merged_pre, list) else []
            msg = (
                "ADR-0041 scoped readiness aggregation skipped: prerequisite flags "
                "(scoped co-authority, readiness preview, enforcement) not all enabled."
            )
            if msg not in merged_list:
                merged_list.append(msg)
            semantic_validator_dispatch_report["warnings"] = merged_list
        else:
            merged_pre = semantic_validator_dispatch_report.get("warnings")
            merged_list = list(merged_pre) if isinstance(merged_pre, list) else []
            msg = (
                "ADR-0041 scoped readiness aggregation skipped: readiness policy input missing "
                "(enable scoped readiness enforcement to emit enforcement payload)."
            )
            if msg not in merged_list:
                merged_list.append(msg)
            semantic_validator_dispatch_report["warnings"] = merged_list
    extra_warnings = [
        *dispatch_mode_warnings,
        *sidecar_deriv_warnings,
        *co_authority_warnings,
        *readiness_preview_warnings,
        *enforcement_warnings,
        *aggregation_warnings,
    ]
    existing_warnings = semantic_validator_dispatch_report.get("warnings")
    merged: list[str] = list(existing_warnings) if isinstance(existing_warnings, list) else []
    for w in extra_warnings:
        t = str(w).strip()
        if t and t not in merged:
            merged.append(t)
    semantic_validator_dispatch_report["warnings"] = merged
    return _json_safe(semantic_validator_dispatch_report)


def build_adr0041_validator_dispatch_harness_report(
    *,
    harness_allow_plan_enforced_local_dispatch: bool = False,
    validator_registry: ValidatorRegistry | None = None,
    dispatch_context: dict[str, Any] | None = None,
    dispatch_mode: ValidatorDispatchMode | str | None = None,
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
    """Explicit ADR-0041 harness for plan-enforced local validator dispatch (tests only).

    When ``harness_allow_plan_enforced_local_dispatch`` is false, behavior matches
    ``build_semantic_validator_dispatch_report_projection`` (registry ignored).
    When true, ``plan_enforced`` runs registered validators only if an explicit
    registry mapping is supplied; missing registry fails closed to ``dry_run``.
    Production ledger normalization continues to use dry-run projection only.
    """
    cap_kw: dict[str, Any] = {
        "turn_kind": turn_kind,
        "turn_number": turn_number,
        "raw_player_input": raw_player_input,
        "input_kind": input_kind,
        "active_actor": active_actor,
        "npc_decision_required": npc_decision_required,
        "action_resolution_required": action_resolution_required,
        "visible_projection_required": visible_projection_required,
        "canonical_scene_seed": canonical_scene_seed,
        "non_lexical_input_present": non_lexical_input_present,
        "knowledge_gap_present": knowledge_gap_present,
        "world_state_change_requested": world_state_change_requested,
    }

    if not harness_allow_plan_enforced_local_dispatch:
        return build_semantic_validator_dispatch_report_projection(
            **cap_kw,
            dispatch_mode=dispatch_mode,
        )

    selection_result, derivation_warnings = _select_semantic_capabilities_from_runtime_context(**cap_kw)
    execution_plan = build_validator_execution_plan(selection_result)
    resolved_mode, mode_warnings = resolve_validator_dispatch_mode(explicit_mode=dispatch_mode)
    harness_warnings: list[str] = []

    if resolved_mode is ValidatorDispatchMode.PLAN_ENFORCED and validator_registry is None:
        resolved_mode = ValidatorDispatchMode.DRY_RUN
        harness_warnings.append(ADR0041_HARNESS_PLAN_ENFORCED_REQUIRES_REGISTRY_WARNING)

    registry_arg: ValidatorRegistry = validator_registry if validator_registry is not None else {}

    report_obj = build_validator_dispatch_report(
        execution_plan,
        mode=resolved_mode,
        validator_registry=registry_arg,
        dispatch_context=dispatch_context or {},
        feature_flag_enabled=(resolved_mode is ValidatorDispatchMode.PLAN_ENFORCED),
    )
    payload = report_obj.to_runtime_projection()["validator_dispatch_report"]
    warnings = [
        *(payload.get("warnings") if isinstance(payload.get("warnings"), list) else []),
        *mode_warnings,
        *derivation_warnings,
        *harness_warnings,
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


def resolve_adr0041_plan_projection_enabled(
    *,
    env_value: str | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Resolve optional ADR-0041 plan-aware sibling projection under runtime_intelligence_projection.

    Default ``False`` (fail closed): sibling omitted; validator_dispatch_report unchanged.
    Explicit truthy env enables sibling-only evidence (still projection-only; no execution).
    """
    warnings: list[str] = []
    raw = env_value if env_value is not None else os.environ.get(ADR0041_PLAN_PROJECTION_ENABLED_ENV)
    text = str(raw or "").strip().lower()
    if text in {"", "0", "false", "no", "off"}:
        return False, tuple(warnings)
    if text in {"1", "true", "yes", "on"}:
        return True, tuple(warnings)
    warnings.append(
        f"Unsupported {ADR0041_PLAN_PROJECTION_ENABLED_ENV}={raw!r}; "
        "ADR-0041 plan projection sibling disabled."
    )
    return False, tuple(warnings)


def _infer_adr0041_turn_class_from_situation(situation: TurnSituation) -> tuple[str, dict[str, Any]]:
    """Map selector TurnSituation to ADR-0041 drift-guard turn class labels."""
    tk = situation.turn_kind
    tk_val = tk.value if isinstance(tk, TurnKind) else str(tk)
    hints: dict[str, Any] = {
        "situation_turn_kind": tk_val,
        "npc_decision_required": bool(situation.npc_decision_required),
        "player_input_present": bool(situation.player_input_present),
        "last_turn_quality": (
            situation.last_turn_quality.value
            if isinstance(situation.last_turn_quality, LastTurnQuality)
            else str(situation.last_turn_quality)
        ),
    }
    if tk is TurnKind.OPENING:
        return TURN_CLASS_OPENING_SCENE, hints
    if tk is TurnKind.NPC_TURN and situation.npc_decision_required:
        return TURN_CLASS_NPC_CONFLICT_TURN, hints
    if tk is TurnKind.PLAYER_INPUT:
        return TURN_CLASS_NORMAL_PLAYER_TURN, hints
    if tk is TurnKind.RECOVERY:
        if situation.last_turn_quality is LastTurnQuality.FALLBACK:
            return TURN_CLASS_DEGRADED_OR_FALLBACK_TURN, hints
        return TURN_CLASS_RECOVERY_TURN, hints
    if tk is TurnKind.SYSTEM_TRANSITION:
        return TURN_CLASS_SYSTEM_TRANSITION, hints
    if situation.last_turn_quality is LastTurnQuality.FALLBACK:
        return TURN_CLASS_DEGRADED_OR_FALLBACK_TURN, hints
    return TURN_CLASS_SYSTEM_TRANSITION, hints


def _build_adr0041_plan_projection_sibling(
    *,
    selection_result: CapabilitySelectionResult,
    execution_plan: ValidatorExecutionPlan,
    dispatch_report: dict[str, Any],
    flag_warnings: tuple[str, ...],
    derivation_warnings: tuple[str, ...],
) -> dict[str, Any]:
    """Sibling projection-only envelope (never executes validators or seams)."""
    situation = selection_result.situation
    turn_class_key, turn_class_hints = _infer_adr0041_turn_class_from_situation(situation)

    avail = build_available_semantic_validator_registry()
    avail_keys = frozenset(avail.keys())
    inventory_safe = {
        row.validator_id: row.safe_for_local_plan_enforced for row in VALIDATOR_REGISTRY_INVENTORY
    }

    planned_validators = list(execution_plan.validators_to_run)
    planned_observers = list(execution_plan.observer_diagnostics)

    would_execute_local_sorted = sorted(vid for vid in planned_validators if vid in avail_keys)
    blocked_missing_registry_sorted = sorted(vid for vid in planned_validators if vid not in avail_keys)
    inventory_marked_unsafe = sorted(
        vid for vid in planned_validators if vid in inventory_safe and not inventory_safe[vid]
    )

    registry_availability: dict[str, dict[str, Any]] = {}
    for vid in sorted(set(planned_validators) | set(planned_observers)):
        registry_availability[vid] = {
            "adapter_registered_for_local_dispatch": vid in avail_keys,
            "inventory_marks_safe_for_local_plan_enforced": bool(inventory_safe.get(vid)),
        }

    consciously_not_executed = {
        "validators_skipped_by_plan_budget_or_exclusion": list(dispatch_report.get("validators_would_skip") or []),
        "judges_disallowed_by_plan": list(dispatch_report.get("judges_would_be_disallowed") or []),
        "observer_diagnostics_planned_only_non_blocking": list(dispatch_report.get("diagnostics_would_run") or []),
        "note": (
            "Dry-run projection does not invoke validators or judges; skipped/disallowed rows reflect "
            "plan semantics only."
        ),
    }

    drift = {
        "production_validation_seam_symbol": "ai_stack.story_runtime.turn.goc_turn_seams.run_validation_seam",
        "adr0041_dispatch_projection_symbol": (
            "ai_stack.runtime_aspect_ledger.build_semantic_validator_dispatch_report_projection"
        ),
        "relationship_note": (
            "run_validation_seam enforces GoC proposal seams (actor lane, transcript shell caps, "
            "hard-forbidden runtime, opening coverage, dramatic-effect gate). ADR-0041 plan projection "
            "enumerates semantic capability-linked validator contracts for local planning only; it does not "
            "replace or reorder run_validation_seam."
        ),
        "validation_seam_contract_surfaces": [
            "actor_lane_human_ai_boundary",
            "npc_lane_transcript_shell_blob_cap",
            "authoritative_action_resolution_surface_waiver",
            "non_goc_module_vertical_slice_waiver",
            "generation_success_gate",
            "proposal_effect_wellformedness_gate",
            "hard_forbidden_runtime_detection",
            "opening_event_coverage_gate",
            "dramatic_effect_gate",
        ],
        "adr0041_planned_local_validator_contract_ids": planned_validators,
    }

    dr_warnings_list = dispatch_report.get("warnings")
    dispatch_warnings: tuple[str, ...] = ()
    if isinstance(dr_warnings_list, list):
        dispatch_warnings = tuple(str(item).strip() for item in dr_warnings_list if str(item).strip())

    warn_seen: list[str] = []
    for bucket in (
        flag_warnings,
        derivation_warnings,
        dispatch_warnings,
        execution_plan.warnings,
        selection_result.warnings,
    ):
        for w in bucket:
            text = str(w).strip()
            if text and text not in warn_seen:
                warn_seen.append(text)

    payload: dict[str, Any] = {
        "schema_version": ADR0041_PLAN_PROJECTION_SCHEMA_VERSION,
        "adr0041_plan_projection_enabled": True,
        "proof_level": "local_only",
        "evidence_scope": dispatch_report.get("evidence_scope"),
        "live_or_staging_evidence": False,
        "execution_changed": False,
        "actually_executed": [],
        "commit_gate_changed": False,
        "readiness_gate_changed": False,
        "judge_execution_changed": False,
        "selected_turn_class": turn_class_key,
        "turn_class_hints": turn_class_hints,
        "capabilities": {
            "enforced": list(selection_result.enforced),
            "observed": list(selection_result.observed),
            "excluded": list(selection_result.excluded),
            "judged": list(selection_result.judged),
        },
        "planned_local_validator_ids": planned_validators,
        "planned_observer_diagnostic_ids": planned_observers,
        "registry_availability_by_id": registry_availability,
        "would_execute_local_validators_if_plan_enforced_with_inventory_adapters": would_execute_local_sorted,
        "validators_unavailable_per_dispatch_report": list(dispatch_report.get("validators_unavailable") or []),
        "unavailable_local_adapters_for_planned_validators": blocked_missing_registry_sorted,
        "blocked_by_missing_registry_or_context": blocked_missing_registry_sorted,
        "inventory_marks_unsafe_for_local_plan_enforced": inventory_marked_unsafe,
        "consciously_not_executed": consciously_not_executed,
        "validator_dispatch_report_echo": {
            "mode": dispatch_report.get("mode"),
            "execution_changed": dispatch_report.get("execution_changed"),
            "actually_executed": dispatch_report.get("actually_executed"),
            "feature_flag_enabled": dispatch_report.get("feature_flag_enabled"),
        },
        "seam_vs_plan_projection_drift_visibility": drift,
        "warnings": warn_seen,
    }
    return _json_safe(payload)


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
    broad_nlu_rec = (
        aspects.get(ASPECT_BROAD_NLU_LISTENING)
        if isinstance(aspects.get(ASPECT_BROAD_NLU_LISTENING), dict)
        else {}
    )
    action_rec = (
        aspects.get(ASPECT_ACTION_RESOLUTION)
        if isinstance(aspects.get(ASPECT_ACTION_RESOLUTION), dict)
        else {}
    )
    conversational_memory_rec = (
        aspects.get(ASPECT_CONVERSATIONAL_MEMORY)
        if isinstance(aspects.get(ASPECT_CONVERSATIONAL_MEMORY), dict)
        else {}
    )
    prompt_authority_rec = (
        aspects.get(ASPECT_PROMPT_AUTHORITY)
        if isinstance(aspects.get(ASPECT_PROMPT_AUTHORITY), dict)
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
    symbolic_object_rec = (
        aspects.get(ASPECT_SYMBOLIC_OBJECT_RESONANCE)
        if isinstance(aspects.get(ASPECT_SYMBOLIC_OBJECT_RESONANCE), dict)
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
    narrative_momentum_rec = (
        aspects.get(ASPECT_NARRATIVE_MOMENTUM)
        if isinstance(aspects.get(ASPECT_NARRATIVE_MOMENTUM), dict)
        else {}
    )
    voice_rec = (
        aspects.get(ASPECT_VOICE_CONSISTENCY)
        if isinstance(aspects.get(ASPECT_VOICE_CONSISTENCY), dict)
        else {}
    )
    tonal_rec = (
        aspects.get(ASPECT_TONAL_CONSISTENCY)
        if isinstance(aspects.get(ASPECT_TONAL_CONSISTENCY), dict)
        else {}
    )
    genre_awareness_rec = (
        aspects.get(ASPECT_GENRE_AWARENESS)
        if isinstance(aspects.get(ASPECT_GENRE_AWARENESS), dict)
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
    broad_nlu_expected = _record_block(broad_nlu_rec, "expected")
    broad_nlu_selected = _record_block(broad_nlu_rec, "selected")
    broad_nlu_actual = _record_block(broad_nlu_rec, "actual")
    action_actual = _record_block(action_rec, "actual")
    conversational_memory_expected = _record_block(conversational_memory_rec, "expected")
    conversational_memory_selected = _record_block(conversational_memory_rec, "selected")
    conversational_memory_actual = _record_block(conversational_memory_rec, "actual")
    prompt_authority_expected = _record_block(prompt_authority_rec, "expected")
    prompt_authority_selected = _record_block(prompt_authority_rec, "selected")
    prompt_authority_actual = _record_block(prompt_authority_rec, "actual")
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
    symbolic_object_expected = _record_block(symbolic_object_rec, "expected")
    symbolic_object_selected = _record_block(symbolic_object_rec, "selected")
    symbolic_object_actual = _record_block(symbolic_object_rec, "actual")
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
    narrative_momentum_expected = _record_block(narrative_momentum_rec, "expected")
    narrative_momentum_selected = _record_block(narrative_momentum_rec, "selected")
    narrative_momentum_actual = _record_block(narrative_momentum_rec, "actual")
    voice_expected = _record_block(voice_rec, "expected")
    tonal_expected = _record_block(tonal_rec, "expected")
    tonal_selected = _record_block(tonal_rec, "selected")
    tonal_actual = _record_block(tonal_rec, "actual")
    genre_awareness_expected = _record_block(genre_awareness_rec, "expected")
    genre_awareness_selected = _record_block(genre_awareness_rec, "selected")
    genre_awareness_actual = _record_block(genre_awareness_rec, "actual")
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
    graph_bundle = src.get(ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY)
    graph_bundle = graph_bundle if isinstance(graph_bundle, dict) else None
    resolved_dispatch_mode, runtime_dispatch_mode_warnings = resolve_validator_dispatch_mode()
    if (
        graph_bundle is not None
        and resolved_dispatch_mode is ValidatorDispatchMode.PLAN_ENFORCED
    ):
        semantic_validator_dispatch_report = _build_adr0041_plan_enforced_runtime_projection_dispatch(
            capability_context=capability_context,
            graph_bundle=graph_bundle,
            dispatch_mode_warnings=runtime_dispatch_mode_warnings,
        )
    else:
        semantic_validator_dispatch_report = build_semantic_validator_dispatch_report_projection(
            **capability_context,
            dispatch_mode=ValidatorDispatchMode.DRY_RUN,
        )

    projection_payload = {
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
            "broad_nlu_listening": {
                "schema_version": broad_nlu_expected.get("schema_version"),
                "primary_discourse_act": broad_nlu_selected.get("primary_discourse_act"),
                "player_input_kind": broad_nlu_actual.get("player_input_kind"),
                "confidence": broad_nlu_actual.get("confidence"),
                "ambiguity_codes": broad_nlu_actual.get("ambiguity_codes") or [],
                "repair_prompt_recommended": bool(
                    broad_nlu_actual.get("repair_prompt_recommended")
                ),
                "response_expectation": broad_nlu_actual.get("response_expectation"),
                "target_actor_refs": broad_nlu_selected.get("target_actor_refs") or [],
                "object_refs": broad_nlu_selected.get("object_refs") or [],
                "source_refs": broad_nlu_selected.get("source_refs") or [],
                "raw_player_input_included": bool(
                    broad_nlu_actual.get("raw_player_input_included")
                ),
                "contract_pass": broad_nlu_actual.get("contract_pass"),
                "failure_reason": broad_nlu_rec.get("failure_reason")
                or (
                    _record_reasons(broad_nlu_rec)[0]
                    if _record_reasons(broad_nlu_rec)
                    else None
                ),
                "status": broad_nlu_rec.get("status"),
            },
            "conversational_memory": {
                "schema_version": conversational_memory_expected.get("schema_version"),
                "selected_tiers": conversational_memory_selected.get("selected_tiers") or [],
                "selected_memory_ref_ids": conversational_memory_selected.get(
                    "selected_memory_ref_ids"
                )
                or [],
                "source_refs": conversational_memory_selected.get("source_refs") or [],
                "memory_present": bool(conversational_memory_actual.get("memory_present")),
                "bounded": bool(conversational_memory_actual.get("bounded")),
                "context_line_count": int(
                    conversational_memory_actual.get("context_line_count") or 0
                ),
                "raw_player_input_included": bool(
                    conversational_memory_actual.get("raw_player_input_included")
                ),
                "raw_prompt_included": bool(
                    conversational_memory_actual.get("raw_prompt_included")
                ),
                "contract_pass": conversational_memory_actual.get("contract_pass"),
                "failure_reason": conversational_memory_rec.get("failure_reason")
                or (
                    _record_reasons(conversational_memory_rec)[0]
                    if _record_reasons(conversational_memory_rec)
                    else None
                ),
                "status": conversational_memory_rec.get("status"),
            },
            "prompt_authority": {
                "schema_version": prompt_authority_expected.get("schema_version"),
                "authoritative_sections": prompt_authority_selected.get(
                    "authoritative_sections"
                )
                or [],
                "source_refs": prompt_authority_selected.get("source_refs") or [],
                "selected_capabilities": prompt_authority_selected.get(
                    "selected_capabilities"
                )
                or [],
                "selected_memory_ref_ids": prompt_authority_selected.get(
                    "selected_memory_ref_ids"
                )
                or [],
                "authority_mode": prompt_authority_actual.get("authority_mode"),
                "prompt_authority_applied_to_packet": bool(
                    prompt_authority_actual.get("prompt_authority_applied_to_packet")
                ),
                "commit_gate_changed": bool(
                    prompt_authority_actual.get("commit_gate_changed")
                ),
                "readiness_gate_changed": bool(
                    prompt_authority_actual.get("readiness_gate_changed")
                ),
                "validation_outcome_changed": bool(
                    prompt_authority_actual.get("validation_outcome_changed")
                ),
                "contract_pass": prompt_authority_actual.get("contract_pass"),
                "failure_reason": prompt_authority_rec.get("failure_reason")
                or (
                    _record_reasons(prompt_authority_rec)[0]
                    if _record_reasons(prompt_authority_rec)
                    else None
                ),
                "status": prompt_authority_rec.get("status"),
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
            "symbolic_object_resonance": {
                "schema_version": symbolic_object_expected.get("schema_version")
                or symbolic_object_selected.get("schema_version")
                or symbolic_object_actual.get("schema_version"),
                "policy_present": bool(symbolic_object_expected.get("policy_present")),
                "policy_enabled": bool(symbolic_object_expected.get("policy_enabled")),
                "commit_impact": symbolic_object_expected.get("commit_impact"),
                "require_structured_events": bool(
                    symbolic_object_expected.get("require_structured_events")
                ),
                "max_symbols_per_turn": int(
                    symbolic_object_expected.get("max_symbols_per_turn") or 0
                ),
                "allowed_resonance_roles": symbolic_object_expected.get(
                    "allowed_resonance_roles"
                )
                or [],
                "selected_symbol_ids": symbolic_object_selected.get("selected_symbol_ids")
                or (
                    symbolic_object_selected.get("target", {}).get("selected_symbol_ids")
                    if isinstance(symbolic_object_selected.get("target"), dict)
                    else []
                )
                or [],
                "selected_object_ids": symbolic_object_selected.get("selected_object_ids")
                or (
                    symbolic_object_selected.get("target", {}).get("selected_object_ids")
                    if isinstance(symbolic_object_selected.get("target"), dict)
                    else []
                )
                or [],
                "selected_resonance_roles": symbolic_object_selected.get(
                    "selected_resonance_roles"
                )
                or (
                    symbolic_object_selected.get("target", {}).get(
                        "selected_resonance_roles"
                    )
                    if isinstance(symbolic_object_selected.get("target"), dict)
                    else []
                )
                or [],
                "required_source_refs": symbolic_object_selected.get(
                    "required_source_refs"
                )
                or [],
                "structured_events_present": bool(
                    symbolic_object_actual.get("structured_events_present")
                ),
                "event_count": int(symbolic_object_actual.get("event_count") or 0),
                "realized_object_ids": symbolic_object_actual.get("realized_object_ids")
                or [],
                "realized_symbol_ids": symbolic_object_actual.get("realized_symbol_ids")
                or [],
                "realized_resonance_roles": symbolic_object_actual.get(
                    "realized_resonance_roles"
                )
                or [],
                "contract_pass": symbolic_object_actual.get("contract_pass"),
                "failure_codes": symbolic_object_actual.get("failure_codes")
                or _record_reasons(symbolic_object_rec),
                "failure_reason": symbolic_object_rec.get("failure_reason")
                or (
                    _record_reasons(symbolic_object_rec)[0]
                    if _record_reasons(symbolic_object_rec)
                    else None
                ),
                "status": symbolic_object_rec.get("status"),
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
            "validator_dispatch_report": semantic_validator_dispatch_report,
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
            "narrative_momentum": {
                "schema_version": narrative_momentum_expected.get("schema_version")
                or narrative_momentum_selected.get("schema_version")
                or narrative_momentum_actual.get("schema_version"),
                "policy_present": bool(narrative_momentum_expected.get("policy_present")),
                "policy_enabled": bool(narrative_momentum_expected.get("policy_enabled")),
                "commit_impact": narrative_momentum_expected.get("commit_impact"),
                "require_structured_events": bool(
                    narrative_momentum_expected.get("require_structured_events")
                ),
                "target_state": narrative_momentum_selected.get("target_state")
                or (
                    narrative_momentum_selected.get("target", {}).get("target_state")
                    if isinstance(narrative_momentum_selected.get("target"), dict)
                    else None
                )
                or narrative_momentum_actual.get("target_state"),
                "target_score": float(
                    narrative_momentum_selected.get("target_score")
                    or (
                        narrative_momentum_selected.get("target", {}).get("target_score")
                        if isinstance(narrative_momentum_selected.get("target"), dict)
                        else 0.0
                    )
                    or narrative_momentum_actual.get("target_score")
                    or 0.0
                ),
                "current_state": narrative_momentum_actual.get("current_state")
                or (
                    narrative_momentum_selected.get("state", {}).get("current_state")
                    if isinstance(narrative_momentum_selected.get("state"), dict)
                    else None
                ),
                "current_score": float(
                    narrative_momentum_actual.get("current_score")
                    or (
                        narrative_momentum_selected.get("state", {}).get("current_score")
                        if isinstance(narrative_momentum_selected.get("state"), dict)
                        else 0.0
                    )
                    or 0.0
                ),
                "trend": narrative_momentum_actual.get("trend")
                or (
                    narrative_momentum_selected.get("state", {}).get("trend")
                    if isinstance(narrative_momentum_selected.get("state"), dict)
                    else None
                ),
                "velocity": float(narrative_momentum_actual.get("velocity") or 0.0),
                "allowed_next_states": narrative_momentum_selected.get("allowed_next_states")
                or (
                    narrative_momentum_selected.get("target", {}).get("allowed_next_states")
                    if isinstance(narrative_momentum_selected.get("target"), dict)
                    else []
                )
                or [],
                "requires_forward_motion": bool(
                    narrative_momentum_selected.get("requires_forward_motion")
                    or (
                        narrative_momentum_selected.get("target", {}).get(
                            "requires_forward_motion"
                        )
                        if isinstance(narrative_momentum_selected.get("target"), dict)
                        else False
                    )
                ),
                "release_allowed": bool(
                    narrative_momentum_selected.get("release_allowed")
                    or (
                        narrative_momentum_selected.get("target", {}).get("release_allowed")
                        if isinstance(narrative_momentum_selected.get("target"), dict)
                        else False
                    )
                ),
                "transition_allowed": narrative_momentum_actual.get("transition_allowed"),
                "structured_events_present": bool(
                    narrative_momentum_actual.get("structured_events_present")
                ),
                "event_count": int(narrative_momentum_actual.get("event_count") or 0),
                "progress_event_count": int(
                    narrative_momentum_actual.get("progress_event_count") or 0
                ),
                "stall_turn_count": int(
                    narrative_momentum_actual.get("stall_turn_count") or 0
                ),
                "stall_budget_respected": narrative_momentum_actual.get(
                    "stall_budget_respected"
                ),
                "source_refs_valid": narrative_momentum_actual.get("source_refs_valid"),
                "contract_pass": narrative_momentum_actual.get("contract_pass"),
                "failure_codes": narrative_momentum_actual.get("failure_codes")
                or _record_reasons(narrative_momentum_rec),
                "failure_reason": narrative_momentum_rec.get("failure_reason")
                or (
                    _record_reasons(narrative_momentum_rec)[0]
                    if _record_reasons(narrative_momentum_rec)
                    else None
                ),
                "status": narrative_momentum_rec.get("status"),
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
            "tonal_consistency": {
                "schema_version": tonal_expected.get("schema_version")
                or tonal_selected.get("schema_version")
                or tonal_actual.get("schema_version"),
                "policy_present": bool(tonal_expected.get("policy_present")),
                "policy_enabled": bool(tonal_expected.get("policy_enabled")),
                "live_loop_mode": tonal_expected.get("live_loop_mode"),
                "classification_source": tonal_expected.get("classification_source")
                or tonal_actual.get("classification_source"),
                "profile_id": tonal_selected.get("profile_id")
                or _record_nested_value(tonal_selected, "profile_id", "target"),
                "target_dimension_ids": tonal_selected.get("target_dimension_ids")
                or (
                    tonal_selected.get("target", {}).get("target_dimension_ids")
                    if isinstance(tonal_selected.get("target"), dict)
                    else []
                )
                or [],
                "required_dimension_ids": tonal_selected.get("required_dimension_ids")
                or (
                    tonal_selected.get("target", {}).get("required_dimension_ids")
                    if isinstance(tonal_selected.get("target"), dict)
                    else []
                )
                or [],
                "realized_dimension_ids": tonal_actual.get("realized_dimension_ids") or [],
                "missing_required_dimension_ids": tonal_actual.get("missing_required_dimension_ids")
                or [],
                "required_dimension_present_count": int(
                    tonal_actual.get("required_dimension_present_count") or 0
                ),
                "register_label": tonal_actual.get("register_label"),
                "genre_label": tonal_actual.get("genre_label"),
                "dimension_marker_classes": tonal_selected.get("dimension_marker_classes")
                or [],
                "forbidden_marker_classes": tonal_selected.get("forbidden_marker_classes")
                or [],
                "forbidden_marker_hits": tonal_actual.get("forbidden_marker_hits") or {},
                "marker_hit_count": int(tonal_actual.get("marker_hit_count") or 0),
                "structured_classification_present": bool(
                    tonal_actual.get("structured_classification_present")
                ),
                "independent_classifier": tonal_actual.get("independent_classifier"),
                "contract_pass": tonal_actual.get("contract_pass"),
                "failure_codes": tonal_actual.get("failure_codes")
                or _record_reasons(tonal_rec),
                "failure_reason": tonal_rec.get("failure_reason")
                or (_record_reasons(tonal_rec)[0] if _record_reasons(tonal_rec) else None),
                "status": tonal_rec.get("status"),
            },
            "genre_awareness": {
                "schema_version": genre_awareness_expected.get("schema_version")
                or genre_awareness_selected.get("schema_version")
                or genre_awareness_actual.get("schema_version"),
                "policy_present": bool(genre_awareness_expected.get("policy_present")),
                "policy_enabled": bool(genre_awareness_expected.get("policy_enabled")),
                "commit_impact": genre_awareness_expected.get("commit_impact"),
                "require_structured_events": bool(
                    genre_awareness_expected.get("require_structured_events")
                ),
                "genre_profile_id": genre_awareness_selected.get("genre_profile_id")
                or _record_nested_value(genre_awareness_selected, "genre_profile_id", "target"),
                "selected_registers": genre_awareness_selected.get("selected_registers")
                or (
                    genre_awareness_selected.get("target", {}).get("selected_registers")
                    if isinstance(genre_awareness_selected.get("target"), dict)
                    else []
                )
                or [],
                "required_conventions": genre_awareness_selected.get("required_conventions")
                or (
                    genre_awareness_selected.get("target", {}).get("required_conventions")
                    if isinstance(genre_awareness_selected.get("target"), dict)
                    else []
                )
                or [],
                "forbidden_marker_ids": genre_awareness_selected.get("forbidden_marker_ids")
                or (
                    genre_awareness_selected.get("target", {}).get("forbidden_marker_ids")
                    if isinstance(genre_awareness_selected.get("target"), dict)
                    else []
                )
                or [],
                "max_genre_signals_per_turn": int(
                    genre_awareness_expected.get("max_genre_signals_per_turn")
                    or (
                        genre_awareness_selected.get("target", {}).get("max_genre_signals_per_turn")
                        if isinstance(genre_awareness_selected.get("target"), dict)
                        else 0
                    )
                    or 0
                ),
                "structured_events_present": bool(
                    genre_awareness_actual.get("structured_events_present")
                ),
                "event_count": int(genre_awareness_actual.get("event_count") or 0),
                "realized_profile_ids": genre_awareness_actual.get("realized_profile_ids")
                or [],
                "realized_registers": genre_awareness_actual.get("realized_registers") or [],
                "realized_conventions": genre_awareness_actual.get("realized_conventions")
                or [],
                "missing_required_conventions": genre_awareness_actual.get(
                    "missing_required_conventions"
                )
                or [],
                "contract_pass": genre_awareness_actual.get("contract_pass"),
                "failure_codes": genre_awareness_actual.get("failure_codes")
                or _record_reasons(genre_awareness_rec),
                "failure_reason": genre_awareness_rec.get("failure_reason")
                or (
                    _record_reasons(genre_awareness_rec)[0]
                    if _record_reasons(genre_awareness_rec)
                    else None
                ),
                "status": genre_awareness_rec.get("status"),
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
    enabled_plan_projection, fp_warnings = resolve_adr0041_plan_projection_enabled()
    if enabled_plan_projection:
        sibling_sel, sibling_deriv = _select_semantic_capabilities_from_runtime_context(**capability_context)
        sibling_plan = build_validator_execution_plan(sibling_sel)
        projection_payload["adr0041_plan_projection"] = _build_adr0041_plan_projection_sibling(
            selection_result=sibling_sel,
            execution_plan=sibling_plan,
            dispatch_report=semantic_validator_dispatch_report,
            flag_warnings=fp_warnings,
            derivation_warnings=sibling_deriv,
        )
    auth_preview = semantic_validator_dispatch_report.get("adr0041_authority_preview")
    if isinstance(auth_preview, dict):
        projection_payload["validation_authority_preview"] = auth_preview
    bridge_obj = semantic_validator_dispatch_report.get("validation_authority_bridge")
    if isinstance(bridge_obj, dict):
        projection_payload["validation_authority_bridge"] = bridge_obj
        ho = bridge_obj.get("authority_handoff_candidate")
        if isinstance(ho, dict):
            projection_payload["authority_handoff_candidate"] = ho
    co_authority_decision = semantic_validator_dispatch_report.get("validation_co_authority_decision")
    if isinstance(co_authority_decision, dict):
        projection_payload["validation_co_authority_decision"] = co_authority_decision
    readiness_co_authority_preview = semantic_validator_dispatch_report.get(
        "readiness_co_authority_preview"
    )
    if isinstance(readiness_co_authority_preview, dict):
        projection_payload["readiness_co_authority_preview"] = readiness_co_authority_preview
    readiness_co_authority_enforcement = semantic_validator_dispatch_report.get(
        "readiness_co_authority_enforcement"
    )
    if isinstance(readiness_co_authority_enforcement, dict):
        projection_payload["readiness_co_authority_enforcement"] = readiness_co_authority_enforcement
        projection_payload["readiness_policy_input"] = readiness_co_authority_enforcement
    readiness_aggregation_decision = semantic_validator_dispatch_report.get(
        "readiness_aggregation_decision"
    )
    if isinstance(readiness_aggregation_decision, dict):
        projection_payload["readiness_aggregation_decision"] = readiness_aggregation_decision
    return _json_safe(projection_payload)


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
        "narrative_momentum_target_state": selected.get("target_state")
        or target.get("target_state"),
        "narrative_momentum_target_score": selected.get("target_score")
        or target.get("target_score"),
        "narrative_momentum_current_state": actual.get("current_state"),
        "narrative_momentum_current_score": actual.get("current_score"),
        "narrative_momentum_trend": actual.get("trend"),
        "narrative_momentum_velocity": actual.get("velocity"),
        "narrative_momentum_transition_allowed": actual.get("transition_allowed"),
        "narrative_momentum_progress_event_count": actual.get("progress_event_count"),
        "narrative_momentum_stall_budget_respected": actual.get("stall_budget_respected"),
        "narrative_momentum_contract_pass": actual.get("contract_pass"),
        "narrative_momentum_failure_codes": actual.get("failure_codes"),
        "genre_awareness_profile_id": selected.get("genre_profile_id")
        or target.get("genre_profile_id"),
        "genre_awareness_selected_registers": selected.get("selected_registers")
        or target.get("selected_registers"),
        "genre_awareness_required_conventions": selected.get("required_conventions")
        or target.get("required_conventions"),
        "genre_awareness_realized_profile_ids": actual.get("realized_profile_ids"),
        "genre_awareness_realized_registers": actual.get("realized_registers"),
        "genre_awareness_realized_conventions": actual.get("realized_conventions"),
        "genre_awareness_missing_required_conventions": actual.get(
            "missing_required_conventions"
        ),
        "genre_awareness_contract_pass": actual.get("contract_pass"),
        "genre_awareness_failure_codes": actual.get("failure_codes"),
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
