"""Story runtime manager package.

Exposes the manager package boundary for session lifecycle, turn execution, visible projection, persistence, and legacy Langfuse support modules.
"""
from __future__ import annotations

from importlib import import_module

_MODULE_NAMES = ['._deps', '.content_language', '.scripted_speech_contracts', '.recoverable_aspect_ledger', '.no_dead_end_recovery', '.session_payloads', '.session_memory_policies', '.visible_projection_opening', '.visible_projection_goc_actor_split', '.visible_projection_backfill', '.actor_turn_summary', '.model_costs_and_path_core', '.langfuse_status_and_degradation', '.degradation_and_turn_blocks', '.scene_block_summary', '.live_scene_turn_envelope', '.player_input_scene_blocks', '.story_window_entries', '.prior_story_state', '.prior_narrative_context', '.committed_dramatic_context', '.dramatic_context_authority', '.ldss_narrative_queue', '.legacy_build_langfuse_path_summary', '.legacy_emit_langfuse_evidence_observations', '.legacy_emit_langfuse_path_spans', '.legacy_emit_langfuse_runtime_aspect_observability', '.legacy_live_scene_blocks_from_visible_bundle', '.legacy_record_visible_projection_aspect', '.manager_init_and_persistence', '.runtime_config', '.session_loop_governance', '.opening_prompt_and_narrator_candidates', '.narrator_output_prompts', '.narrator_output_realization', '.souffleuse_output_realization', '.opening_fallback_observability', '.actor_tracking.w5_projection', '.scripted_continuation', '.opening_execution', '.session_lifecycle', '.branching_api', '.callback_and_cascade_api', '.cascade_refresh', '.branch_selection', '.branch_timeline', '.branch_simulation', '.turn_execution', '.player_visible_persistence', '.recoverable_rejection_and_sessions', '.session_state_api', '.thin_path_snapshot_api', '.diagnostics_api', '._legacy_methods', '.runtime_manager']
_LOADED_MODULES = [import_module(name, __name__) for name in _MODULE_NAMES]

for _module in _LOADED_MODULES:
    for _name in getattr(_module, "__all__", ()): 
        globals()[_name] = getattr(_module, _name)

_EXPORTS = {
    name: value
    for name, value in globals().items()
    if not name.startswith("__") and name not in {"import_module", "annotations"}
}
for _module in _LOADED_MODULES:
    _module.__dict__.update(_EXPORTS)

__all__ = sorted(
    name
    for name in _EXPORTS
    if name not in {"_MODULE_NAMES", "_LOADED_MODULES", "_EXPORTS"}
)
