"""Narrator path opening-state source chunk 000.

Contributes ordered source lines for the legacy manager method that builds narrator opening-path state. This chunk is intentionally small and ordered by the legacy manifest.
"""
SOURCE = r'''\
    def _build_narrator_path_opening_state(
        self,
        *,
        session: StorySession,
        trace_id: str | None,
    ) -> dict[str, Any]:
        """Build Turn 0 through the general narrator path.

        The narrator path is the Director route for narration, movement
        handoffs, description, and phases where nobody speaks. For the GoC
        opening it avoids the full player-turn graph: no action resolution, no
        NPC agency plan, no RAG query, and no LDSS fallback. If the session
        language differs from the canonical authoring language, the output
        module realizes the canonical English blocks into player-visible text.
        """
        narrator_path = build_goc_narrator_path_opening(
            session_output_language=session.session_output_language
        )
        source_narrator_blocks = [
            dict(block)
            for block in narrator_path.get("scene_blocks", [])
            if isinstance(block, dict) and str(block.get("text") or "").strip()
        ]
        souffleuse_projection = build_goc_opening_souffleuse_projection(
            session_output_language=session.session_output_language,
            runtime_projection=session.runtime_projection
            if isinstance(session.runtime_projection, dict)
            else None,
            narrator_path=narrator_path,
            scene_blocks=source_narrator_blocks,
        )
        source_souffleuse_blocks = [
            dict(block)
            for block in (
                souffleuse_projection.get("blocks")
                if isinstance(souffleuse_projection, dict)
                else []
            )
            if isinstance(block, dict) and str(block.get("text") or "").strip()
        ]
        narrator_blocks, output_realization = self._realize_narrator_path_output(
            source_blocks=source_narrator_blocks,
            narrator_path=narrator_path,
            session=session,
        )
        souffleuse_blocks, souffleuse_output_realization = self._realize_souffleuse_output(
            source_blocks=source_souffleuse_blocks,
            session=session,
        )
        blocks = [*narrator_blocks, *souffleuse_blocks]
        if not blocks:
            raise RuntimeError("Narrator path produced no opening scene blocks.")
        gm_narration = [
            str(block.get("text") or "").strip()
            for block in narrator_blocks
            if str(block.get("text") or "").strip()
        ]
        joined = "\n\n".join(gm_narration)
        director_plan = (
            narrator_path.get("director_plan")
            if isinstance(narrator_path.get("director_plan"), dict)
            else {}
        )
        selected_capabilities = [
            str(cap).strip()
            for cap in (director_plan.get("selected_capabilities") or [NARRATOR_OPENING_EVENT_REALIZE])
            if str(cap).strip()
        ]
        if not selected_capabilities:
            selected_capabilities = [NARRATOR_OPENING_EVENT_REALIZE]
        if souffleuse_blocks and SOUFFLEUSE_OPENING_ROLE_ORIENTATION not in selected_capabilities:
            selected_capabilities.append(SOUFFLEUSE_OPENING_ROLE_ORIENTATION)
        director_plan = dict(director_plan)
        director_plan["selected_capabilities"] = selected_capabilities
        source_refs = [
            str(ref).strip()
            for ref in (narrator_path.get("source_refs") or director_plan.get("content_source_refs") or [])
            if str(ref).strip()
        ]
        for block in blocks:
            if not isinstance(block, dict):
                continue
            for ref in block.get("source_refs") if isinstance(block.get("source_refs"), list) else []:
                text_ref = str(ref).strip()
                if text_ref and text_ref not in source_refs:
                    source_refs.append(text_ref)
        canonical_step_ids = [
            str(step_id).strip()
            for step_id in (narrator_path.get("canonical_step_ids") or [])
            if str(step_id).strip()
        ]
        output_realized = str(output_realization.get("status") or "").strip() in {
            "realized",
            "synthesized",
        }
        souffleuse_output_realized = (
            str(souffleuse_output_realization.get("status") or "").strip() == "realized"
        )
        output_realization_status = str(output_realization.get("status") or "").strip()
        souffleuse_output_realization_status = str(
            souffleuse_output_realization.get("status") or ""
        ).strip()
        output_fallback_used = output_realization_status.startswith(
            "fallback_output_module"
        ) or souffleuse_output_realization_status.startswith("fallback_output_module")
        output_fallback_reasons = [
            str(reason).strip()
            for reason in (
                output_realization.get("fallback_reason"),
                souffleuse_output_realization.get("fallback_reason"),
            )
            if str(reason or "").strip()
        ]
        generation_provider = (
            str(output_realization.get("provider") or "").strip() if output_realized else "world_engine"
        ) or "world_engine"
        generation_model = (
            str(output_realization.get("api_model") or output_realization.get("model_id") or "").strip()
            if output_realized
            else "narrator_path_renderer"
        ) or "narrator_path_renderer"
        output_module_nodes = []
        if output_realized:
            output_module_nodes.append("output_module.realize")
        if souffleuse_output_realized:
            output_module_nodes.append("souffleuse.output_realize")
        phase_costs = {
            "narrator_path": build_deterministic_phase_cost(
                phase="narrator_path",
                provider="world_engine",
                model="narrator_path_renderer",
                scene_block_count=len(blocks),
                selected_capabilities=selected_capabilities,
            )
        }
        if output_realized:
            phase_costs["narrator_path_synthesis_module"] = build_unavailable_phase_cost(
                phase="narrator_path_synthesis_module",
                provider=generation_provider,
                model=generation_model,
                reason="usage_accounting_unavailable",
                scene_block_count=len(blocks),
                adapter=output_realization.get("adapter"),
            )
        if souffleuse_output_realized:
            phase_costs["souffleuse_output_module"] = build_unavailable_phase_cost(
                phase="souffleuse_output_module",
                provider=str(souffleuse_output_realization.get("provider") or generation_provider),
                model=str(
                    souffleuse_output_realization.get("api_model")
                    or souffleuse_output_realization.get("model_id")
                    or generation_model
                ),
                reason="output_module_usage_unavailable",
                scene_block_count=len(souffleuse_blocks),
                adapter=souffleuse_output_realization.get("adapter"),
            )
        if isinstance(souffleuse_projection, dict):
            diagnostics = souffleuse_projection.get("diagnostics")
            if isinstance(diagnostics, dict):
                diagnostics["output_realization"] = souffleuse_output_realization
        structured_output = {
            "schema_version": "runtime_actor_turn_v1",
            "narrative_response": joined,
            "narration_summary": gm_narration,
            "spoken_lines": [],
            "action_lines": [],
            "proposed_scene_id": session.current_scene_id,
            "intent_summary": "Director selected narrator_path for speech-free canonical opening.",
            "director_path_mode": "narrator_path",
            "canonical_step_ids": canonical_step_ids,
            "source_refs": source_refs,
            "source_authoring_language": narrator_path.get("authoring_language"),
            "session_output_language": session.session_output_language,
            "output_realization": output_realization,
            "souffleuse_output_realization": souffleuse_output_realization,
            "souffleuse_blocks": souffleuse_blocks,
            "souffleuse_projection": souffleuse_projection
            if isinstance(souffleuse_projection, dict)
            else {},
        }
        runtime_profile_id = _runtime_profile_id_from_projection(
            session.runtime_projection if isinstance(session.runtime_projection, dict) else None
        )
        ledger = initialize_runtime_aspect_ledger(
            session_id=session.session_id,
            module_id=session.module_id,
            turn_number=0,
            turn_kind="opening",
            raw_player_input=None,
            input_kind="opening",
            trace_id=trace_id,
            runtime_profile_id=runtime_profile_id,
        )
        ledger = set_aspect_record(
            ledger,
            ASPECT_CAPABILITY_SELECTION,
            make_aspect_record(
                applicable=True,
                status="passed",
                expected={
                    "director_path_mode": "narrator_path",
                    "speech_allowed": False,
                    "npc_agency_required": False,
                    "player_action_resolution_required": False,
                },
                selected={
                    "selected_capabilities": selected_capabilities,
                    "suppressed_capability_groups": director_plan.get("skipped_capability_groups")
                    if isinstance(director_plan.get("skipped_capability_groups"), list)
                    else [],
                },
                actual={
                    "realized_capabilities": selected_capabilities,
                    "forbidden_capability_realized": False,
                    "missing_required_capabilities": [],
                    "npc_agency_plan_built": False,
                    "speech_projection_allowed": False,
                    "souffleuse_block_count": len(souffleuse_blocks),
                },
                reasons=[
                    "director_selected_narrator_path",
                    *(
                        ["director_selected_souffleuse_content_cue"]
                        if souffleuse_blocks
                        else []
                    ),
                ],
                source="director_narrator_path",
            ),
        )
        ledger = set_aspect_record(
            ledger,
            ASPECT_NARRATOR_AUTHORITY,
            make_aspect_record(
                applicable=True,
                status="passed",
                expected={
                    "authority_owner": "narrator",
                    "origin_capability": NARRATOR_OPENING_EVENT_REALIZE,
                    "speech_allowed": False,
                    "content_source_refs": source_refs,
                },
                actual={
                    "narrator_block_count": len(narrator_blocks),
                    "souffleuse_block_count": len(souffleuse_blocks),
                    "actor_line_count": 0,
                    "actor_action_count": 0,
                    "human_actor_line_count": 0,
                    "source_refs": source_refs,
                },
                reasons=["narrator_path_realized_visible_blocks"],
                source="director_narrator_path",
                selected_capability=NARRATOR_OPENING_EVENT_REALIZE,
                realized_capability=NARRATOR_OPENING_EVENT_REALIZE,
'''
