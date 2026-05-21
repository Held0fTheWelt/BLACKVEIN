"""Langfuse verify source segment: handler_live_matrix_and_score_start.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
            if not isinstance(row, dict):
                continue
            ev, _src = _extract_normalized_wos_evidence(row)
            det_scores, _ = _extract_scores_split(row)
            is_opening = _is_opening_trace(row)
            lo_val = _live_opening_value(det_scores, row)
            matrix.append(
                {
                    "trace_id": row.get("id"),
                    "trace_name": row.get("name"),
                    "is_opening_trace": is_opening,
                    "selected_player_role": ev.get("selected_player_role"),
                    "trace_origin": ev.get("trace_origin"),
                    "execution_tier": ev.get("execution_tier"),
                    "canonical_player_flow": ev.get("canonical_player_flow"),
                    "opening_shape_contract_pass": ev.get("opening_shape_contract_pass"),
                    "live_runtime_contract_pass": ev.get("live_runtime_contract_pass"),
                    "live_opening_contract_pass": lo_val,
                    "final_adapter": ev.get("final_adapter"),
                    "quality_class": ev.get("quality_class"),
                    "narration_summary_synthesized": _extract_metadata(row).get("narration_summary_synthesized"),
                }
            )
        return {
            "ok": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(matrix),
            "rows": matrix,
        }

    def fetch_langfuse_trace_scores(arguments: dict[str, Any]) -> dict[str, Any]:
        trace_id = str(arguments.get("trace_id") or "").strip()
        if not trace_id:
            return {"ok": False, "error": "trace_id required"}
        allow_non_live = bool(arguments.get("allow_non_live", False))
        raw = _langfuse_get_trace(trace_id)
        if raw.get("error"):
            return {"ok": False, "error": raw["error"], "details": raw}
        meta = _extract_metadata(raw)
        if not allow_non_live:
            origin = str(meta.get("trace_origin") or "").lower()
            tier = str(meta.get("execution_tier") or "").lower()
            cpf = bool(meta.get("canonical_player_flow"))
            if origin != "live_ui" or tier != "live" or not cpf:
                return {
                    "ok": False,
                    "error": "trace_filtered_as_non_live",
                    "reason": (
                        "trace_origin, execution_tier, or canonical_player_flow does not match "
                        "live evidence criteria (live_ui / live / true)"
                    ),
                    "actual": {
                        "trace_origin": meta.get("trace_origin"),
                        "execution_tier": meta.get("execution_tier"),
                        "canonical_player_flow": meta.get("canonical_player_flow"),
                    },
                    "hint": "Pass allow_non_live: true to inspect non-live traces",
                }
        det_scores, judge_scores = _extract_scores_split(raw)
        is_opening = _is_opening_trace(raw)
        lo_val = _live_opening_value(det_scores, raw)
        enriched_det = dict(det_scores)
        enriched_det["live_opening_contract_pass"] = lo_val
        sm = _first_score_metadata(raw) or {}
        opening_shape_diagnostics = {
            k: sm.get(k)
            for k in (
                "opening_shape_subgates",
                "opening_shape_failure_reasons",
                "scene_block_summary",
                "first_actor_block_index",
                "narrator_block_count",
'''
