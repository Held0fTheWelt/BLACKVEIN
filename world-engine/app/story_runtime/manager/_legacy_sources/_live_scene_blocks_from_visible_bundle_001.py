"""Live-scene block source chunk 001.

Contributes ordered source lines for extracting live-scene blocks from visible projection bundles. This chunk is intentionally small and ordered by the legacy manifest.
"""
SOURCE = r'''\
                        selected_player_role=role,
                    ):
                        continue
                append_block("actor_line", line, speaker_label=actor_label(speaker_id), actor_id=speaker_id or None)
                emitted = True
        actions = parsed.get("action_lines")
        if isinstance(actions, list):
            for row in actions:
                if not isinstance(row, dict):
                    continue
                actor_id = str(row.get("actor_id") or "").strip()
                line = str(row.get("text") or row.get("line") or "").strip()
                if not line:
                    continue
                if proj is not None:
                    if not actor_id:
                        continue
                    if _is_goc_human_lane_actor(
                        actor_id,
                        human_actor_id=human_id,
                        selected_player_role=role,
                    ):
                        continue
                append_block(
                    _goc_action_block_type,
                    line,
                    speaker_label=actor_label(actor_id),
                    actor_id=actor_id or None,
                )
                emitted = True
        return emitted

    for line in _coerce_visible_text_lines(bundle.get("gm_narration")):
        if append_json_blocks(line):
            continue
        append_block("narrator", line, speaker_label="Narrator")

    for item in bundle.get("spoken_lines") or []:
        if isinstance(item, dict):
            speaker_id = str(item.get("speaker_id") or "").strip()
            line = str(item.get("text") or item.get("line") or "").strip()
            if not line:
                continue
            if proj is not None:
                if not speaker_id:
                    continue
                if _is_goc_human_lane_actor(
                    speaker_id,
                    human_actor_id=human_id,
                    selected_player_role=role,
                ):
                    continue
            append_block("actor_line", line, speaker_label=actor_label(speaker_id), actor_id=speaker_id or None)
            continue
        for line in _coerce_visible_text_lines(item):
            label = "Actor"
            text = line
            if ":" in line:
                maybe_label, maybe_text = line.split(":", 1)
                if maybe_label.strip() and maybe_text.strip():
                    label = maybe_label.strip()
                    text = maybe_text.strip()
            if proj is not None:
                lane_key = canonicalize_goc_actor_id(label) or label.strip().lower()
                if lane_key and _is_goc_human_lane_actor(
                    lane_key,
                    human_actor_id=human_id,
                    selected_player_role=role,
                ):
                    continue
            append_block("actor_line", text, speaker_label=label)

    for item in bundle.get("action_lines") or []:
        if isinstance(item, dict):
            aid = str(item.get("actor_id") or "").strip()
            line = str(item.get("text") or item.get("line") or "").strip()
            if not line:
                continue
            if proj is not None:
                if not aid:
                    continue
                if _is_goc_human_lane_actor(
                    aid,
                    human_actor_id=human_id,
                    selected_player_role=role,
                ):
                    continue
            append_block(_goc_action_block_type, line, speaker_label=actor_label(aid), actor_id=aid or None)
            continue
        for line in _coerce_visible_text_lines(item):
            append_block(_goc_action_block_type, line, speaker_label="Action")

    if graph_state is not None and turn_number == 0:
        sl_n, al_n = _structured_lane_dict_counts(structured_output if isinstance(structured_output, dict) else None)
        count_before_backfill = _actor_block_projection_count(blocks)
        bf_src = "none"
        bf_filt: str | None = None
        if isinstance(structured_output, dict) and structured_output:
            blocks, bf_src, bf_filt = _maybe_backfill_opening_actor_from_structured(
                blocks,
                structured_output=structured_output,
                runtime_projection=proj,
                turn_number=turn_number,
                human_actor_id=human_id,
                selected_player_role=role,
                delivery_fn=delivery,
                actor_label_fn=actor_label,
                story_runtime_experience=_exp_eff,
            )
        actor_src = bf_src
        filt_out = bf_filt
        if actor_src == "none" and count_before_backfill > 0:
            for b in blocks[3:]:
                if not isinstance(b, dict):
                    continue
                bt = str(b.get("block_type") or "").strip().lower()
                if bt == "actor_line":
                    actor_src = "spoken_lines"
                    break
                if bt == "actor_action":
                    actor_src = "action_lines"
                    break
        graph_state["_actor_block_projection_evidence"] = {
            "actor_line_count_before_projection": sl_n,
            "action_line_count_before_projection": al_n,
            "actor_block_count_after_projection": _actor_block_projection_count(blocks),
            "actor_block_source": actor_src,
            "actor_block_filtered_reason": filt_out,
        }

    blocks, vis_diag = _finalize_visible_blocks_with_goc_actor_split(
        blocks,
        expected_language=_exp_lang,
        human_actor_id=human_id or None,
        selected_player_role=role or None,
        turn_number=turn_number,
        player_input_echo_strings=echo_strings or None,
        runtime_projection=proj,
        story_runtime_experience=_exp_eff,
    )
    if graph_state is not None:
        graph_state["_visible_narrative_contract"] = vis_diag
        ev_post = graph_state.get("_actor_block_projection_evidence")
        if turn_number == 0 and isinstance(ev_post, dict):
            ev_post["actor_block_count_after_projection"] = _actor_block_projection_count(blocks)

    narrator_path_selected = (
        graph_state is not None
        and str(graph_state.get("director_path_mode") or "").strip() == "narrator_path"
    )
    if turn_number == 0 and graph_state is not None and not narrator_path_selected:
        blocks, _polished = polish_first_opening_actor_block(blocks, output_language=_exp_lang)
        graph_state["_opening_transition_diagnostics"] = compute_opening_transition_from_scene_blocks(
            blocks,
            human_actor_id=human_id or None,
            selected_player_role=role or None,
        )
    elif turn_number == 0 and graph_state is not None and narrator_path_selected:
        graph_state.pop("_opening_transition_diagnostics", None)

    return blocks
'''
