"""Runtime executor assembled from small logical source segments."""
from __future__ import annotations

from importlib import import_module
import linecache

_PARTS = [
    'runtime_executor_imports_01',
    'runtime_executor_imports_02',
    'semantic_input_translation_01',
    'actor_lane_reconciliation_01',
    'actor_lane_reconciliation_02',
    'actor_lane_reconciliation_03',
    'authority_aspects_01',
    'authority_aspects_02',
    'runtime_aspect_records_voice_scene_01',
    'runtime_aspect_records_voice_scene_02',
    'runtime_aspect_records_social_npc_01',
    'runtime_aspect_records_social_npc_02',
    'runtime_aspect_records_social_npc_03',
    'retrieval_continuity_01',
    'retrieval_continuity_02',
    'retrieval_continuity_03',
    'reaction_order_and_npc_projection_01',
    'reaction_order_and_npc_projection_02',
    'dramatic_packet_context_01',
    'dramatic_generation_packet_01',
    'dramatic_generation_packet_02',
    'dramatic_generation_packet_03',
    'dramatic_generation_packet_04',
    'director_context_and_locations_01',
    'director_context_and_locations_02',
    'director_context_and_locations_03',
    'runtime_executor_graph_01',
    'runtime_executor_run_01',
    'runtime_executor_run_02',
    'runtime_executor_translation_01',
    'runtime_executor_translation_02',
    'runtime_executor_translation_03',
    'runtime_executor_translation_04',
    'runtime_executor_context_action_01',
    'runtime_executor_context_action_02',
    'runtime_executor_context_action_03',
    'runtime_executor_context_action_04',
    'runtime_executor_context_action_05',
    'runtime_executor_director_01',
    'runtime_executor_director_02',
    'runtime_executor_director_03',
    'runtime_executor_director_04',
    'runtime_executor_director_05',
    'runtime_executor_director_06',
    'runtime_executor_aspect_derivation_01',
    'runtime_executor_aspect_derivation_02',
    'runtime_executor_aspect_derivation_03',
    'runtime_executor_aspect_derivation_04',
    'runtime_executor_aspect_derivation_05',
    'runtime_executor_aspect_derivation_06',
    'runtime_executor_model_context_01',
    'runtime_executor_model_context_02',
    'runtime_executor_model_context_03',
    'runtime_executor_model_context_04',
    'runtime_executor_model_pipeline_01',
    'runtime_executor_model_pipeline_02',
    'runtime_executor_model_pipeline_03',
    'runtime_executor_model_pipeline_04',
    'runtime_executor_commit_render_01',
    'runtime_executor_commit_render_02',
    'runtime_executor_commit_render_03',
    'runtime_executor_commit_render_04',
]

_source_lines: list[str] = []
for _part in _PARTS:
    _source_lines.extend(import_module(f"{__package__}.{_part}").SOURCE_LINES)

_source = "".join(_source_lines)
linecache.cache["ai_stack/langgraph/langgraph_runtime_executor.py"] = (
    len(_source),
    None,
    _source.splitlines(keepends=True),
    "ai_stack/langgraph/langgraph_runtime_executor.py",
)
exec(compile(_source, "ai_stack/langgraph/langgraph_runtime_executor.py", "exec"), globals())

del import_module, linecache, _part, _source, _source_lines
