"""Shared data contracts for LangGraph runtime validation."""

from __future__ import annotations

from .dependencies import Any, Callable, dataclass, field

ValidationHook = Callable[..., Any]

class RuntimeAspectValidationHooks:
    actor_lane_validation: ValidationHook
    build_authority_aspect_records: ValidationHook
    dramatic_quality_rejection_locked: ValidationHook
    structured_output_from_generation: ValidationHook
    runtime_governance_section: ValidationHook
    voice_consistency_validation: ValidationHook
    voice_aspect_record: ValidationHook
    voice_semantic_failure_present: ValidationHook
    scene_energy_aspect_record: ValidationHook
    pacing_rhythm_aspect_record: ValidationHook
    sensory_context_aspect_record: ValidationHook
    social_pressure_aspect_record: ValidationHook
    information_disclosure_aspect_record: ValidationHook
    npc_agency_plan_from_state: ValidationHook
    npc_agency_aspect_record: ValidationHook
class _RuntimeAspectBuild:
    state: Any
    generation: dict[str, Any]
    proposed_state_effects: list[dict[str, Any]]
    hooks: RuntimeAspectValidationHooks
    outcome: dict[str, Any]
    dramatic_rejection_locked: bool
    actor_lane_validation: dict[str, Any]
    ledger: dict[str, Any]
    structured_output: dict[str, Any]
    narrator_authority: dict[str, Any]
    npc_authority: dict[str, Any]
    capability_selection: dict[str, Any] = field(default_factory=dict)
    cap_violation: dict[str, Any] = field(default_factory=dict)
    cap_missing_first: Any = None
    validations: dict[str, Any] = field(default_factory=dict)
    failures: dict[str, Any] = field(default_factory=dict)
