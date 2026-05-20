SOURCE = r'''\
def _live_scene_blocks_from_visible_bundle(
    visible_output_bundle: dict[str, Any] | None,
    *,
    turn_number: int,
    structured_output: dict[str, Any] | None = None,
    runtime_projection: dict[str, Any] | None = None,
    graph_state: dict[str, Any] | None = None,
    session_output_language: str = DEFAULT_SESSION_LANGUAGE,
    player_input: str | None = None,
    story_runtime_experience: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if graph_state is not None and turn_number != 0:
        graph_state.pop("_actor_block_projection_evidence", None)
        graph_state.pop("_opening_transition_diagnostics", None)
    bundle = visible_output_bundle if isinstance(visible_output_bundle, dict) else {}
    proj = runtime_projection if isinstance(runtime_projection, dict) else None
    human_id = str((proj or {}).get("human_actor_id") or "").strip()
    role = str((proj or {}).get("selected_player_role") or "").strip()
    _exp_eff = _effective_story_runtime_experience_slice(graph_state, story_runtime_experience)
    _goc_action_block_type = (
        "actor_line"
        if goc_transcript_policy_flags(_exp_eff)["map_action_lines_to_actor_line_lane"]
        else "actor_action"
    )
    _exp_lang = str(session_output_language or DEFAULT_SESSION_LANGUAGE).strip().lower()[:2] or DEFAULT_SESSION_LANGUAGE
    echo_strings: list[str] = []
    pi = str(player_input or "").strip()
    if pi:
        echo_strings.append(pi)
    ledger = (
        graph_state.get("turn_aspect_ledger")
        if isinstance(graph_state, dict) and isinstance(graph_state.get("turn_aspect_ledger"), dict)
        else {}
    )
    beat_record = (
        (ledger.get("turn_aspect_ledger") or {}).get("beat")
        if isinstance(ledger.get("turn_aspect_ledger"), dict)
        else {}
    )
    selected_beat_id = None
    canonical_turn_id = None
    if isinstance(beat_record, dict):
        selected_beat_id = (
            (beat_record.get("selected") or {}).get("selected_beat_id")
            if isinstance(beat_record.get("selected"), dict)
            else None
        ) or (
            (beat_record.get("actual") or {}).get("selected_beat_id")
            if isinstance(beat_record.get("actual"), dict)
            else None
        )
    if isinstance(ledger, dict):
        canonical_turn_id = (
            ledger.get("canonical_turn_id")
            or ledger.get("turn_id")
            or ledger.get("turn_record_id")
        )

    def origin_metadata(block_type: str, actor_id: str | None = None) -> dict[str, Any]:
        bt = str(block_type or "").strip().lower()
        if bt == "narrator":
            frame = graph_state.get("player_action_frame") if isinstance(graph_state, dict) and isinstance(graph_state.get("player_action_frame"), dict) else {}
            pik = str(frame.get("player_input_kind") or "").strip().lower()
            action_kind = str(frame.get("action_kind") or "").strip().lower()
            capability = NARRATOR_ACTION_CONSEQUENCE_DESCRIBE
            if is_perception_like_player_input_kind(pik):
                capability = NARRATOR_PERCEPTION_RESULT_DESCRIBE
            elif action_kind == "movement":
                capability = NARRATOR_LOCATION_TRANSITION_DESCRIBE
            elif action_kind == "object_interaction":
                capability = NARRATOR_OBJECT_STATE_DESCRIBE
            elif turn_number == 0:
                capability = NARRATOR_OPENING_EVENT_REALIZE
            return {
                "origin_aspect": "narrator_authority",
                "origin_beat_id": selected_beat_id,
                "origin_capability": capability,
                "authority_owner": "narrator",
                "expected_owner": "narrator",
                "actual_owner": "narrator",
                "canonical_turn_id": canonical_turn_id,
                "evidence_role": EVIDENCE_REQUIRED,
            }
        if bt == "actor_line":
            interp = graph_state.get("interpreted_input") if isinstance(graph_state, dict) and isinstance(graph_state.get("interpreted_input"), dict) else {}
            pik = str(interp.get("player_input_kind") or "").strip().lower()
            return {
                "origin_aspect": "npc_authority",
                "origin_beat_id": selected_beat_id,
                "origin_capability": NPC_DIRECT_ANSWER_ALLOWED
                if is_speech_like_player_input_kind(pik)
                else NPC_SOCIAL_REACTION_OPTIONAL,
                "authority_owner": "npc" if actor_id else "runtime",
                "expected_owner": "npc" if actor_id else "system",
                "actual_owner": "npc" if actor_id else "system",
                "canonical_turn_id": canonical_turn_id,
                "evidence_role": EVIDENCE_SUPPORTING,
            }
        if bt == "actor_action":
            return {
                "origin_aspect": "npc_authority",
                "origin_beat_id": selected_beat_id,
                "origin_capability": NPC_ACTION_GESTURE_OPTIONAL,
                "authority_owner": "npc" if actor_id else "runtime",
                "expected_owner": "npc" if actor_id else "system",
                "actual_owner": "npc" if actor_id else "system",
                "canonical_turn_id": canonical_turn_id,
                "evidence_role": EVIDENCE_SUPPORTING,
            }
        return {
            "origin_aspect": "visible_projection",
            "origin_beat_id": selected_beat_id,
            "origin_capability": None,
            "authority_owner": "runtime",
            "expected_owner": "system",
            "actual_owner": "system",
            "canonical_turn_id": canonical_turn_id,
            "evidence_role": EVIDENCE_SUPPORTING,
        }

    def with_origin(block: dict[str, Any]) -> dict[str, Any]:
        out = dict(block)
        meta = origin_metadata(
            str(out.get("block_type") or out.get("type") or ""),
            str(out.get("actor_id") or "").strip() or None,
        )
        for key, value in meta.items():
            out.setdefault(key, value)
        return out

    existing = bundle.get("scene_blocks")
    if isinstance(existing, list) and existing:
        blocks = [with_origin(block) for block in existing if isinstance(block, dict)]
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

    def delivery() -> dict[str, Any]:
        return {
            "mode": "typewriter",
            "characters_per_second": 44,
            "pause_before_ms": 150,
            "pause_after_ms": 650,
            "skippable": True,
        }

    blocks: list[dict[str, Any]] = []

    def append_block(block_type: str, text: str, *, speaker_label: str, actor_id: str | None = None) -> None:
        raw = str(text or "").strip()
        if not raw:
            return
        clean, _partial = sanitize_visible_block_text(
            raw,
            block_type=str(block_type or ""),
            speaker_label=str(speaker_label or ""),
            actor_id=str(actor_id).strip() if actor_id else None,
            expected_language=_exp_lang,
        )
        if not clean:
            return
        blocks.append(
            {
                "id": f"turn-{turn_number}-live-block-{len(blocks) + 1}",
                "block_type": block_type,
                "speaker_label": speaker_label,
                "actor_id": actor_id,
                "target_actor_id": None,
                "text": clean,
                "delivery": delivery(),
                "source": "live_runtime_graph",
                **origin_metadata(block_type, actor_id),
            }
        )

    def actor_label(actor_id: str) -> str:
        aid = str(actor_id or "").strip()
        display_names = proj.get("actor_display_names") if isinstance(proj.get("actor_display_names"), dict) else {}
        if aid and display_names.get(aid):
            return str(display_names.get(aid))
        roster = proj.get("actor_roster") if isinstance(proj.get("actor_roster"), dict) else {}
        roster_row = roster.get(aid) if aid and isinstance(roster.get(aid), dict) else {}
        label = str(roster_row.get("display_name") or roster_row.get("name") or "").strip()
        if label:
            return label
        return aid.replace("_", " ").strip().title() or "Actor"

    def append_json_blocks(raw: str) -> bool:
        text = str(raw or "").strip()
        if not text.startswith("{"):
            return False
        try:
            parsed = json.loads(text)
        except Exception:
            return False
        if not isinstance(parsed, dict):
            return False
        emitted = False
        summary = str(parsed.get("narration_summary") or parsed.get("narrative_response") or "").strip()
        if summary:
            append_block("narrator", summary, speaker_label="Narrator")
            emitted = True
        spoken = parsed.get("spoken_lines")
        if isinstance(spoken, list):
            for row in spoken:
                if not isinstance(row, dict):
                    continue
                speaker_id = str(row.get("speaker_id") or "").strip()
                line = str(row.get("text") or row.get("line") or "").strip()
                if not line:
                    continue
                if proj is not None:
                    if not speaker_id:
                        continue
                    if _is_goc_human_lane_actor(
                        speaker_id,
                        human_actor_id=human_id,
'''
