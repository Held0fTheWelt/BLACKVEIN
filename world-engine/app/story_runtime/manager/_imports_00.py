from __future__ import annotations

import logging
import os
import re
import threading
import copy
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
import yaml
from ai_stack.actor_tracking import (
    W5Snapshot,
    build_w5_admin_actor_view,
    build_w5_admin_conflicts_view,
    build_w5_admin_narrator_projection_preview,
    build_w5_admin_npc_projection_preview,
    build_w5_admin_snapshot_view,
    build_w5_admin_validation_view,
    build_w5_langfuse_metadata,
    build_w5_runtime_metadata,
    build_w5_projection_for_narrator,
    build_w5_projection_for_player_shell,
    extract_w5_snapshot_from_committed_event,
)
from story_runtime_core import ModelRegistry, RoutingPolicy, interpret_player_input
from ai_stack.language_io.language_adapter import (
    build_player_attributed_visible_line,
    greeting_imperative_addressee_fragment,
    greeting_imperative_visible_pair,
    resolve_string,
)
from story_runtime_core.player_input_intent_contract import (
    FORBIDDEN_NON_SPEECH_ACTION_SEMANTIC_MOVES,
    INTENT_CONTRACT_VERSION,
    PLAYER_INPUT_KINDS,
    is_perception_like_player_input_kind,
    is_question_punctuation_probe_guarded,
    is_speech_like_player_input_kind,
    player_input_kind_family,
)
from story_runtime_core.branching import (
    BRANCHING_TIMELINE_DEFAULT_MAX_ACTIVE_TREES,
    BRANCHING_TIMELINE_EVENT_NODE_SELECTED,
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED,
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_CONFLICT,
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_STARTED,
    BRANCHING_TIMELINE_EVENT_TREE_BECAME_STALE,
    BRANCHING_TIMELINE_EVENT_TREE_CREATED,
    BRANCHING_TIMELINE_EVENT_TREE_EXPIRED,
    BRANCHING_TIMELINE_SCOPE_ACTIVE,
    BRANCHING_TREE_STATUS_COMMITTED,
    BRANCHING_TREE_STATUS_EXPIRED,
    BRANCHING_TREE_STATUS_NOT_APPLICABLE,
    BRANCHING_TREE_STATUS_SIMULATED,
    BRANCHING_TREE_STATUS_STALE,
    append_simulation_node,
    branch_tree_is_fresh,
    branch_tree_path_nodes,
    clamp_simulation_limits,
    find_branch_tree_node,
    finalize_simulation_tree,
    forecast_has_options,
    make_branch_tree_record,
    make_simulated_turn_node,
    make_simulation_tree,
    mark_branch_tree_committed,
    mark_branch_tree_expired,
    mark_branch_tree_stale,
    simulated_input_for_branch_option,
    build_branching_forecast,
    append_branch_timeline_event,
    archive_branch_timeline,
    compact_branch_timeline,
    make_branch_timeline_event,
    make_branch_timeline_record,
    stable_branch_timeline_id,
)
from story_runtime_core.callbacks import (
    build_graph_callback_web_export,
    build_callback_web_record,
    stable_callback_web_id,
)
from story_runtime_core.langfuse_tracing_environment import local_langfuse_evidence_metadata
from story_runtime_core.consequences import (
    build_consequence_cascade_record,
    build_graph_consequence_cascade_export,
    stable_consequence_cascade_id,
)
from story_runtime_core.recovery import (
    NO_DEAD_END_RECOVERY_SCHEMA_VERSION,
    build_no_dead_end_recovery_record,
)
from story_runtime_core.adapters import BaseModelAdapter, build_default_model_adapters
from story_runtime_core.model_registry import build_default_registry
from ai_stack import (
    RuntimeTurnGraphExecutor,
    build_runtime_retriever,
    create_default_capability_registry,
)
from ai_stack.prompt_store import configure_prompt_bundle, render_prompt
from ai_stack.rag.rag_retrieval_dtos import retrieval_config_from_governed
from ai_stack.quality_lab.runtime_quality_semantics import canonical_quality_class
from ai_stack.story_runtime.runtime_aspect_ledger import (
    ASPECT_ACTION_RESOLUTION,
    ASPECT_BEAT,
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_CALLBACK_WEB,
    ASPECT_COMMIT,
    ASPECT_CONSEQUENCE_CASCADE,
    ASPECT_DRAMATIC_IRONY,
    ASPECT_EXPECTATION_VARIATION,
    ASPECT_GENRE_AWARENESS,
    ASPECT_HIERARCHICAL_MEMORY,
    ASPECT_IMPROVISATIONAL_COHERENCE,
    ASPECT_INFORMATION_DISCLOSURE,
    ASPECT_INPUT,
    ASPECT_NARRATIVE_ASPECT,
    ASPECT_NARRATIVE_MOMENTUM,
    ASPECT_NARRATOR_AUTHORITY,
    ASPECT_NO_DEAD_END_RECOVERY,
    ASPECT_NPC_AGENCY,
    ASPECT_NPC_AUTHORITY,
    ASPECT_PACING_RHYTHM,
    ASPECT_SCENE_ENERGY,
    ASPECT_SENSORY_CONTEXT,
    ASPECT_SOCIAL_PRESSURE,
    ASPECT_SYMBOLIC_OBJECT_RESONANCE,
    ASPECT_TEMPORAL_CONTROL,
    ASPECT_TONAL_CONSISTENCY,
    ASPECT_VALIDATION,
    ASPECT_VOICE_CONSISTENCY,
    ASPECT_VISIBLE_PROJECTION,
    aspect_score_metadata,
    ensure_runtime_aspect_ledger,
    initialize_runtime_aspect_ledger,
    make_aspect_record,
    normalize_runtime_aspect_ledger,
    set_aspect_record,
)
from ai_stack.contracts.callback_web_contracts import (
    callback_web_aspect_blocks,
    callback_web_bounds_from_policy,
    callback_web_policy_from_module_runtime,
    normalize_callback_web_policy,
    validate_callback_web_record,
)
from ai_stack.contracts.consequence_cascade_contracts import (
    consequence_cascade_aspect_blocks,
    consequence_cascade_bounds_from_policy,
    consequence_cascade_policy_from_module_runtime,
    normalize_consequence_cascade_policy,
    validate_consequence_cascade_record,
)
from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.contracts.environment_state_contracts import (
    build_environment_model,
    normalize_environment_state,
)
from ai_stack.contracts.hierarchical_memory_contracts import (
    build_hierarchical_memory_write,
    empty_hierarchical_memory_snapshot,
    merge_hierarchical_memory_snapshot,
    normalize_hierarchical_memory_snapshot,
    project_hierarchical_memory_context,
)
from ai_stack.contracts.narrative_aspect_contracts import validate_narrative_aspects
from ai_stack.contracts.dramatic_capability_contracts import (
    NPC_ACTION_GESTURE_OPTIONAL,
    NPC_DIRECT_ANSWER_ALLOWED,
    NPC_SOCIAL_REACTION_OPTIONAL,
    NARRATOR_ACTION_CONSEQUENCE_DESCRIBE,
    NARRATOR_LOCATION_TRANSITION_DESCRIBE,
    NARRATOR_OBJECT_STATE_DESCRIBE,
    NARRATOR_OPENING_EVENT_REALIZE,
    NARRATOR_PERCEPTION_RESULT_DESCRIBE,
    PLAYER_ACTION_REQUEST,
    PLAYER_MOVEMENT_REQUEST,
    PLAYER_OBJECT_INTERACTION_REQUEST,
    PLAYER_PERCEPTION_REQUEST,
    PLAYER_SPEECH_REQUEST,
)
from ai_stack.contracts.visible_origin_contracts import (
    EVIDENCE_REQUIRED,
    EVIDENCE_SUPPORTING,
    REQUIRED_VISIBLE_ORIGIN_KEYS,
    block_has_required_origin,
    preserve_folded_origin_metadata,
    visible_origin_from_block,
)
from ai_stack.contracts.runtime_turn_contracts import (
    DEGRADATION_SIGNAL_ACTOR_LANES_VALIDATION_GATED,
    DEGRADATION_SIGNAL_DEGRADED_COMMIT,
    DEGRADATION_SIGNAL_FALLBACK_USED,
    DEGRADATION_SIGNAL_NON_FACTUAL_STAGING,
    DEGRADATION_SIGNAL_PROSE_ONLY_RECOVERY,
    DEGRADATION_SIGNAL_RETRY_EXHAUSTED,
    DEGRADATION_SIGNAL_THIN_PROSE_OVERRIDE,
    DEGRADATION_SIGNAL_VALUES,
    DEGRADATION_SIGNAL_WEAK_SIGNAL_ACCEPTED,
    QUALITY_CLASS_DEGRADED,
    QUALITY_CLASS_FAILED,
    QUALITY_CLASS_HEALTHY,
    QUALITY_CLASS_VALUES,
)
from ai_stack.story_runtime.story_runtime_playability import is_hard_boundary_failure
from ai_stack.live_dramatic_scene_simulator import (
    LDSSInput,
    build_ldss_input_from_session,
    build_scene_turn_envelope_v2,
    run_ldss,
)
from ai_stack.telemetry.diagnostics_envelope import (
    DegradationEvent,
    build_diagnostics_envelope,
    build_narrative_gov_summary,
)
from ai_stack.telemetry.runtime_cost_attribution import (
    aggregate_phase_costs,
    build_deterministic_phase_cost,
    build_mock_phase_cost,
    build_provider_usage_phase_cost,
    build_unavailable_phase_cost,
)
from ai_stack.story_runtime.narrative import NarrativeRuntimeAgent, NarrativeRuntimeAgentInput, NarrativeEventKind
from ai_stack.story_runtime.god_of_carnage.god_of_carnage_frozen_vocabulary import canonicalize_goc_actor_id, expand_goc_actor_id_aliases
from ai_stack.story_runtime.god_of_carnage.god_of_carnage_yaml_authority import goc_actor_identity
from ai_stack.story_runtime.npc_agency.god_of_carnage_npc_transcript_projection import (
    goc_transcript_policy_flags,
    split_merged_goc_actor_line_segments,
)
from ai_stack.story_runtime.god_of_carnage.god_of_carnage_opening_transition import (
    compute_opening_transition_from_scene_blocks,
    polish_first_opening_actor_block,
    role_display_name as _role_display_name,
)

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
