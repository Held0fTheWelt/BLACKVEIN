"""Legacy source manifest.

Lists ordered legacy source chunks and their target methods so the compatibility loader can assemble them deterministically.
"""
from __future__ import annotations

SOURCE_CHUNKS = {
    '_build_langfuse_path_summary': ['_build_langfuse_path_summary_000', '_build_langfuse_path_summary_001', '_build_langfuse_path_summary_002', '_build_langfuse_path_summary_003'],
    '_emit_langfuse_evidence_observations': ['_emit_langfuse_evidence_observations_000', '_emit_langfuse_evidence_observations_001', '_emit_langfuse_evidence_observations_002'],
    '_emit_langfuse_path_spans': ['_emit_langfuse_path_spans_000', '_emit_langfuse_path_spans_001'],
    '_emit_langfuse_runtime_aspect_observability': ['_emit_langfuse_runtime_aspect_observability_000', '_emit_langfuse_runtime_aspect_observability_001', '_emit_langfuse_runtime_aspect_observability_002', '_emit_langfuse_runtime_aspect_observability_003', '_emit_langfuse_runtime_aspect_observability_004', '_emit_langfuse_runtime_aspect_observability_005', '_emit_langfuse_runtime_aspect_observability_006'],
    '_live_scene_blocks_from_visible_bundle': ['_live_scene_blocks_from_visible_bundle_000', '_live_scene_blocks_from_visible_bundle_001'],
    '_record_visible_projection_aspect': ['_record_visible_projection_aspect_000', '_record_visible_projection_aspect_001', '_record_visible_projection_aspect_002'],
    'method:_build_narrator_path_opening_state': ['method___build_narrator_path_opening_state_000', 'method___build_narrator_path_opening_state_001', 'method___build_narrator_path_opening_state_002'],
    'method:_finalize_committed_turn': ['method___finalize_committed_turn_000', 'method___finalize_committed_turn_001', 'method___finalize_committed_turn_002', 'method___finalize_committed_turn_003', 'method___finalize_committed_turn_004', 'method___finalize_committed_turn_005'],
}

__all__ = ["SOURCE_CHUNKS"]
