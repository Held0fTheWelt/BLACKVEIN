SOURCE = r'''\
def _record_visible_projection_aspect(
    *,
    ledger: dict[str, Any] | None,
    session_id: str,
    module_id: str,
    turn_number: int,
    turn_kind: str,
    raw_player_input: str,
    trace_id: str | None,
    scene_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    out = ensure_runtime_aspect_ledger(
        ledger,
        session_id=session_id,
        module_id=module_id,
        turn_number=turn_number,
        turn_kind=turn_kind,
        raw_player_input=raw_player_input,
        trace_id=trace_id,
    )
    required_keys = REQUIRED_VISIBLE_ORIGIN_KEYS
    origin_present = bool(scene_blocks) and all(
        isinstance(block, dict) and block_has_required_origin(block)
        for block in scene_blocks
    )
    aspects = out.get("turn_aspect_ledger") if isinstance(out.get("turn_aspect_ledger"), dict) else {}
    narr = aspects.get(ASPECT_NARRATOR_AUTHORITY) if isinstance(aspects, dict) else {}
    narr_expected = narr.get("expected") if isinstance(narr, dict) and isinstance(narr.get("expected"), dict) else {}
    narrator_required = bool(narr_expected.get("required"))
    narrator_present = any(
        str(block.get("block_type") or "").strip().lower() == "narrator"
        and str(block.get("origin_aspect") or "").strip() == ASPECT_NARRATOR_AUTHORITY
        for block in scene_blocks
        if isinstance(block, dict)
    )
    failure_reason = None
    missing_field = None
    lost_at_stage = None
    if not origin_present:
        failure_reason = "visible_block_origin_missing"
        missing_field = "origin_metadata"
        lost_at_stage = "visible_projection"
    elif narrator_required and not narrator_present:
        failure_reason = "required_narrator_block_lost_in_projection"
        lost_at_stage = "visible_projection"
    status = "passed" if failure_reason is None else "failed"
    out = set_aspect_record(
        out,
        ASPECT_VISIBLE_PROJECTION,
        make_aspect_record(
            applicable=True,
            status=status,
            expected={
                "visible_block_origin_metadata": True,
                "required_narrator_block_preserved": narrator_required,
            },
        actual={
            "scene_block_count": len(scene_blocks),
            "visible_block_origin_present": origin_present,
            "blocks_have_origin_aspect": origin_present,
            "required_narrator_block_present": narrator_present,
            "required_blocks_present": (not narrator_required) or narrator_present,
            "lost_required_narrator_block": narrator_required and not narrator_present,
            "required_visible_origin_preserved": origin_present,
            "narrator_required": narrator_required,
            "visible_block_origins": [
                visible_origin_from_block(block)
                for block in scene_blocks
                if isinstance(block, dict) and visible_origin_from_block(block)
            ],
        },
            reasons=[] if failure_reason is None else [failure_reason],
            source="projection",
            failure_class=None if failure_reason is None else "projection_failure",
            failure_reason=failure_reason,
            missing_field=missing_field,
            expected_owner="narrator" if narrator_required else None,
            actual_owner="narrator" if narrator_present else None,
            lost_at_stage=lost_at_stage,
        ),
    )
    if failure_reason is not None:
        validation_record = (
            out.get("turn_aspect_ledger", {}).get(ASPECT_VALIDATION)
            if isinstance(out.get("turn_aspect_ledger"), dict)
            else {}
        )
        commit_record = (
            out.get("turn_aspect_ledger", {}).get(ASPECT_COMMIT)
            if isinstance(out.get("turn_aspect_ledger"), dict)
            else {}
        )
        out = set_aspect_record(
            out,
            ASPECT_VALIDATION,
            make_aspect_record(
                applicable=True,
                status="failed",
                expected={
                    **(
                        validation_record.get("expected")
                        if isinstance(validation_record, dict) and isinstance(validation_record.get("expected"), dict)
                        else {}
                    ),
                    "visible_projection_preserves_required_blocks": True,
                },
                actual={
                    **(
                        validation_record.get("actual")
                        if isinstance(validation_record, dict) and isinstance(validation_record.get("actual"), dict)
                        else {}
                    ),
                    "projection_failure_detected": True,
                    "visible_projection_failure_reason": failure_reason,
                },
                reasons=[failure_reason],
                source="validator",
                failure_class="projection_failure",
                failure_reason=failure_reason,
                missing_field=missing_field,
                expected_owner="narrator" if narrator_required else None,
                actual_owner="narrator" if narrator_present else None,
                lost_at_stage=lost_at_stage,
            ),
        )
        out = set_aspect_record(
            out,
            ASPECT_COMMIT,
            make_aspect_record(
                applicable=True,
                status="partial",
                expected={
                    **(
                        commit_record.get("expected")
                        if isinstance(commit_record, dict) and isinstance(commit_record.get("expected"), dict)
                        else {}
                    ),
                    "projection_failure_recorded": True,
                },
                actual={
                    **(
                        commit_record.get("actual")
                        if isinstance(commit_record, dict) and isinstance(commit_record.get("actual"), dict)
                        else {}
                    ),
                    "projection_failure_detected": True,
                    "visible_projection_failure_reason": failure_reason,
                },
                reasons=[failure_reason],
                source="commit",
                failure_class="projection_failure",
                failure_reason=failure_reason,
                missing_field=missing_field,
                lost_at_stage=lost_at_stage,
            ),
        )
    try:
        runtime_policy = load_module_runtime_policy(
            module_id=module_id,
            runtime_profile_id=out.get("runtime_profile_id"),
        ).to_dict()
    except Exception:
        runtime_policy = {}
    narrative_policy = (
        runtime_policy.get("narrative_aspect_policy")
        if isinstance(runtime_policy.get("narrative_aspect_policy"), dict)
        else {}
    )
    narrative_validation = validate_narrative_aspects(
        narrative_aspect_policy=narrative_policy,
        runtime_context={
            "ledger": out,
            "scene_blocks": scene_blocks,
            "visible_blocks": scene_blocks,
            "input": {
                "kind": turn_kind,
                "raw_player_input": raw_player_input,
            },
            "turn": {
                "number": turn_number,
                "kind": turn_kind,
            },
        },
    ).to_dict()
    candidate_aspects = [
        str(row.get("id") or "").strip()
        for row in (narrative_policy.get("aspects") or [])
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    ]
    semantic_profile_aspects = [
        str(row.get("id") or "").strip()
        for row in (narrative_policy.get("aspects") or [])
        if isinstance(row, dict)
        and str(row.get("id") or "").strip()
        and isinstance(row.get("semantic_profile"), dict)
        and row.get("semantic_profile")
    ]
    missing_narrative_evidence = narrative_validation.get("missing_required_evidence") or []
    if not isinstance(missing_narrative_evidence, list):
        missing_narrative_evidence = []
    missing_visible_narrative_evidence = [
        item
        for item in missing_narrative_evidence
        if isinstance(item, dict) and str(item.get("kind") or "").startswith("visible_")
    ]
    narrative_commit_impact = str(narrative_validation.get("commit_impact") or "diagnostic")
    narrative_failure_reason = narrative_validation.get("failure_reason")
    out = set_aspect_record(
        out,
        ASPECT_NARRATIVE_ASPECT,
        make_aspect_record(
            applicable=bool(narrative_policy.get("aspects")),
            status=str(narrative_validation.get("status") or "not_applicable"),
            expected={
                "policy_present": bool(narrative_policy.get("aspects")),
                "candidate_aspects": candidate_aspects,
                "evidence_required": bool(candidate_aspects),
                "commit_impact": narrative_commit_impact,
                "semantic_tracking_enabled": bool(semantic_profile_aspects),
                "semantic_profile_aspects": semantic_profile_aspects,
                "theme_tracking_policy_present": bool(semantic_profile_aspects),
            },
            selected={
                "selected_aspects": narrative_validation.get("selected_aspects") or [],
                "selection_source": "module_policy" if candidate_aspects else "not_applicable",
                "selected_theme_aspects": narrative_validation.get("semantic_aspect_ids") or [],
            },
            actual={
                "realized_aspects": narrative_validation.get("realized_aspects") or [],
                "missing_required_evidence": missing_narrative_evidence,
                "evidence": narrative_validation.get("evidence") or [],
                "visible_when_required": not bool(missing_visible_narrative_evidence),
                "semantic_classifications": narrative_validation.get("semantic_classifications") or [],
                "semantic_classification_count": int(narrative_validation.get("semantic_classification_count") or 0),
                "semantic_weak_alignment_count": int(narrative_validation.get("semantic_weak_alignment_count") or 0),
                "semantic_required_weak_alignment_count": int(narrative_validation.get("semantic_required_weak_alignment_count") or 0),
                "selected_theme_aspects": narrative_validation.get("semantic_aspect_ids") or [],
                "realized_theme_aspects": narrative_validation.get("realized_semantic_aspects") or [],
            },
            reasons=[str(narrative_failure_reason)] if narrative_failure_reason else [],
'''
