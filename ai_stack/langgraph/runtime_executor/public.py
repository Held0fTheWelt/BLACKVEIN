"""Runtime executor assembled from named source segments.

This module is the transitional loader for the DS-010 runtime-executor split.
The physical files are kept below 200 lines and grouped by responsibility so
the next pass can promote each group into ordinary Python helper modules.
"""
from __future__ import annotations

from importlib import import_module
import linecache

_GROUPS = {
    "imports": (
        "executor_imports_core",
        "executor_imports_narrative",
    ),
    "input_and_actor_lanes": (
        "semantic_input_translation",
        "actor_lane_scope",
        "actor_lane_structured_lines",
        "actor_lane_scene_function",
    ),
    "runtime_aspect_records": (
        "authority_aspect_records",
        "authority_voice_profiles",
        "runtime_dispatch_and_voice_aspects",
        "scene_energy_pacing_aspects",
        "social_pressure_aspect_records",
        "information_disclosure_aspect_records",
        "npc_agency_aspect_records",
    ),
    "retrieval_and_projection": (
        "retrieval_actor_keys",
        "retrieval_continuity_query",
        "retrieval_adapter_invocation",
        "reaction_order_governance",
        "npc_agency_projection",
        "relationship_dynamics_context",
    ),
    "dramatic_packet": (
        "dramatic_generation_packet_opening",
        "dramatic_generation_packet_context",
        "dramatic_generation_packet_authority",
        "dramatic_generation_packet_payload",
    ),
    "director_context": (
        "director_routing_requirements",
        "director_location_completion",
        "director_w5_location_projection",
    ),
    "executor_shell": (
        "executor_graph_build",
        "executor_run_prepare",
        "executor_run_finish",
    ),
    "executor_input_and_action": (
        "executor_translation_adapter",
        "executor_input_interpretation_start",
        "executor_input_interpretation_semantics",
        "executor_input_interpretation_finish",
        "executor_meta_control",
        "executor_retrieval_context",
        "executor_action_resolution_start",
        "executor_action_resolution_commit",
        "executor_realization_capabilities",
    ),
    "executor_director": (
        "executor_goc_canonical_content",
        "executor_scene_assessment",
        "executor_director_selection_opening",
        "executor_director_selection_context",
        "executor_director_selection_parameters",
        "executor_director_selection_finish",
    ),
    "executor_aspect_derivation": (
        "executor_scene_energy_temporal_derivation",
        "executor_social_tonal_relationship_derivation",
        "executor_symbolic_meta_genre_derivation",
        "executor_sensory_improv_info_derivation",
        "executor_irony_expectation_momentum_derivation",
        "executor_context_synthesis_derivation",
    ),
    "executor_model_pipeline": (
        "executor_model_context_prompt",
        "executor_model_context_retrieval",
        "executor_model_context_validation",
        "executor_model_context_payload",
        "executor_model_routing_invocation",
        "executor_model_fallback",
        "executor_generation_self_correction",
        "executor_generation_normalization",
    ),
    "executor_commit_render": (
        "executor_validation_commit",
        "executor_commit_render_start",
        "executor_visible_render",
        "executor_package_output",
    ),
}

_source_lines: list[str] = []
for _parts in _GROUPS.values():
    for _part in _parts:
        _source_lines.extend(import_module(f"{__package__}.{_part}").SOURCE_LINES)

_source = "".join(_source_lines)
linecache.cache["ai_stack/langgraph/langgraph_runtime_executor.py"] = (
    len(_source),
    None,
    _source.splitlines(keepends=True),
    "ai_stack/langgraph/langgraph_runtime_executor.py",
)
exec(compile(_source, "ai_stack/langgraph/langgraph_runtime_executor.py", "exec"), globals())

del import_module, linecache, _part, _parts, _source, _source_lines
