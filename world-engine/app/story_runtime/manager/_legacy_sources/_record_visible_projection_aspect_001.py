"""Visible-projection aspect source chunk 001.

Contributes ordered source lines for recording visible-projection aspect observations. This chunk is intentionally small and ordered by the legacy manifest.
"""
SOURCE = r'''\
            source="projection",
            failure_class=(
                "hard_contract_failure"
                if narrative_failure_reason and narrative_commit_impact == "reject"
                else "recoverable_dramatic_failure"
                if narrative_failure_reason and narrative_commit_impact == "recover"
                else "degradation_only"
                if narrative_failure_reason
                else None
            ),
            failure_reason=str(narrative_failure_reason) if narrative_failure_reason else None,
            missing_field="narrative_aspect_evidence" if narrative_failure_reason else None,
            lost_at_stage="visible_projection" if missing_visible_narrative_evidence else None,
        ),
    )
    if narrative_failure_reason and narrative_commit_impact in {"recover", "reject"}:
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
        failure_class = (
            "hard_contract_failure"
            if narrative_commit_impact == "reject"
            else "recoverable_dramatic_failure"
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
                    "narrative_aspect_contract_pass": True,
                },
                actual={
                    **(
                        validation_record.get("actual")
                        if isinstance(validation_record, dict) and isinstance(validation_record.get("actual"), dict)
                        else {}
                    ),
                    "narrative_aspect_failure": True,
                    "narrative_aspect_failure_reason": narrative_failure_reason,
                },
                reasons=[str(narrative_failure_reason)],
                source="validator",
                failure_class=failure_class,
                failure_reason=str(narrative_failure_reason),
                missing_field="narrative_aspect_evidence",
                lost_at_stage="visible_projection" if missing_visible_narrative_evidence else None,
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
                    "narrative_aspect_failure_recorded": True,
                },
                actual={
                    **(
                        commit_record.get("actual")
                        if isinstance(commit_record, dict) and isinstance(commit_record.get("actual"), dict)
                        else {}
                    ),
                    "narrative_aspect_failure": True,
                    "narrative_aspect_failure_reason": narrative_failure_reason,
                },
                reasons=[str(narrative_failure_reason)],
                source="commit",
                failure_class=failure_class,
                failure_reason=str(narrative_failure_reason),
                missing_field="narrative_aspect_evidence",
                lost_at_stage="visible_projection" if missing_visible_narrative_evidence else None,
            ),
        )
    beat = aspects.get(ASPECT_BEAT) if isinstance(aspects, dict) else {}
    if isinstance(beat, dict) and beat.get("applicable"):
        expected = beat.get("expected") if isinstance(beat.get("expected"), dict) else {}
        selected = beat.get("selected") if isinstance(beat.get("selected"), dict) else {}
        expected_realization = [
            str(item)
            for item in (expected.get("expected_realization") or [])
            if str(item).strip()
        ]
        narrator_realized = any(
            str(block.get("origin_aspect") or "") == ASPECT_NARRATOR_AUTHORITY
            for block in scene_blocks
            if isinstance(block, dict)
        )
        npc_realized = any(
            str(block.get("origin_aspect") or "") == ASPECT_NPC_AUTHORITY
            for block in scene_blocks
            if isinstance(block, dict)
        )
        realized_capabilities = {
            str(block.get("origin_capability") or "").strip()
            for block in scene_blocks
            if isinstance(block, dict) and str(block.get("origin_capability") or "").strip()
        }
        for block in scene_blocks:
            if not isinstance(block, dict):
                continue
            folded = block.get("folded_origin_evidence")
            if isinstance(folded, list):
                for origin in folded:
                    if isinstance(origin, dict) and str(origin.get("origin_capability") or "").strip():
                        realized_capabilities.add(str(origin.get("origin_capability")).strip())
        missing_expected: list[str] = []
        for expected_item in expected_realization:
            if expected_item in realized_capabilities:
                continue
            if expected_item in {"narrator", "narrator_authority"} and narrator_realized:
                continue
            if expected_item in {"npc", "npc_authority"} and npc_realized:
                continue
            missing_expected.append(expected_item)
        beat_realized = origin_present and not missing_expected
        beat_contractually_required = bool(
            expected.get("contractually_required")
            or selected.get("contractually_required")
            or expected.get("hard_contract_required")
        )
        if beat_realized:
            beat_status = "passed"
            beat_failure_class = None
            beat_failure_reason = None
        elif beat_contractually_required:
            beat_status = "failed"
            beat_failure_class = "hard_contract_failure"
            beat_failure_reason = "selected_required_beat_lost"
        elif missing_expected:
            beat_status = "partial"
            beat_failure_class = "degradation_only"
            beat_failure_reason = "beat_realization_not_visible"
        else:
            beat_status = "partial"
            beat_failure_class = "observability_gap"
            beat_failure_reason = "beat_realization_not_visible"
        out = set_aspect_record(
            out,
            ASPECT_BEAT,
            make_aspect_record(
                applicable=True,
                status=beat_status,
                expected=expected,
                selected=selected,
                actual={
                    **(beat.get("actual") if isinstance(beat.get("actual"), dict) else {}),
                    "realized": beat_realized,
                    "visible": bool(scene_blocks),
                    "committed": (
                        (beat.get("actual") or {}).get("committed")
                        if isinstance(beat.get("actual"), dict)
                        else None
                    ),
                    "missing_expected_realization": missing_expected,
                    "realization_evidence": [
                        visible_origin_from_block(block)
                        for block in scene_blocks
                        if isinstance(block, dict)
                        and (
                            str(block.get("origin_beat_id") or "").strip()
                            == str(selected.get("selected_beat_id") or "").strip()
                            or str(block.get("origin_capability") or "").strip() in set(expected_realization)
                        )
                    ],
                    "failure_classification": beat_failure_class,
                },
                reasons=[] if beat_realized else [beat_failure_reason],
                source="projection",
                failure_class=beat_failure_class,
                failure_reason=beat_failure_reason,
                selected_beat=selected.get("selected_beat_id"),
                lost_at_stage="visible_projection" if not beat_realized else None,
            ),
        )
        if beat_failure_class == "hard_contract_failure":
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
                        "contractually_required_beat_realized": True,
                    },
                    actual={
                        **(
                            validation_record.get("actual")
                            if isinstance(validation_record, dict) and isinstance(validation_record.get("actual"), dict)
                            else {}
                        ),
                        "required_beat_lost": True,
                        "selected_beat": selected.get("selected_beat_id"),
                    },
                    reasons=[beat_failure_reason],
                    source="validator",
                    failure_class=beat_failure_class,
                    failure_reason=beat_failure_reason,
                    selected_beat=selected.get("selected_beat_id"),
                    lost_at_stage="visible_projection",
                ),
            )
            out = set_aspect_record(
                out,
                ASPECT_COMMIT,
                make_aspect_record(
'''
