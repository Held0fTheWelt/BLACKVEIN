"""Langfuse verify source segment: adr0041_runtime_evidence.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
    return "not_applicable"


def _sif(ev: dict[str, Any], field: str, value: Any) -> None:
    """Set ev[field] = value only if the field is currently None."""
    if value is not None and ev.get(field) is None:
        ev[field] = value


def _extract_normalized_wos_evidence(
    raw_trace: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract WoS evidence from a Langfuse trace using a four-source priority chain.

    Priority (first non-None wins per field):
      1. trace.output.path_summary (or trace.output if it IS the path_summary)
      2. story.graph.path_summary observation (output → input → metadata)
      3. Score metadata (score_metadata_base carries player-role, adapter, quality)
      4. Turn span metadata (backend.turn.execute / world-engine.turn.execute)
      5. trace.metadata (top-level, usually only trace_origin/execution_tier)
      6. world-engine.session.create statusMessage (key=value fallback)

    Returns (evidence_dict, evidence_sources_dict).
    """
    obs_list = _get_observations(raw_trace)

    ev: dict[str, Any] = {
        "trace_id": str(raw_trace.get("id") or raw_trace.get("trace_id") or "").strip(),
        "session_id": None,
        "selected_player_role": None,
        "human_actor_id": None,
        "npc_actor_ids": [],
        "trace_origin": None,
        "execution_tier": None,
        "canonical_player_flow": None,
        "final_adapter": None,
        "quality_class": None,
        "fallback_reason": None,
    }

    path_summary_source = "missing"
    score_source = "missing"
    status_message_fallback_used = False

    _PS_FIELDS = {
        "session_id", "selected_player_role", "human_actor_id", "npc_actor_ids",
        "canonical_turn_id", "runtime_profile_id", "turn_aspect_ledger_present",
        "trace_origin", "execution_tier", "canonical_player_flow",
        "final_adapter", "quality_class", "fallback_reason",
        "first_actor_block_index",
        "narrator_block_count",
        "structured_narration_summary_kind",
        "opening_narration_normalized",
        "opening_narration_source",
        "opening_narration_beat_count",
        "narration_summary_input_kind",
    }
    _CLASSIFICATION_FIELDS = {"trace_origin", "execution_tier", "canonical_player_flow"}

    def _apply(src: dict[str, Any], fields: set[str]) -> None:
        for f in fields:
            _sif(ev, f, src.get(f))

    # --- Source 1: trace.output ---
    trace_output = _coerce_dict_or_json(raw_trace.get("output"))
    if trace_output:
        nested_ps = _coerce_dict_or_json(trace_output.get("path_summary"))
        direct_ps = (
            trace_output
            if trace_output.get("contract") == "story_runtime_path_observability.v1"
            else {}
        )
'''
