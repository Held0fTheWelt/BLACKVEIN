# Runtime Executor Split

This package is the DS-010 staging area for
`ai_stack.langgraph.langgraph_runtime_executor`.

The original executor mixed input translation, actor-lane governance,
retrieval, dramatic packet construction, director selection, model routing,
validation, commit, render, and output packaging in one file. The current
split keeps the public import surface stable while making those responsibilities
visible as named source groups. Every file in this package is kept below 200
physical lines.

## Transitional Loader

`public.py` assembles the legacy executor source from responsibility-specific
`SOURCE_LINES` chunks and publishes the same symbols that callers already import from
`ai_stack.langgraph.langgraph_runtime_executor`.

This is deliberately transitional. It gives Despaghettify a low-risk cut point:
tests keep exercising the old runtime behaviour, while the next pass can
promote each group into normal Python modules with real functions, imports, and
unit seams. The compatibility facade
`../langgraph_runtime_executor.py` points at `public.py`.

Each segment file starts with a module docstring that names its responsibility.
Those docstrings are not generation markers; they are the local reading guide
for the slice until the next pass replaces the `SOURCE_LINES` chunk with normal
module code.

## Responsibility Groups

| Group | Files | What happens there |
|-------|-------|--------------------|
| Imports | `executor_imports_core.py`, `executor_imports_narrative.py` | Original dependency surface needed by the assembled executor. |
| Input and actor lanes | `semantic_input_translation.py`, `actor_lane_scope.py`, `actor_lane_structured_lines.py`, `actor_lane_scene_function.py` | Player input normalization, semantic translation payloads, responder reconciliation, actor legality, and scene-function compatibility checks. |
| Runtime aspect records | `authority_aspect_records.py`, `authority_voice_profiles.py`, `runtime_dispatch_and_voice_aspects.py`, `scene_energy_pacing_aspects.py`, `social_pressure_aspect_records.py`, `information_disclosure_aspect_records.py`, `npc_agency_aspect_records.py` | Aspect-record builders for authority, voice, dispatch, pacing, pressure, disclosure, and NPC agency surfaces. |
| Retrieval and projection | `retrieval_actor_keys.py`, `retrieval_continuity_query.py`, `retrieval_adapter_invocation.py`, `reaction_order_governance.py`, `npc_agency_projection.py`, `relationship_dynamics_context.py` | Active actor derivation, retrieval continuity context, adapter invocation, reaction-order checks, NPC plan projection, and relationship context compaction. |
| Dramatic packet | `dramatic_generation_packet_opening.py`, `dramatic_generation_packet_context.py`, `dramatic_generation_packet_authority.py`, `dramatic_generation_packet_payload.py` | The former `_build_dramatic_generation_packet` flow, split by opening state, context assembly, authority constraints, and final packet payload. |
| Director context | `director_routing_requirements.py`, `director_location_completion.py`, `director_w5_location_projection.py` | Drama-aware routing requirements, destination context, actor-location completion, and optional W5 projection support. |
| Executor shell | `executor_graph_build.py`, `executor_run_prepare.py`, `executor_run_finish.py` | `RuntimeTurnGraphExecutor` initialization, graph wiring, run preparation, and run completion. |
| Executor input and action | `executor_translation_adapter.py`, `executor_input_interpretation_start.py`, `executor_input_interpretation_semantics.py`, `executor_input_interpretation_finish.py`, `executor_meta_control.py`, `executor_retrieval_context.py`, `executor_action_resolution_start.py`, `executor_action_resolution_commit.py`, `executor_realization_capabilities.py` | Class methods for translating player input, interpreting intent, handling meta-control turns, retrieving context, resolving player action, and realizing capabilities. |
| Executor director | `executor_goc_canonical_content.py`, `executor_scene_assessment.py`, `executor_director_selection_opening.py`, `executor_director_selection_context.py`, `executor_director_selection_parameters.py`, `executor_director_selection_finish.py` | Canonical content resolution, scene assessment, and director dramatic-parameter selection. |
| Executor aspect derivation | `executor_scene_energy_temporal_derivation.py`, `executor_social_tonal_relationship_derivation.py`, `executor_symbolic_meta_genre_derivation.py`, `executor_sensory_improv_info_derivation.py`, `executor_irony_expectation_momentum_derivation.py`, `executor_context_synthesis_derivation.py` | Runtime derivation methods for narrative aspects and context synthesis. |
| Executor model pipeline | `executor_model_context_prompt.py`, `executor_model_context_retrieval.py`, `executor_model_context_validation.py`, `executor_model_context_payload.py`, `executor_model_routing_invocation.py`, `executor_model_fallback.py`, `executor_generation_self_correction.py`, `executor_generation_normalization.py` | Model-context assembly, routing, invocation, fallback, self-correction, and proposal normalization. |
| Executor commit/render | `executor_validation_commit.py`, `executor_commit_render_start.py`, `executor_visible_render.py`, `executor_package_output.py` | Validation seam delegation, commit seam, visible render, and output package handoff. |

## Next Despaghettify Pass

The next DS-010 pass should replace `SOURCE_LINES` chunks group by group:

1. Move top-level helpers into ordinary modules first, starting with semantic
   input, actor lanes, retrieval, dramatic packet, and director context.
2. Convert large executor methods into mixins or collaborators only when the
   method boundary already matches a responsibility group above.
3. Keep `langgraph_runtime_executor.py` as the compatibility import until all
   direct imports in tests and runtime code point at stable module names.
4. Re-run Docify after each promoted group so explanations live beside the new
   code rather than only in this README.
