from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict


class RuntimeTurnState(TypedDict, total=False):
    session_id: str
    module_id: str
    current_scene_id: str
    player_input: str
    trace_id: str
    host_versions: dict[str, Any]
    host_experience_template: dict[str, Any]
    force_experiment_preview: bool
    # Bounded prior-thread snapshot from story runtime (no evidence lists / no history blobs).
    active_narrative_threads: list[dict[str, Any]]
    thread_pressure_summary: str
    interpreted_input: dict[str, Any]
    interpreted_move: dict[str, Any]
    task_type: str
    routing: dict[str, Any]
    selected_provider: str
    selected_timeout: float
    retrieval: dict[str, Any]
    context_text: str
    model_prompt: str
    generation: dict[str, Any]
    fallback_needed: bool
    graph_diagnostics: dict[str, Any]
    nodes_executed: list[str]
    node_outcomes: dict[str, str]
    graph_errors: list[str]
    capability_audit: list[dict[str, Any]]
    # Canonical turn field groups (CANONICAL_TURN_CONTRACT_GOC.md §4–§5).
    goc_slice_active: bool
    goc_canonical_yaml: dict[str, Any]
    goc_yaml_slice: dict[str, Any]
    prior_continuity_impacts: list[dict[str, Any]]
    prior_dramatic_signature: dict[str, str]
    scene_assessment: dict[str, Any]
    selected_responder_set: list[dict[str, Any]]
    selected_scene_function: str
    pacing_mode: str
    silence_brevity_decision: dict[str, Any]
    proposed_state_effects: list[dict[str, Any]]
    validation_outcome: dict[str, Any]
    committed_result: dict[str, Any]
    visible_output_bundle: dict[str, Any]
    continuity_impacts: list[dict[str, Any]]
    visibility_class_markers: list[str]
    failure_markers: list[dict[str, Any]]
    fallback_markers: list[dict[str, Any]]
    diagnostics_refs: list[dict[str, Any]]
    experiment_preview: bool
    transition_pattern: str
    # Turn execution basis (host/session may supply; see CANONICAL_TURN_CONTRACT_GOC.md G3 projection).
    turn_id: str
    turn_number: int
    turn_timestamp_iso: str
    turn_initiator_type: str
    turn_input_class: str
    turn_execution_mode: str
    # Bounded semantic planner state (phases 0–4); advisory until validation/commit.
    semantic_move_record: dict[str, Any]
    social_state_record: dict[str, Any]
    character_mind_records: list[dict[str, Any]]
    scene_plan_record: dict[str, Any]
    dramatic_effect_outcome: dict[str, Any]


STORY_RUNTIME_ROUTING_POLICY_ID = "story_runtime_core.RoutingPolicy"
STORY_RUNTIME_ROUTING_POLICY_VERSION = "registry_default_v1"
