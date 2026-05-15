"""
``ai_stack/langgraph_runtime_state.py`` — expand purpose, primary
entrypoints, and invariants for maintainers.
"""
from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict


class RuntimeTurnState(TypedDict, total=False):
    """``RuntimeTurnState`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    session_id: str
    module_id: str
    current_scene_id: str
    player_input: str
    trace_id: str
    host_versions: dict[str, Any]
    host_experience_template: dict[str, Any]
    # Neutral module policy loaded from content/config. Runtime intelligence
    # gates consume this shape rather than branching on module-specific names.
    module_runtime_policy: dict[str, Any]
    force_experiment_preview: bool
    # Bounded prior-thread snapshot from story runtime (no evidence lists / no history blobs).
    active_narrative_threads: list[dict[str, Any]]
    thread_pressure_summary: str
    interpreted_input: dict[str, Any]
    interpreted_move: dict[str, Any]
    player_action_frame: dict[str, Any]
    affordance_resolution: dict[str, Any]
    response_plan: dict[str, Any]
    scene_affordance_model: dict[str, Any]
    environment_model: dict[str, Any]
    environment_state: dict[str, Any]
    environment_transition: dict[str, Any]
    task_type: str
    routing: dict[str, Any]
    selected_provider: str
    selected_timeout: float
    retrieval: dict[str, Any]
    context_text: str
    context_synthesis_bundle: dict[str, Any]
    context_synthesis_diagnostics: dict[str, Any]
    context_synthesis_retry_history: list[dict[str, Any]]
    validation_feedback: dict[str, Any]
    model_prompt: str
    dramatic_generation_packet: dict[str, Any]
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
    opening_scene_sequence: dict[str, Any]
    hard_forbidden_rules: dict[str, Any]
    goc_runtime_knowledge_contract: dict[str, Any]
    # GOC-KNOWLEDGE-RUNTIME-INTEGRATION P0.1: structured knowledge surfaces
    # exposed to scene director, narrator packet, and diagnostics so they
    # influence runtime behaviour without re-loading YAML in each node.
    apartment_layout: dict[str, Any]
    apartment_objects: dict[str, Any]
    premise_and_backstory: dict[str, Any]
    actor_pressure_profiles: dict[str, Any]
    phase_beat_policy: dict[str, Any]
    narrator_sensory_palette: dict[str, Any]
    scene_affordances: dict[str, Any]
    knowledge_runtime_loaded: dict[str, bool]
    prior_continuity_impacts: list[dict[str, Any]]
    prior_dramatic_signature: dict[str, str]
    prior_social_state_record: dict[str, Any]
    prior_narrative_thread_state: dict[str, Any]
    prior_callback_web_state: dict[str, Any]
    prior_consequence_cascade_state: dict[str, Any]
    prior_temporal_control_state: dict[str, Any]
    prior_expectation_variation_state: dict[str, Any]
    prior_pacing_rhythm_state: dict[str, Any]
    prior_social_pressure_state: dict[str, Any]
    prior_relationship_state_record: dict[str, Any]
    prior_planner_truth: dict[str, Any]
    # Bounded hierarchical memory context derived from canonical committed turns.
    hierarchical_memory_context: dict[str, Any]
    scene_assessment: dict[str, Any]
    selected_responder_set: list[dict[str, Any]]
    selected_scene_function: str
    pacing_mode: str
    silence_brevity_decision: dict[str, Any]
    scene_energy_target: dict[str, Any]
    scene_energy_transition: dict[str, Any]
    scene_energy_validation: dict[str, Any]
    pacing_rhythm_state: dict[str, Any]
    pacing_rhythm_target: dict[str, Any]
    pacing_rhythm_validation: dict[str, Any]
    temporal_control_state: dict[str, Any]
    temporal_control_target: dict[str, Any]
    temporal_control_validation: dict[str, Any]
    sensory_context_state: dict[str, Any]
    sensory_context_target: dict[str, Any]
    sensory_context_validation: dict[str, Any]
    improvisational_coherence_target: dict[str, Any]
    improvisational_coherence_validation: dict[str, Any]
    social_pressure_state: dict[str, Any]
    social_pressure_target: dict[str, Any]
    social_pressure_validation: dict[str, Any]
    relationship_state_record: dict[str, Any]
    relationship_dynamics_target: dict[str, Any]
    relationship_dynamics_context: dict[str, Any]
    relationship_state_validation: dict[str, Any]
    information_disclosure_target: dict[str, Any]
    information_disclosure_validation: dict[str, Any]
    expectation_variation_state: dict[str, Any]
    expectation_variation_target: dict[str, Any]
    expectation_variation_validation: dict[str, Any]
    proposed_state_effects: list[dict[str, Any]]
    candidate_deltas: list[dict[str, Any]]
    state_delta_boundary: dict[str, Any]
    validation_outcome: dict[str, Any]
    committed_result: dict[str, Any]
    visible_output_bundle: dict[str, Any]
    dramatic_context_summary: dict[str, Any]
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
    live_player_truth_surface: bool
    session_output_language: str
    # MVP2 actor-lane enforcement context: human_actor_id + ai_forbidden_actor_ids.
    # Populated by the host at turn start; consumed by validate_seam before commit.
    actor_lane_context: dict[str, Any]
    # Bounded semantic planner state (phases 0–4); advisory until validation/commit.
    semantic_move_record: dict[str, Any]
    social_state_record: dict[str, Any]
    character_mind_records: list[dict[str, Any]]
    character_voice_profiles: list[dict[str, Any]]
    voice_consistency_validation: dict[str, Any]
    npc_agency_simulation: dict[str, Any]
    npc_initiative_validation: dict[str, Any]
    dramatic_irony_record: dict[str, Any]
    dramatic_irony_validation: dict[str, Any]
    meta_narrative_awareness_target: dict[str, Any]
    meta_narrative_awareness_validation: dict[str, Any]
    scene_plan_record: dict[str, Any]
    dramatic_effect_outcome: dict[str, Any]
    # Model-generated structured behavior outputs; populated by the
    # ``proposal_normalize`` graph node from
    # ``generation["metadata"]["structured_output"]``.
    responder_id: str
    primary_responder_id: str
    secondary_responder_ids: list[str]
    spoken_lines: list[dict[str, Any] | str]
    action_lines: list[dict[str, Any] | str]
    initiative_events: list[dict[str, Any]]
    state_effects: list[dict[str, Any]]
    function_type: str
    emotional_shift: dict[str, Any]
    social_outcome: str
    dramatic_direction: str
    # Reconciliation outcome recording whether the model-proposed responders
    # matched the director's selected_responder_set and how many out-of-scope
    # actors were dropped. Populated by the validate_seam node.
    responder_reconciliation: dict[str, Any]
    actor_lane_validation: dict[str, Any]
    quality_class: str
    degradation_signals: list[str]
    degradation_summary: str
    # PRIMARY-PARSER-EVIDENCE-01: captured by invoke_model node before any self-correction
    # or LDSS overwrite can erase the primary attempt's parser error and raw output.
    primary_attempt_evidence: dict[str, Any]
    # PLAYER-LOCAL-CONTEXT-AND-NARRATOR-CONSEQUENCE-01: spatial context after committed action.
    player_local_context: dict[str, Any]
    local_context_transition: dict[str, Any]
    narrator_consequence_plan: dict[str, Any]
    # ADR-0036: normative language for all model-visible turn text (host-injected).
    session_output_language: str
    # Effective ``story_runtime_experience`` slice from governed runtime config (operator/admin).
    story_runtime_experience: dict[str, Any]
    validation_execution_mode: str
    # HUMAN-INPUT-ATTRIBUTION-01: committed-turn diagnostics (host/world-engine may attach).
    human_input_attribution: dict[str, Any]
    # RuntimeAspectLedger is backend/world-engine-owned authority evidence.
    # Authority-relevant records are consumed by validation/commit before
    # diagnostics or Langfuse emission.
    turn_aspect_ledger: dict[str, Any]


STORY_RUNTIME_ROUTING_POLICY_ID = "story_runtime_core.RoutingPolicy"
STORY_RUNTIME_ROUTING_POLICY_VERSION = "registry_default_v1"
