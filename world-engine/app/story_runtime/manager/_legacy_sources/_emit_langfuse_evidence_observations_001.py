SOURCE = r'''\
            and semantic_move_kind not in FORBIDDEN_NON_SPEECH_ACTION_SEMANTIC_MOVES
        )
    npc_action_narration_boundary_pass = not bool(
        path_summary.get("npc_narrated_player_action_violation")
    )
    player_input_attribution = path_summary.get("player_input_attribution_pass")
    player_input_attribution_pass = (
        True if player_input_attribution is None else bool(player_input_attribution)
    )
    intent_surface_contract_pass = True
    if intent_kind:
        intent_surface_contract_pass = (
            intent_kind in PLAYER_INPUT_KINDS
            and isinstance(path_summary.get("player_action_committed"), bool)
            and isinstance(path_summary.get("player_speech_committed"), bool)
            and isinstance(path_summary.get("narrator_response_expected"), bool)
            and isinstance(path_summary.get("npc_response_expected"), bool)
        )
    deterministic_scores["intent_surface_contract_pass"] = 1.0 if intent_surface_contract_pass else 0.0
    deterministic_scores["player_input_attribution_pass"] = 1.0 if player_input_attribution_pass else 0.0
    deterministic_scores["semantic_move_alignment_pass"] = 1.0 if semantic_alignment_pass else 0.0
    subtext_contract_raw = path_summary.get("subtext_contract_pass")
    if subtext_contract_raw is None:
        subtext_fields_present = any(
            path_summary.get(key)
            for key in (
                "subtext_surface_mode",
                "subtext_hidden_intent_hypothesis",
                "subtext_function",
                "subtext_sincerity_band",
            )
        )
        subtext_contract_pass = True
        if subtext_fields_present:
            subtext_contract_pass = all(
                bool(str(path_summary.get(key) or "").strip())
                for key in (
                    "subtext_surface_mode",
                    "subtext_hidden_intent_hypothesis",
                    "subtext_function",
                    "subtext_sincerity_band",
                )
            )
    else:
        subtext_contract_pass = bool(subtext_contract_raw)
    deterministic_scores["subtext_contract_pass"] = 1.0 if subtext_contract_pass else 0.0
    deterministic_scores["npc_action_narration_boundary_pass"] = (
        1.0 if npc_action_narration_boundary_pass else 0.0
    )
    # OPEN-SCORE-SPLIT-01:
    # - opening_shape_contract_pass: purely visible opening-shape quality (can pass in fixtures/mocks).
    # - live_opening_contract_pass: strict live-only success marker for canonical live_ui opening.
    # ``opening_contract_pass`` is kept as a compatibility alias to opening_shape_contract_pass.
    # Turn > 0 trivially passes the shape check (opening-only structural contract).
    _turn_number = int(path_summary.get("turn_number") or 0)
    _opening_blocks: list[dict[str, Any]] = []
    _opening_shape_subgates: dict[str, bool] = {}
    _opening_shape_failure_reasons: list[str] = []
    _scene_block_summary: list[dict[str, Any]] = []
    first_actor_block_index_val: int | None = None
    narrator_block_count_val = 0
    structured_narration_summary_kind: str | None = None
    if _turn_number == 0:
        _opening_blocks = _scene_blocks_from_turn_event(event)
        opening_shape_pass = (
            1.0 if _opening_block_contract_satisfied(_opening_blocks) else 0.0
        )
        # OPEN-SHAPE-EVIDENCE-01: Decompose the contract into auditable subgates and
        # capture a small scene-block excerpt so dashboards can answer "why did
        # opening_shape_contract_pass fail?" without re-fetching the trace body.
        _opening_shape_subgates, _opening_shape_failure_reasons = (
            _compute_opening_shape_subgates(_opening_blocks)
        )
        if narrator_path_selected:
            narrator_only_shape_pass = (
                len(_opening_blocks) >= 4
                and all(
                    str(block.get("block_type") or block.get("type") or "").strip().lower()
                    == "narrator"
                    for block in _opening_blocks
                    if isinstance(block, dict)
                )
            )
            _opening_shape_subgates["narrator_path_narrator_only_valid"] = narrator_only_shape_pass
            if narrator_only_shape_pass:
                opening_shape_pass = 1.0
                _opening_shape_failure_reasons = [
                    reason
                    for reason in _opening_shape_failure_reasons
                    if reason not in {"no_actor_block_present", "first_actor_missing"}
                ]
        _scene_block_summary = _compact_scene_block_summary(_opening_blocks)

        def _bt_ev(b: dict) -> str:
            return str(b.get("block_type") or b.get("type") or "").strip().lower()

        narrator_block_count_val = sum(1 for b in _opening_blocks if _bt_ev(b) == "narrator")
        for i, b in enumerate(_opening_blocks):
            if _bt_ev(b) in {"actor_line", "actor_action"}:
                first_actor_block_index_val = i
                break
        gen_ev = ((event.get("model_route") or {}).get("generation") or {}) if isinstance(event.get("model_route"), dict) else {}
        meta_ev = gen_ev.get("metadata") if isinstance(gen_ev.get("metadata"), dict) else {}
        struct_ev = meta_ev.get("structured_output") if isinstance(meta_ev.get("structured_output"), dict) else None
        if struct_ev is None and isinstance(gen_ev.get("structured_output"), dict):
            struct_ev = gen_ev["structured_output"]
        if isinstance(struct_ev, dict):
            ns_ev = struct_ev.get("narration_summary")
            if isinstance(ns_ev, str) and ns_ev.strip():
                structured_narration_summary_kind = "str"
            elif isinstance(ns_ev, list):
                structured_narration_summary_kind = "list"
            else:
                structured_narration_summary_kind = "absent"
        else:
            structured_narration_summary_kind = "missing_structured"
        if (
            opening_shape_pass < 1.0
            and structured_narration_summary_kind == "str"
            and "narration_summary_single_string" not in _opening_shape_failure_reasons
        ):
            _opening_shape_failure_reasons = list(_opening_shape_failure_reasons) + [
                "narration_summary_single_string"
            ]
    else:
        opening_shape_pass = 1.0
    deterministic_scores["opening_shape_contract_pass"] = opening_shape_pass
    deterministic_scores["opening_contract_pass"] = opening_shape_pass
    # STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P6: promote role_anchor_present
    # to its own top-level numeric score so dashboards can filter without nested metadata joins.
    if _turn_number == 0:
        deterministic_scores["opening_role_anchor_pass"] = (
            1.0 if _opening_shape_subgates.get("role_anchor_present") else 0.0
        )
    else:
        deterministic_scores["opening_role_anchor_pass"] = 1.0
    deterministic_scores["hard_forbidden_absent"] = (
        1.0 if path_summary.get("hard_forbidden_absent", True) else 0.0
    )
    deterministic_scores["opening_summary_only_absent"] = (
        1.0 if path_summary.get("opening_summary_only_absent", True) else 0.0
    )
    deterministic_scores["opening_event_coverage_pass"] = (
        1.0 if (_turn_number > 0 or path_summary.get("opening_event_coverage_pass", True)) else 0.0
    )
    # GOC-KNOWLEDGE-RUNTIME-INTEGRATION P0.3/P0.4: per-category absent-scores derived
    # from hard_forbidden_detection.detected detection_keys. Deterministic 1.0 / 0.0.
    _hfd_for_scores = path_summary.get("hard_forbidden_detection") if isinstance(path_summary.get("hard_forbidden_detection"), dict) else {}
    _detected_keys: set[str] = set()
    for _hit in (_hfd_for_scores.get("detected") or []):
        if isinstance(_hit, dict):
            _key = str(_hit.get("detection_key") or "").strip()
            if _key:
                _detected_keys.add(_key)
    _absent_score_map = {
        "opening_player_speech_absent": "forced_player_speech",
        "opening_npc_exposition_absent": "npc_world_explanation",
        "npc_exposition_absent": "npc_world_explanation",
        "player_agency_violation_absent": "player_agency_violation",
        "meta_runtime_language_absent": "meta_runtime_language",
        "stage_direction_labels_absent": "stage_direction_labels",
        "source_reproduction_absent": "source_text_reproduction",
    }
    for _score_name, _detection_key in _absent_score_map.items():
        deterministic_scores[_score_name] = 0.0 if _detection_key in _detected_keys else 1.0
    if _turn_number == 0:
        if narrator_path_selected:
            _transition_diag_for_scores = {
                "narrator_path_transition_contract_pass": True,
                "narrator_path_transition_mode": "speech_free_scene_setup",
            }
        else:
            _transition_diag_for_scores = compute_opening_transition_from_scene_blocks(
                _opening_blocks,
                human_actor_id=str(path_summary.get("human_actor_id") or "").strip() or None,
                selected_player_role=str(path_summary.get("selected_player_role") or "").strip() or None,
            )
            deterministic_scores["opening_transition_contract_pass"] = (
                1.0 if _transition_diag_for_scores.get("opening_transition_contract_pass") else 0.0
            )
    else:
        _transition_diag_for_scores = {}
        if not narrator_path_selected:
            deterministic_scores["opening_transition_contract_pass"] = 1.0
    _p0_player_turn_langfuse_scores = frozenset(
        {
            "player_action_frame_present",
            "affordance_resolution_present",
            "affordance_status_valid",
            "action_commit_policy_present",
        }
    )
    live_contract_pass = all(
        value == 1.0
        for key, value in deterministic_scores.items()
        if _turn_number > 0 or key not in _p0_player_turn_langfuse_scores
    ) and path_summary.get("quality_class") not in {"degraded", "failed"}
    deterministic_scores["live_runtime_contract_pass"] = 1.0 if live_contract_pass else 0.0
    # Player-visible path only (excludes mock/usage/RAG gates). Stays green in mock_only when UI output is present.
    qc = path_summary.get("quality_class")
    surface_ok = (
        deterministic_scores["visible_output_present"] == 1.0
        and deterministic_scores["actor_lane_safety_pass"] == 1.0
        and deterministic_scores["fallback_absent"] == 1.0
        and qc not in {"degraded", "failed"}
    )
    deterministic_scores["live_runtime_visible_surface_pass"] = 1.0 if surface_ok else 0.0
    _valid_aff = frozenset(
        {"allowed", "allowed_offscreen", "partial", "ambiguous", "blocked", "unknown_target", "unsafe"}
    )
    _aff_st_ev = str(path_summary.get("affordance_status") or "").strip().lower()
    _aff_pres_ev = bool(path_summary.get("affordance_resolution_present"))
    # P0 player-action Langfuse scores apply only to real player turns (``turn_number > 0``).
    # Opening traces must not contribute ``player_action_frame_present`` / affordance scores
    # that could be mistaken for P0 correctness evidence.
    if _turn_number > 0:
        deterministic_scores["player_action_frame_present"] = (
            1.0 if bool(path_summary.get("player_action_frame_present")) else 0.0
        )
        deterministic_scores["affordance_resolution_present"] = 1.0 if _aff_pres_ev else 0.0
        deterministic_scores["affordance_status_valid"] = (
            1.0 if (not _aff_pres_ev or _aff_st_ev in _valid_aff) else 0.0
        )
        deterministic_scores["action_commit_policy_present"] = (
            1.0 if str(path_summary.get("action_commit_policy") or "").strip() else 0.0
        )
        # PLAYER-LOCAL-CONTEXT-AND-NARRATOR-CONSEQUENCE-01 scores (action-resolution short-path only).
        _lct = path_summary.get("local_context_transition") if isinstance(path_summary.get("local_context_transition"), dict) else None
        _ncp = path_summary.get("narrator_consequence_plan") if isinstance(path_summary.get("narrator_consequence_plan"), dict) else None
        _intent_kind_for_consequence = str(path_summary.get("player_input_kind") or "").strip().lower()
        _is_action_resolution_turn = _authoritative_action_surface and _intent_kind_for_consequence in {
            "action",
            "perception",
            "object_interaction",
            "physical_action",
            "movement_action",
            "perception_action",
        }
        # STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P4: emit deterministic
        # action-context scores on every player turn — not only the authoritative action
'''
