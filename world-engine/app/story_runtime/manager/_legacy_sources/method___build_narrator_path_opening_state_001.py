"""Narrator path opening-state source chunk 001.

Contributes ordered source lines for the legacy manager method that builds narrator opening-path state. This chunk is intentionally small and ordered by the legacy manifest.
"""
SOURCE = r'''\
            ),
        )
        for aspect_name in (ASPECT_NPC_AUTHORITY, ASPECT_NPC_AGENCY, ASPECT_VOICE_CONSISTENCY):
            ledger = set_aspect_record(
                ledger,
                aspect_name,
                make_aspect_record(
                    applicable=False,
                    status="not_applicable",
                    expected={"speech_allowed": False, "npc_response_expected": False},
                    actual={"selected_responder_count": 0, "npc_agency_plan_built": False},
                    reasons=["narrator_path_speech_free_phase"],
                    source="director_narrator_path",
                ),
            )
        ledger = set_aspect_record(
            ledger,
            ASPECT_NARRATIVE_ASPECT,
            make_aspect_record(
                applicable=True,
                status="passed",
                expected={"path_id": narrator_path.get("path_id"), "canonical_step_ids": canonical_step_ids},
                selected={"selected_aspects": ["public_violence_to_civilized_threshold"]},
                actual={"source_refs": source_refs, "visible_block_count": len(blocks)},
                reasons=["canonical_path_steps_001_005_realized"],
                source="director_narrator_path",
            ),
        )
        ledger = set_aspect_record(
            ledger,
            ASPECT_BEAT,
            make_aspect_record(
                applicable=True,
                status="passed",
                expected={"canonical_step_ids": canonical_step_ids},
                selected={
                    "selected_beat_id": canonical_step_ids[0] if canonical_step_ids else "opening_narrator_path",
                    "transition_allowed": True,
                },
                actual={
                    "committed": True,
                    "advanced": True,
                    "committed_beat_id": canonical_step_ids[-1] if canonical_step_ids else "opening_narrator_path",
                },
                reasons=["canonical_narrator_sequence_realized"],
                source="director_narrator_path",
                selected_beat=canonical_step_ids[0] if canonical_step_ids else "opening_narrator_path",
            ),
        )
        ledger = set_aspect_record(
            ledger,
            ASPECT_VALIDATION,
            make_aspect_record(
                applicable=True,
                status="passed",
                expected={
                    "narrator_path_contract": "narrator_only",
                    "actor_lines_forbidden": True,
                    "visible_output_required": True,
                },
                actual={
                    "validation_status": "approved",
                    "narrator_block_count": len(narrator_blocks),
                    "souffleuse_block_count": len(souffleuse_blocks),
                    "actor_line_count": 0,
                    "actor_action_count": 0,
                },
                reasons=["narrator_path_opening_contract_passed"],
                source="director_narrator_path",
            ),
        )
        ledger = set_aspect_record(
            ledger,
            ASPECT_COMMIT,
            make_aspect_record(
                applicable=True,
                status="passed",
                expected={"commit_allowed": True, "turn_kind": "opening"},
                actual={"commit_applied": True, "committed_scene_id": session.current_scene_id},
                reasons=["narrator_path_opening_committed"],
                source="director_narrator_path",
            ),
        )
        ledger = set_aspect_record(
            ledger,
            ASPECT_VISIBLE_PROJECTION,
            make_aspect_record(
                applicable=True,
                status="passed",
                expected={"visible_scene_blocks_required": True},
                actual={
                    "visible_output_present": True,
                    "scene_block_count": len(blocks),
                    "narrator_block_count": len(narrator_blocks),
                    "souffleuse_block_count": len(souffleuse_blocks),
                    "actor_line_count": 0,
                    "actor_action_count": 0,
                },
                reasons=["narrator_path_projected_to_scene_blocks"],
                source="director_narrator_path",
            ),
        )
        return {
            "session_id": session.session_id,
            "module_id": session.module_id,
            "current_scene_id": session.current_scene_id,
            "turn_number": 0,
            "turn_input_class": "opening",
            "turn_initiator_type": "engine",
            "trace_id": trace_id,
            "director_path_mode": "narrator_path",
            "director_narrator_path_plan": director_plan,
            "narrator_path": {
                "contract": narrator_path.get("contract"),
                "path_mode": narrator_path.get("path_mode"),
                "path_id": narrator_path.get("path_id"),
                "canonical_step_ids": canonical_step_ids,
                "source_refs": source_refs,
                "authoring_language": narrator_path.get("authoring_language"),
                "session_output_language": session.session_output_language,
                "output_realization": output_realization,
                "souffleuse_output_realization": souffleuse_output_realization,
            },
            "souffleuse_projection": souffleuse_projection
            if isinstance(souffleuse_projection, dict)
            else {},
            "opening_scene_sequence": {
                "id": narrator_path.get("path_id"),
                "mode": "narrator_path",
                "canonical_step_ids": canonical_step_ids,
                "source_refs": source_refs,
            },
            "player_action_frame": {
                "player_input_kind": "opening",
                "action_kind": "narration",
                "speech_projection_allowed": False,
                "souffleuse_guidance_present": bool(souffleuse_blocks),
            },
            "interpreted_input": {
                "kind": "opening",
                "player_input_kind": "opening",
                "confidence": 1.0,
                "player_action_committed": False,
                "player_speech_committed": False,
                "narrator_response_expected": True,
                "npc_response_expected": False,
                "director_path_mode": "narrator_path",
            },
            "generation": {
                "attempted": True,
                "success": True,
                "content": joined,
                "model_raw_text": joined,
                "structured_output": structured_output,
                "fallback_used": output_fallback_used,
                "metadata": {
                    "adapter": output_realization.get("adapter") or NARRATOR_PATH_ADAPTER,
                    "provider": generation_provider,
                    "model": generation_model,
                    "adapter_invocation_mode": output_realization.get("adapter_invocation_mode")
                    or NARRATOR_PATH_INVOCATION_MODE,
                    "final_adapter": output_realization.get("adapter") or NARRATOR_PATH_ADAPTER,
                    "final_adapter_invocation_mode": output_realization.get("adapter_invocation_mode")
                    or NARRATOR_PATH_INVOCATION_MODE,
                    "structured_output": structured_output,
                    "usage_available": False,
                    "usage_source": output_realization.get("usage_source") or "canonical_content_renderer",
                    "generation_latency_ms": 0,
                    "fallback_reason": "; ".join(output_fallback_reasons)
                    if output_fallback_used
                    else None,
                    "output_realization": output_realization,
                    "souffleuse_output_realization": souffleuse_output_realization,
                    "souffleuse_projection": souffleuse_projection
                    if isinstance(souffleuse_projection, dict)
                    else {},
                },
            },
            "graph_diagnostics": {
                "errors": list(
                    (
                        souffleuse_projection.get("diagnostics", {}).get("errors")
                        if isinstance(souffleuse_projection, dict)
                        and isinstance(souffleuse_projection.get("diagnostics"), dict)
                        else []
                    )
                    or []
                ),
                "execution_health": "degraded_generation"
                if output_fallback_used
                else "healthy",
                "graph_name": "director_narrator_path",
                "nodes_executed": [
                    "director.narrator_path.select",
                    "narrator_path.realize",
                    *output_module_nodes,
                    *(
                        ["souffleuse.select", "souffleuse.realize"]
                        if souffleuse_blocks
                        else []
                    ),
                    "visible.project",
                    "commit.apply",
                ],
            },
            "nodes_executed": [
                "director.narrator_path.select",
                "narrator_path.realize",
                *output_module_nodes,
                *(
                    ["souffleuse.select", "souffleuse.realize"]
                    if souffleuse_blocks
                    else []
                ),
                "visible.project",
                "commit.apply",
            ],
            "retrieval": {},
            "routing": {
                "selected_provider": generation_provider,
                "selected_model": generation_model,
                "fallback_stage_reached": "output_module_fallback"
                if output_fallback_used
                else "primary_only",
            },
            "validation_outcome": {
                "status": "approved",
                "reason": "narrator_path_opening_contract_passed",
                "validator_lane": "narrator_path_contract_v1",
            },
            "visible_output_bundle": {
                "gm_narration": gm_narration,
                "scene_blocks": blocks,
                "souffleuse_blocks": souffleuse_blocks,
                "spoken_lines": [],
                "action_lines": [],
            },
            "selected_responder_set": [],
            "committed_result": {
                "commit_applied": True,
                "committed_effects": [
                    {
                        "effect_type": "narrator_path_opening",
                        "description": "Canonical narrator path opening projected without NPC agency.",
                    }
                ],
                "reason": "narrator_path_opening_committed",
'''
