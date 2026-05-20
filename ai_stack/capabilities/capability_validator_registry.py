"""ADR-0041 semantic validator registry inventory and conservative local adapters.

Default registry is empty. Opt-in registries may expose thin wrappers around
existing deterministic validators when dispatch context supplies the required
fields. Unregistered IDs must never false-green as success.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_stack.capabilities.capability_selector import (
    CAP_ACTION_RESOLUTION,
    CAP_BROAD_NLU_LISTENING,
    CAP_CALLBACK_WEB,
    CAP_CONVERSATIONAL_MEMORY,
    CAP_CONSEQUENCE_CASCADE,
    CAP_DRAMATIC_IRONY,
    CAP_ENVIRONMENT_STATE,
    CAP_INFORMATION_DISCLOSURE,
    CAP_LONG_HORIZON_FORECAST,
    CAP_NARRATOR_AUTHORITY,
    CAP_NPC_AGENCY,
    CAP_PLAYER_INTENT_INFERENCE,
    CAP_PROMPT_AUTHORITY,
    CAP_SCENE_ENERGY,
    CAP_SENSORY_CONTEXT,
    CAP_SILENCE_NEGATIVE_SPACE,
    CAP_THEMATIC_TRACKING,
    CAP_VOICE_CONSISTENCY,
    validate_semantic_capability_name,
)
from ai_stack.capabilities.capability_validator_dispatch import LocalValidatorCallable
from ai_stack.capabilities.capability_validator_plan import (
    GOC_SEAM_MIRROR_SUITE_CAPABILITY,
    JUDGE_VALIDATORS,
    LOCAL_VALIDATORS,
    OBSERVER_DIAGNOSTICS,
    ValidatorPlanEntry,
)
from ai_stack.story_runtime.npc_agency.character.character_voice_validation import validate_voice_consistency
from ai_stack.story_runtime.narrative.dramatic_irony_runtime import validate_dramatic_irony_realization
from ai_stack.contracts.environment_state_contracts import evaluate_environment_state_contract
from ai_stack.story_runtime.turn.god_of_carnage_seam_mirror_validator_adapters import (
    ACTOR_LANE_FORBIDDEN_CONTRACT,
    DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT,
    HARD_FORBIDDEN_RUNTIME_CONTRACT,
    MODEL_GENERATION_PRECHECK_CONTRACT,
    NPC_TRANSCRIPT_SHELL_CONTRACT,
    OPENING_EVENT_COVERAGE_CONTRACT,
    PROPOSED_EFFECTS_SHAPE_CONTRACT,
    SEAM_MIRROR_VALIDATOR_IDS,
    seam_mirror_registry_map,
)
from ai_stack.story_runtime.narrative.information_disclosure_engine import validate_information_disclosure_realization
from ai_stack.story_runtime.narrator.narrator_authority_validation import evaluate_narrator_authority_contract
from ai_stack.story_runtime.npc_agency.npc_agency_realization import validate_npc_initiative_realization
from ai_stack.story_runtime.turn.player_turn_validator_evaluation import (
    evaluate_action_resolution_contract,
    evaluate_player_intent_contract,
)
from ai_stack.story_runtime.narrative.scene_energy_engine import validate_scene_energy_realization
from ai_stack.story_runtime.narrative.sensory_context_engine import validate_sensory_context_realization

LOCAL_PROOF_LEVEL = "local_only"

# ADR-0041 turn-class coverage (deterministic semantic validator IDs only; no Pi/Π keys).
# Enforced IDs align with `capability_selector` opening / player / NPC conflict paths.
TURN_CLASS_OPENING_SCENE = "opening_scene"
TURN_CLASS_NORMAL_PLAYER_TURN = "normal_player_turn"
TURN_CLASS_NPC_CONFLICT_TURN = "npc_conflict_turn"
TURN_CLASS_RECOVERY_TURN = "recovery_turn"
TURN_CLASS_SYSTEM_TRANSITION = "system_transition"
TURN_CLASS_DEGRADED_OR_FALLBACK_TURN = "degraded_or_fallback_turn"

# Observer diagnostic IDs referenced by validator plans when a capability is observed (non-blocking).
# Includes `environment_state_diagnostic` (fallback from `_observer_diagnostic_id` — not listed in OBSERVER_DIAGNOSTICS).
CANONICAL_OBSERVER_DIAGNOSTIC_IDS: frozenset[str] = frozenset(
    frozenset(OBSERVER_DIAGNOSTICS.values()) | {"environment_state_diagnostic"}
)


# Inventory status vocabulary (ADR-0041 registry audit).
STATUS_IMPLEMENTED_CALLABLE = "implemented_callable"
STATUS_IMPLEMENTED_NEEDS_ADAPTER = "implemented_but_needs_adapter"
STATUS_PLANNED_ONLY = "planned_only"
STATUS_OBSERVER_ONLY = "observer_only"
STATUS_JUDGE_ONLY = "judge_only"
STATUS_NOT_SAFE_FOR_REGISTRY = "not_safe_for_registry"
STATUS_DEPRECATED_OR_STALE = "deprecated_or_stale"

PLANNED_LOCAL_VALIDATOR_IDS: tuple[str, ...] = tuple(LOCAL_VALIDATORS.values())
PLANNED_OBSERVER_DIAGNOSTIC_IDS: tuple[str, ...] = tuple(OBSERVER_DIAGNOSTICS.values())
PLANNED_SEAM_MIRROR_VALIDATOR_IDS: tuple[str, ...] = SEAM_MIRROR_VALIDATOR_IDS
PLANNED_JUDGE_IDS: tuple[str, ...] = tuple(JUDGE_VALIDATORS.values())
PLANNED_ALL_DISPATCH_IDS: tuple[str, ...] = (
    *PLANNED_LOCAL_VALIDATOR_IDS,
    *PLANNED_OBSERVER_DIAGNOSTIC_IDS,
    *PLANNED_SEAM_MIRROR_VALIDATOR_IDS,
    *PLANNED_JUDGE_IDS,
)


@dataclass(frozen=True)
class ValidatorRegistryInventoryRow:
    validator_id: str
    capability: str
    current_status: str
    source_file_or_symbol: str
    adapter_needed: bool
    safe_for_local_plan_enforced: bool
    blocking_or_non_blocking: str
    judge_required: bool
    notes: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "validator_id", validate_semantic_capability_name(self.validator_id))
        object.__setattr__(self, "capability", validate_semantic_capability_name(self.capability))


VALIDATOR_REGISTRY_INVENTORY: tuple[ValidatorRegistryInventoryRow, ...] = (
    ValidatorRegistryInventoryRow(
        validator_id="narrator_authority_contract",
        capability=CAP_NARRATOR_AUTHORITY,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol="ai_stack/story_runtime/narrator/narrator_authority_validation.py::evaluate_narrator_authority_contract",
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Thin adapter over deterministic narrator required/present rules extracted from runtime authority assembly.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="scene_energy_contract",
        capability=CAP_SCENE_ENERGY,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol="ai_stack/story_runtime/narrative/scene_energy_engine.py::validate_scene_energy_realization",
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Requires dispatch_context scene_energy_target, scene_energy_transition, structured_output.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="environment_state_contract",
        capability=CAP_ENVIRONMENT_STATE,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol="ai_stack/contracts/environment_state_contracts.py::evaluate_environment_state_contract",
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Thin adapter over normalize_environment_state; requires module_id and environment_state or environment_model.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="information_disclosure_contract",
        capability=CAP_INFORMATION_DISCLOSURE,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol="ai_stack/story_runtime/narrative/information_disclosure_engine.py::validate_information_disclosure_realization",
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Requires dispatch_context information_disclosure_target and structured_output.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="voice_consistency_contract",
        capability=CAP_VOICE_CONSISTENCY,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol="ai_stack/story_runtime/npc_agency/character/character_voice_validation.py::validate_voice_consistency",
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Requires dispatch_context structured_output and voice_profiles.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="npc_agency_contract",
        capability=CAP_NPC_AGENCY,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol="ai_stack/story_runtime/npc_agency/npc_agency_realization.py::validate_npc_initiative_realization",
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Requires dispatch_context npc_agency_plan and structured_output.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="player_intent_contract",
        capability=CAP_PLAYER_INTENT_INFERENCE,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol="ai_stack/story_runtime/turn/player_turn_validator_evaluation.py::evaluate_player_intent_contract",
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Thin adapter over player_input_kind contract checks and interpret_goc_semantic_move.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="action_resolution_contract",
        capability=CAP_ACTION_RESOLUTION,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol="ai_stack/story_runtime/turn/player_turn_validator_evaluation.py::evaluate_action_resolution_contract",
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Thin adapter over resolve_player_action affordance outcomes or pre-resolved frames.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="consequence_cascade_contract",
        capability=CAP_CONSEQUENCE_CASCADE,
        current_status=STATUS_IMPLEMENTED_NEEDS_ADAPTER,
        source_file_or_symbol="ai_stack/contracts/consequence_cascade_contracts.py::validate_consequence_cascade_record",
        adapter_needed=True,
        safe_for_local_plan_enforced=False,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Record validator exists; world-engine path uses committed cascade state, not turn-local structured_output alone.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="forecast_contract",
        capability=CAP_LONG_HORIZON_FORECAST,
        current_status=STATUS_PLANNED_ONLY,
        source_file_or_symbol="ai_stack/story_runtime/runtime_aspect_ledger.py::branching_forecast projection",
        adapter_needed=True,
        safe_for_local_plan_enforced=False,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Forecast projection metadata only; no local validate_forecast_realization.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="silence_negative_space_contract",
        capability=CAP_SILENCE_NEGATIVE_SPACE,
        current_status=STATUS_IMPLEMENTED_NEEDS_ADAPTER,
        source_file_or_symbol="ai_stack/contracts/silence_negative_space_contract.py::build_silence_negative_space_decision",
        adapter_needed=True,
        safe_for_local_plan_enforced=False,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Decision builder exists; no registry-safe validate_silence_negative_space_realization.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="dramatic_irony_contract",
        capability=CAP_DRAMATIC_IRONY,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol="ai_stack/story_runtime/narrative/dramatic_irony_runtime.py::validate_dramatic_irony_realization",
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Requires dispatch_context dramatic_irony_record and generation payload.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="thematic_tracking_diagnostic",
        capability=CAP_THEMATIC_TRACKING,
        current_status=STATUS_OBSERVER_ONLY,
        source_file_or_symbol="ai_stack/contracts/narrative_aspect_contracts.py::validate_narrative_aspects",
        adapter_needed=True,
        safe_for_local_plan_enforced=False,
        blocking_or_non_blocking="non_blocking",
        judge_required=False,
        notes="Thematic tracking maps to narrative aspect policy; observe-only in ADR-0041 opening plan.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="callback_web_diagnostic",
        capability=CAP_CALLBACK_WEB,
        current_status=STATUS_OBSERVER_ONLY,
        source_file_or_symbol="ai_stack/contracts/callback_web_contracts.py::validate_callback_web_record",
        adapter_needed=True,
        safe_for_local_plan_enforced=False,
        blocking_or_non_blocking="non_blocking",
        judge_required=False,
        notes="Continuity record validator; observer diagnostic only for plan dispatch.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="sensory_context_diagnostic",
        capability=CAP_SENSORY_CONTEXT,
        current_status=STATUS_OBSERVER_ONLY,
        source_file_or_symbol="ai_stack/story_runtime/narrative/sensory_context_engine.py::validate_sensory_context_realization",
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="non_blocking",
        judge_required=False,
        notes="Callable exists but ADR-0041 plans it as non-blocking observer diagnostic.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="broad_nlu_listening_diagnostic",
        capability=CAP_BROAD_NLU_LISTENING,
        current_status=STATUS_OBSERVER_ONLY,
        source_file_or_symbol="ai_stack/contracts/active_listening_contracts.py::derive_broad_nlu_listening",
        adapter_needed=True,
        safe_for_local_plan_enforced=False,
        blocking_or_non_blocking="non_blocking",
        judge_required=False,
        notes="Structured local active-listening evidence; observer diagnostic until production gating is governed.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="conversational_memory_diagnostic",
        capability=CAP_CONVERSATIONAL_MEMORY,
        current_status=STATUS_OBSERVER_ONLY,
        source_file_or_symbol="ai_stack/contracts/active_listening_contracts.py::derive_conversational_memory_context",
        adapter_needed=True,
        safe_for_local_plan_enforced=False,
        blocking_or_non_blocking="non_blocking",
        judge_required=False,
        notes="Committed-memory continuity projection; observer diagnostic, no raw prompt or raw player input storage.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id="prompt_authority_diagnostic",
        capability=CAP_PROMPT_AUTHORITY,
        current_status=STATUS_OBSERVER_ONLY,
        source_file_or_symbol="ai_stack/contracts/active_listening_contracts.py::build_prompt_authority_packet",
        adapter_needed=True,
        safe_for_local_plan_enforced=False,
        blocking_or_non_blocking="non_blocking",
        judge_required=False,
        notes="Model-visible prompt authority declaration; observer diagnostic until production gate authority is governed.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id=ACTOR_LANE_FORBIDDEN_CONTRACT,
        capability=GOC_SEAM_MIRROR_SUITE_CAPABILITY,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol=(
            "ai_stack/story_runtime/turn/god_of_carnage_seam_mirror_validator_adapters.py::adapter_actor_lane_forbidden_contract"
        ),
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Deterministic mirror of god_of_carnage_turn_seams._check_human_actor_violations; plan_enforced sidecar only.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id=NPC_TRANSCRIPT_SHELL_CONTRACT,
        capability=GOC_SEAM_MIRROR_SUITE_CAPABILITY,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol=(
            "ai_stack/story_runtime/turn/god_of_carnage_seam_mirror_validator_adapters.py::adapter_npc_transcript_shell_contract"
        ),
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Deterministic mirror of god_of_carnage_turn_seams._check_npc_spoken_action_lane_blob_cap.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id=PROPOSED_EFFECTS_SHAPE_CONTRACT,
        capability=GOC_SEAM_MIRROR_SUITE_CAPABILITY,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol=(
            "ai_stack/story_runtime/turn/god_of_carnage_seam_mirror_validator_adapters.py::adapter_proposed_effects_shape_contract"
        ),
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Deterministic mirror of run_validation_seam proposed_state_effects shape checks.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id=MODEL_GENERATION_PRECHECK_CONTRACT,
        capability=GOC_SEAM_MIRROR_SUITE_CAPABILITY,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol=(
            "ai_stack/story_runtime/turn/god_of_carnage_seam_mirror_validator_adapters.py::adapter_model_generation_precheck_contract"
        ),
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Deterministic mirror of run_validation_seam generation success/error short-circuit.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id=HARD_FORBIDDEN_RUNTIME_CONTRACT,
        capability=GOC_SEAM_MIRROR_SUITE_CAPABILITY,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol=(
            "ai_stack/story_runtime/turn/god_of_carnage_seam_mirror_validator_adapters.py::adapter_hard_forbidden_runtime_contract"
        ),
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Deterministic mirror of god_of_carnage_knowledge_runtime_gates.detect_hard_forbidden_runtime.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id=OPENING_EVENT_COVERAGE_CONTRACT,
        capability=GOC_SEAM_MIRROR_SUITE_CAPABILITY,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol=(
            "ai_stack/story_runtime/turn/god_of_carnage_seam_mirror_validator_adapters.py::adapter_opening_event_coverage_contract"
        ),
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes="Deterministic mirror of evaluate_opening_event_coverage when turn_input_class is opening.",
    ),
    ValidatorRegistryInventoryRow(
        validator_id=DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT,
        capability=GOC_SEAM_MIRROR_SUITE_CAPABILITY,
        current_status=STATUS_IMPLEMENTED_CALLABLE,
        source_file_or_symbol=(
            "ai_stack/story_runtime/turn/god_of_carnage_seam_mirror_validator_adapters.py::adapter_dramatic_effect_gate_mirror_contract"
        ),
        adapter_needed=True,
        safe_for_local_plan_enforced=True,
        blocking_or_non_blocking="blocking",
        judge_required=False,
        notes=(
            "Best-effort mirror of evaluate_dramatic_effect_gate; may use defaulted evaluation context "
            "when graph dispatch context omits seam fields."
        ),
    ),
)

def inventory_rows_by_validator_id() -> dict[str, ValidatorRegistryInventoryRow]:
    return {row.validator_id: row for row in VALIDATOR_REGISTRY_INVENTORY}


def unavailable_validator_result(
    validator_id: str,
    *,
    reason: str = "validator_not_registered",
    blocking: bool = True,
) -> dict[str, Any]:
    return {
        "validator_id": validate_semantic_capability_name(validator_id),
        "available": False,
        "passed": False,
        "blocking": blocking,
        "proof_level": LOCAL_PROOF_LEVEL,
        "live_or_staging_evidence": False,
        "status": "unavailable",
        "reason": reason,
    }


def normalize_validator_dispatch_result(
    validator_id: str,
    raw: dict[str, Any] | None,
    *,
    blocking: bool = True,
) -> dict[str, Any]:
    """Normalize a local validator return into ADR-0041 registry evidence shape."""
    vid = validate_semantic_capability_name(validator_id)
    if not isinstance(raw, dict):
        return unavailable_validator_result(vid, reason="validator_returned_non_dict")
    status = str(raw.get("status") or "").strip().lower()
    contract_pass = raw.get("contract_pass")
    if contract_pass is None:
        contract_pass = status in {"approved", "passed", "local_stub_executed", "local_executed"}
    passed = bool(contract_pass) and status not in {"rejected", "failed", "error", "unavailable"}
    available = status not in {"unavailable"} and raw.get("available") is not False
    return {
        "validator_id": vid,
        "available": available,
        "passed": passed,
        "blocking": bool(raw.get("blocking", blocking)),
        "proof_level": LOCAL_PROOF_LEVEL,
        "live_or_staging_evidence": False,
        "status": status or ("approved" if passed else "rejected"),
        "reason": raw.get("reason"),
        "source_status": status,
        "failure_codes": raw.get("failure_codes") or [],
    }


def _structured_output(ctx: dict[str, Any]) -> dict[str, Any]:
    structured = ctx.get("structured_output")
    return structured if isinstance(structured, dict) else {}


def _adapter_narrator_authority(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    structured = ctx.get("structured_output")
    if not isinstance(structured, dict) and not isinstance(ctx.get("proposed_state_effects"), list):
        return unavailable_validator_result(
            "narrator_authority_contract",
            reason="missing_required_context",
        )
    raw = evaluate_narrator_authority_contract(
        structured_output=structured if isinstance(structured, dict) else None,
        turn_number=int(ctx.get("turn_number") or 0),
        narrator_required=ctx.get("narrator_required"),
        player_input_kind=ctx.get("player_input_kind") or ctx.get("input_kind"),
        affordance_requires_narrator=ctx.get("affordance_requires_narrator"),
        narrator_response_expected=ctx.get("narrator_response_expected"),
        proposed_state_effects=ctx.get("proposed_state_effects")
        if isinstance(ctx.get("proposed_state_effects"), list)
        else None,
    )
    return normalize_validator_dispatch_result("narrator_authority_contract", raw, blocking=True)


def _adapter_environment_state(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    raw = evaluate_environment_state_contract(
        environment_state=ctx.get("environment_state")
        if isinstance(ctx.get("environment_state"), dict)
        else None,
        module_id=str(ctx.get("module_id") or "").strip() or None,
        environment_model=ctx.get("environment_model")
        if isinstance(ctx.get("environment_model"), dict)
        else None,
        runtime_projection=ctx.get("runtime_projection")
        if isinstance(ctx.get("runtime_projection"), dict)
        else None,
        actor_lane_context=ctx.get("actor_lane_context")
        if isinstance(ctx.get("actor_lane_context"), dict)
        else None,
        turn_number=int(ctx.get("turn_number") or 0),
    )
    return normalize_validator_dispatch_result("environment_state_contract", raw, blocking=True)


def _adapter_scene_energy(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    target = ctx.get("scene_energy_target")
    if not isinstance(target, dict):
        return unavailable_validator_result(
            "scene_energy_contract",
            reason="missing_scene_energy_target",
        )
    raw = validate_scene_energy_realization(
        scene_energy_target=target,
        scene_energy_transition=ctx.get("scene_energy_transition")
        if isinstance(ctx.get("scene_energy_transition"), dict)
        else None,
        structured_output=_structured_output(ctx),
        scene_plan_record=ctx.get("scene_plan_record")
        if isinstance(ctx.get("scene_plan_record"), dict)
        else None,
    )
    return normalize_validator_dispatch_result("scene_energy_contract", raw, blocking=True)


def _adapter_information_disclosure(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    target = ctx.get("information_disclosure_target")
    if not isinstance(target, dict):
        return unavailable_validator_result(
            "information_disclosure_contract",
            reason="missing_information_disclosure_target",
        )
    raw = validate_information_disclosure_realization(
        information_disclosure_target=target,
        structured_output=_structured_output(ctx),
        visible_blocks=ctx.get("visible_blocks") if isinstance(ctx.get("visible_blocks"), list) else None,
    )
    return normalize_validator_dispatch_result("information_disclosure_contract", raw, blocking=True)


def _adapter_voice_consistency(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    profiles = ctx.get("voice_profiles")
    if not isinstance(profiles, list):
        return unavailable_validator_result(
            "voice_consistency_contract",
            reason="missing_voice_profiles",
        )
    raw = validate_voice_consistency(
        structured_output=_structured_output(ctx),
        voice_profiles=profiles,
        validation_mode=ctx.get("voice_validation_mode"),
    ).to_runtime_dict()
    return normalize_validator_dispatch_result("voice_consistency_contract", raw, blocking=True)


def _adapter_npc_agency(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    plan = ctx.get("npc_agency_plan")
    if not isinstance(plan, dict):
        return unavailable_validator_result(
            "npc_agency_contract",
            reason="missing_npc_agency_plan",
        )
    raw = validate_npc_initiative_realization(
        plan,
        _structured_output(ctx),
        actor_lane_context=ctx.get("actor_lane_context")
        if isinstance(ctx.get("actor_lane_context"), dict)
        else None,
        strict_required=bool(ctx.get("npc_agency_strict_required", True)),
    )
    status = str(raw.get("status") or "").strip().lower()
    passed = status == "approved"
    return {
        "validator_id": "npc_agency_contract",
        "available": True,
        "passed": passed,
        "blocking": True,
        "proof_level": LOCAL_PROOF_LEVEL,
        "live_or_staging_evidence": False,
        "status": status or ("approved" if passed else "rejected"),
        "reason": None if passed else "npc_initiative_realization_not_approved",
        "failure_codes": list(raw.get("failure_codes") or []),
    }


def _adapter_dramatic_irony(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    record = ctx.get("dramatic_irony_record")
    if not isinstance(record, dict):
        return unavailable_validator_result(
            "dramatic_irony_contract",
            reason="missing_dramatic_irony_record",
        )
    generation = ctx.get("generation")
    generation = generation if isinstance(generation, dict) else {"metadata": {"structured_output": _structured_output(ctx)}}
    raw = validate_dramatic_irony_realization(
        record=record,
        generation=generation,
        proposed_state_effects=ctx.get("proposed_state_effects")
        if isinstance(ctx.get("proposed_state_effects"), list)
        else None,
    )
    status = str(raw.get("realization_status") or raw.get("status") or "").strip().lower()
    passed = status in {"realized", "selected_only", "not_evaluated"} and not raw.get("violation_codes")
    if raw.get("violation_codes"):
        passed = False
    return {
        "validator_id": "dramatic_irony_contract",
        "available": True,
        "passed": passed,
        "blocking": True,
        "proof_level": LOCAL_PROOF_LEVEL,
        "live_or_staging_evidence": False,
        "status": "approved" if passed else "rejected",
        "reason": None if passed else "dramatic_irony_violation",
        "violation_codes": list(raw.get("violation_codes") or []),
    }


def _adapter_player_intent(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    interpreted = ctx.get("interpreted_input")
    if not isinstance(interpreted, dict):
        return unavailable_validator_result(
            "player_intent_contract",
            reason="missing_required_context",
        )
    raw = ctx.get("raw_player_input") or ctx.get("raw_text")
    raw_text = str(raw or interpreted.get("raw_text") or "").strip() or None
    raw = evaluate_player_intent_contract(
        raw_player_input=raw_text,
        interpreted_input=interpreted,
        interpreted_move=ctx.get("interpreted_move")
        if isinstance(ctx.get("interpreted_move"), dict)
        else None,
        module_id=str(ctx.get("module_id") or "").strip() or None,
    )
    return normalize_validator_dispatch_result("player_intent_contract", raw, blocking=True)


def _adapter_action_resolution(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    frame = ctx.get("player_action_frame")
    aff = ctx.get("affordance_resolution")
    if isinstance(frame, dict) and isinstance(aff, dict):
        raw = evaluate_action_resolution_contract(
            player_action_frame=frame,
            affordance_resolution=aff,
        )
        return normalize_validator_dispatch_result("action_resolution_contract", raw, blocking=True)

    interpreted = ctx.get("interpreted_input")
    raw_input = ctx.get("raw_player_input") or ctx.get("raw_text")
    module_id = str(ctx.get("module_id") or "").strip() or None
    projection = ctx.get("runtime_projection")
    if not isinstance(interpreted, dict) or not str(raw_input or "").strip():
        return unavailable_validator_result(
            "action_resolution_contract",
            reason="missing_required_context",
        )
    if not module_id or not isinstance(projection, dict):
        return unavailable_validator_result(
            "action_resolution_contract",
            reason="missing_required_context",
        )
    raw = evaluate_action_resolution_contract(
        raw_player_input=str(raw_input or "").strip(),
        interpreted_input=interpreted,
        module_id=module_id,
        runtime_projection=projection,
        content_modules_root=ctx.get("content_modules_root"),
        environment_state=ctx.get("environment_state")
        if isinstance(ctx.get("environment_state"), dict)
        else None,
        environment_model=ctx.get("environment_model")
        if isinstance(ctx.get("environment_model"), dict)
        else None,
        player_local_context=ctx.get("player_local_context")
        if isinstance(ctx.get("player_local_context"), dict)
        else None,
    )
    return normalize_validator_dispatch_result("action_resolution_contract", raw, blocking=True)


def _adapter_sensory_context_diagnostic(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    target = ctx.get("sensory_context_target")
    if not isinstance(target, dict):
        return unavailable_validator_result(
            "sensory_context_diagnostic",
            reason="missing_sensory_context_target",
            blocking=False,
        )
    raw = validate_sensory_context_realization(
        sensory_context_target=target,
        sensory_context_state=ctx.get("sensory_context_state")
        if isinstance(ctx.get("sensory_context_state"), dict)
        else None,
        structured_output=_structured_output(ctx),
    )
    result = normalize_validator_dispatch_result(
        "sensory_context_diagnostic",
        raw,
        blocking=False,
    )
    result["blocking"] = False
    return result


_GOC_SEAM_MIRROR_CORE: tuple[str, ...] = (
    ACTOR_LANE_FORBIDDEN_CONTRACT,
    NPC_TRANSCRIPT_SHELL_CONTRACT,
    PROPOSED_EFFECTS_SHAPE_CONTRACT,
    MODEL_GENERATION_PRECHECK_CONTRACT,
    HARD_FORBIDDEN_RUNTIME_CONTRACT,
    DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT,
)

_OPENING_CAPABILITY_ENFORCED_VALIDATOR_IDS: tuple[str, ...] = (
    "narrator_authority_contract",
    "scene_energy_contract",
    "environment_state_contract",
    "information_disclosure_contract",
    "voice_consistency_contract",
)

_PLAYER_CAPABILITY_ENFORCED_VALIDATOR_IDS: tuple[str, ...] = (
    "player_intent_contract",
    "action_resolution_contract",
    "information_disclosure_contract",
    "voice_consistency_contract",
    "scene_energy_contract",
)

_NPC_CAPABILITY_ENFORCED_VALIDATOR_IDS: tuple[str, ...] = (
    "npc_agency_contract",
    "voice_consistency_contract",
    "scene_energy_contract",
    "information_disclosure_contract",
)

_RECOVERY_CAPABILITY_ENFORCED_VALIDATOR_IDS: tuple[str, ...] = (
    "narrator_authority_contract",
    "voice_consistency_contract",
    "information_disclosure_contract",
)

_SYSTEM_TRANSITION_CAPABILITY_ENFORCED_VALIDATOR_IDS: tuple[str, ...] = (
    "narrator_authority_contract",
    "environment_state_contract",
    "information_disclosure_contract",
)

_DEGRADED_OR_FALLBACK_CAPABILITY_ENFORCED_VALIDATOR_IDS: tuple[str, ...] = (
    "narrator_authority_contract",
    "voice_consistency_contract",
    "scene_energy_contract",
    "information_disclosure_contract",
)

_OPENING_ENFORCED_VALIDATOR_IDS: tuple[str, ...] = (
    *_GOC_SEAM_MIRROR_CORE,
    OPENING_EVENT_COVERAGE_CONTRACT,
    *_OPENING_CAPABILITY_ENFORCED_VALIDATOR_IDS,
)

# Capability-selection plan only (no seam-mirror prepend). Graph sidecar prepends mirrors atop this.
OPENING_SCENE_CAPABILITY_PLAN_VALIDATOR_IDS: tuple[str, ...] = _OPENING_CAPABILITY_ENFORCED_VALIDATOR_IDS
NORMAL_PLAYER_TURN_CAPABILITY_PLAN_VALIDATOR_IDS: tuple[str, ...] = _PLAYER_CAPABILITY_ENFORCED_VALIDATOR_IDS

_PLAYER_TURN_ENFORCED_VALIDATOR_IDS: tuple[str, ...] = (
    *_GOC_SEAM_MIRROR_CORE,
    *_PLAYER_CAPABILITY_ENFORCED_VALIDATOR_IDS,
)

_NPC_CONFLICT_ENFORCED_VALIDATOR_IDS: tuple[str, ...] = (
    *_GOC_SEAM_MIRROR_CORE,
    *_NPC_CAPABILITY_ENFORCED_VALIDATOR_IDS,
)

_RECOVERY_ENFORCED_VALIDATOR_IDS: tuple[str, ...] = (
    *_GOC_SEAM_MIRROR_CORE,
    *_RECOVERY_CAPABILITY_ENFORCED_VALIDATOR_IDS,
)

_SYSTEM_TRANSITION_ENFORCED_VALIDATOR_IDS: tuple[str, ...] = (
    *_GOC_SEAM_MIRROR_CORE,
    *_SYSTEM_TRANSITION_CAPABILITY_ENFORCED_VALIDATOR_IDS,
)

_DEGRADED_OR_FALLBACK_ENFORCED_VALIDATOR_IDS: tuple[str, ...] = (
    *_GOC_SEAM_MIRROR_CORE,
    *_DEGRADED_OR_FALLBACK_CAPABILITY_ENFORCED_VALIDATOR_IDS,
)

KNOWN_TURN_CLASSES: tuple[str, ...] = (
    TURN_CLASS_OPENING_SCENE,
    TURN_CLASS_NORMAL_PLAYER_TURN,
    TURN_CLASS_NPC_CONFLICT_TURN,
    TURN_CLASS_RECOVERY_TURN,
    TURN_CLASS_SYSTEM_TRANSITION,
    TURN_CLASS_DEGRADED_OR_FALLBACK_TURN,
)

TURN_CLASS_ENFORCED_VALIDATORS: dict[str, tuple[str, ...]] = {
    TURN_CLASS_OPENING_SCENE: _OPENING_ENFORCED_VALIDATOR_IDS,
    TURN_CLASS_NORMAL_PLAYER_TURN: _PLAYER_TURN_ENFORCED_VALIDATOR_IDS,
    TURN_CLASS_NPC_CONFLICT_TURN: _NPC_CONFLICT_ENFORCED_VALIDATOR_IDS,
    TURN_CLASS_RECOVERY_TURN: _RECOVERY_ENFORCED_VALIDATOR_IDS,
    TURN_CLASS_SYSTEM_TRANSITION: _SYSTEM_TRANSITION_ENFORCED_VALIDATOR_IDS,
    TURN_CLASS_DEGRADED_OR_FALLBACK_TURN: _DEGRADED_OR_FALLBACK_ENFORCED_VALIDATOR_IDS,
}

# Typical observer diagnostics for each turn class (selector-driven; always non-blocking in plans).
TURN_CLASS_TYPICAL_OBSERVER_DIAGNOSTIC_IDS: dict[str, tuple[str, ...]] = {
    TURN_CLASS_OPENING_SCENE: (
        "thematic_tracking_diagnostic",
        "callback_web_diagnostic",
        "sensory_context_diagnostic",
    ),
    TURN_CLASS_NORMAL_PLAYER_TURN: (
        "environment_state_diagnostic",
        "broad_nlu_listening_diagnostic",
        "conversational_memory_diagnostic",
        "prompt_authority_diagnostic",
        "thematic_tracking_diagnostic",
        "callback_web_diagnostic",
    ),
    TURN_CLASS_NPC_CONFLICT_TURN: (
        "thematic_tracking_diagnostic",
        "callback_web_diagnostic",
    ),
    TURN_CLASS_RECOVERY_TURN: (
        "environment_state_diagnostic",
        "conversational_memory_diagnostic",
        "thematic_tracking_diagnostic",
    ),
    TURN_CLASS_SYSTEM_TRANSITION: (
        "environment_state_diagnostic",
        "conversational_memory_diagnostic",
        "prompt_authority_diagnostic",
    ),
    TURN_CLASS_DEGRADED_OR_FALLBACK_TURN: (
        "environment_state_diagnostic",
        "conversational_memory_diagnostic",
        "callback_web_diagnostic",
    ),
}


_AVAILABLE_ADAPTER_REGISTRY: dict[str, LocalValidatorCallable] = {
    "narrator_authority_contract": _adapter_narrator_authority,
    "environment_state_contract": _adapter_environment_state,
    "scene_energy_contract": _adapter_scene_energy,
    "information_disclosure_contract": _adapter_information_disclosure,
    "voice_consistency_contract": _adapter_voice_consistency,
    "player_intent_contract": _adapter_player_intent,
    "action_resolution_contract": _adapter_action_resolution,
    "npc_agency_contract": _adapter_npc_agency,
    "dramatic_irony_contract": _adapter_dramatic_irony,
    "sensory_context_diagnostic": _adapter_sensory_context_diagnostic,
    **seam_mirror_registry_map(),
}


def build_default_semantic_validator_registry() -> dict[str, LocalValidatorCallable]:
    """Return an empty conservative registry (production default)."""
    return {}


def build_available_semantic_validator_registry() -> dict[str, LocalValidatorCallable]:
    """Return opt-in adapters for inventory rows marked safe_for_local_plan_enforced."""
    allowed = {
        row.validator_id
        for row in VALIDATOR_REGISTRY_INVENTORY
        if row.safe_for_local_plan_enforced
    }
    return {
        validator_id: _AVAILABLE_ADAPTER_REGISTRY[validator_id]
        for validator_id in allowed
        if validator_id in _AVAILABLE_ADAPTER_REGISTRY
    }


def build_opening_enforced_semantic_validator_registry() -> dict[str, LocalValidatorCallable]:
    """Return opening-scene enforced validators that have safe local adapters."""
    available = build_available_semantic_validator_registry()
    return {
        validator_id: available[validator_id]
        for validator_id in _OPENING_ENFORCED_VALIDATOR_IDS
        if validator_id in available
    }


def build_player_turn_enforced_semantic_validator_registry() -> dict[str, LocalValidatorCallable]:
    """Return normal player-turn enforced validators that have safe local adapters."""
    available = build_available_semantic_validator_registry()
    return {
        validator_id: available[validator_id]
        for validator_id in _PLAYER_TURN_ENFORCED_VALIDATOR_IDS
        if validator_id in available
    }


def build_npc_conflict_enforced_semantic_validator_registry() -> dict[str, LocalValidatorCallable]:
    """Return NPC conflict-turn enforced validators that have safe local adapters."""
    available = build_available_semantic_validator_registry()
    return {
        validator_id: available[validator_id]
        for validator_id in _NPC_CONFLICT_ENFORCED_VALIDATOR_IDS
        if validator_id in available
    }


def build_recovery_turn_enforced_semantic_validator_registry() -> dict[str, LocalValidatorCallable]:
    """Return recovery-turn enforced validators that have safe local adapters."""
    available = build_available_semantic_validator_registry()
    return {
        validator_id: available[validator_id]
        for validator_id in _RECOVERY_ENFORCED_VALIDATOR_IDS
        if validator_id in available
    }


def build_system_transition_enforced_semantic_validator_registry() -> dict[str, LocalValidatorCallable]:
    """Return system-transition enforced validators that have safe local adapters."""
    available = build_available_semantic_validator_registry()
    return {
        validator_id: available[validator_id]
        for validator_id in _SYSTEM_TRANSITION_ENFORCED_VALIDATOR_IDS
        if validator_id in available
    }


def build_degraded_or_fallback_enforced_semantic_validator_registry() -> dict[str, LocalValidatorCallable]:
    """Return degraded/fallback enforced validators that have safe local adapters."""
    available = build_available_semantic_validator_registry()
    return {
        validator_id: available[validator_id]
        for validator_id in _DEGRADED_OR_FALLBACK_ENFORCED_VALIDATOR_IDS
        if validator_id in available
    }


def normalize_turn_class_key(turn_class: str) -> str:
    """Normalize and validate a turn-class key (lowercase semantic identifier)."""
    return validate_semantic_capability_name(str(turn_class or "").strip())


def get_turn_class_enforced_validators(turn_class: str) -> tuple[str, ...]:
    """Return enforced validator IDs for an ADR-0041 turn class; fail closed if unknown."""
    key = normalize_turn_class_key(turn_class)
    if key not in TURN_CLASS_ENFORCED_VALIDATORS:
        raise ValueError(f"Unknown ADR-0041 turn class: {turn_class!r}")
    return TURN_CLASS_ENFORCED_VALIDATORS[key]


def goc_seam_mirror_plan_validator_ids_for_turn_class(turn_class: str) -> tuple[str, ...]:
    """Seam-mirror validators prepended before capability-derived plan entries (graph plan_enforced)."""
    key = normalize_turn_class_key(turn_class)
    if key == TURN_CLASS_OPENING_SCENE:
        return _GOC_SEAM_MIRROR_CORE + (OPENING_EVENT_COVERAGE_CONTRACT,)
    return _GOC_SEAM_MIRROR_CORE


def get_typical_observer_diagnostic_ids_for_turn_class(turn_class: str) -> tuple[str, ...]:
    """Return typical non-blocking observer diagnostic IDs for a turn class."""
    key = normalize_turn_class_key(turn_class)
    if key not in TURN_CLASS_TYPICAL_OBSERVER_DIAGNOSTIC_IDS:
        raise ValueError(f"Unknown ADR-0041 turn class: {turn_class!r}")
    return TURN_CLASS_TYPICAL_OBSERVER_DIAGNOSTIC_IDS[key]


@dataclass(frozen=True)
class TurnClassRegistryCoverage:
    """Local-only coverage report: which enforced validators are present in a registry map."""

    turn_class: str
    required_enforced_validator_ids: tuple[str, ...]
    validator_ids_registered: tuple[str, ...]
    validator_ids_missing: tuple[str, ...]
    typical_observer_diagnostic_ids: tuple[str, ...]
    coverage_complete: bool


def get_registry_coverage_for_turn_class(
    turn_class: str,
    registry: Mapping[str, LocalValidatorCallable],
) -> TurnClassRegistryCoverage:
    """Compare required enforced validators for a turn class to a registry (no execution)."""
    required = get_turn_class_enforced_validators(turn_class)
    registered = tuple(vid for vid in required if vid in registry)
    missing = tuple(vid for vid in required if vid not in registry)
    observers = get_typical_observer_diagnostic_ids_for_turn_class(turn_class)
    key = normalize_turn_class_key(turn_class)
    return TurnClassRegistryCoverage(
        turn_class=key,
        required_enforced_validator_ids=required,
        validator_ids_registered=registered,
        validator_ids_missing=missing,
        typical_observer_diagnostic_ids=observers,
        coverage_complete=len(missing) == 0,
    )


def assert_turn_class_registry_coverage(
    turn_class: str,
    registry: Mapping[str, LocalValidatorCallable],
    *,
    require_complete: bool = True,
) -> TurnClassRegistryCoverage:
    """Assert optional full adapter coverage for a turn class; returns the coverage report."""
    cov = get_registry_coverage_for_turn_class(turn_class, registry)
    if require_complete and not cov.coverage_complete:
        raise AssertionError(
            f"Turn class {cov.turn_class!r} missing registry adapters for: {cov.validator_ids_missing!r}"
        )
    return cov


def build_semantic_validator_registry(
    *,
    include_available_adapters: bool = False,
) -> dict[str, LocalValidatorCallable]:
    """Build a registry map for explicit plan_enforced dispatch."""
    if not include_available_adapters:
        return build_default_semantic_validator_registry()
    return dict(build_available_semantic_validator_registry())
