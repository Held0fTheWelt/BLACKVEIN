"""Langfuse verify source segment: handler_judge_matrix_rows.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
            elif lo_val == 0.0:
                live_opening_str = "fail"
            else:
                live_opening_str = str(lo_val or "—")
            main_issue: str | None = None
            if lo_val == 0.0 and is_opening:
                main_issue = "live_opening_fail"
            elif det_scores.get("live_runtime_contract_pass") == 0.0:
                main_issue = "runtime_contract_fail"
            else:
                for jname in WOS_CATEGORICAL_JUDGES_ORDER:
                    cat = _jcat(jname)
                    if _judge_category_triggers_issue(jname, cat):
                        main_issue = jname
                        break
            row_out: dict[str, Any] = {
                "role": role,
                "trace_id": row.get("id"),
                "trace_name": row.get("name"),
                "is_opening_trace": is_opening,
                "live_opening": live_opening_str,
                "main_issue": main_issue,
            }
            sev_by_col: dict[str, Any] = {}
            for jname, col_key in _MATRIX_JUDGE_COLUMN_KEYS.items():
                cat = _jcat(jname)
                row_out[col_key] = cat
                sev_by_col[col_key] = _category_severity(jname, cat)
            row_out["judge_category_severity"] = sev_by_col
            row_out["llm_judge_interpretation"] = _build_llm_judge_interpretation(
                judge_scores,
                trace_context=str(row.get("name") or ""),
            )
            row_out["judge_score_coverage_gaps"] = _judge_score_coverage_gaps(
                is_opening=is_opening,
                judge_scores=judge_scores,
            )
            matrix.append(row_out)
        return {
            "ok": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "filter": {
                "trace_origin": trace_origin,
                "execution_tier": execution_tier,
                "canonical_player_flow": canonical_player_flow,
                "trace_name": trace_name_filter,
                "roles": roles,
                "limit_per_role": limit_per_role,
            },
            "count": len(matrix),
            "matrix": matrix,
            "evaluator_column_metadata": _evaluator_column_metadata(),
            "canonical_evaluator_definition_doc": LLM_AS_A_JUDGE_DOC_RELATIVE_PATH,
        }

    def build_opening_quality_context(arguments: dict[str, Any]) -> dict[str, Any]:
        trace_id = str(arguments.get("trace_id") or "").strip()
        if not trace_id:
            return {"ok": False, "error": "trace_id required"}
        include_raw_reasoning = bool(arguments.get("include_raw_reasoning", False))
        raw = _langfuse_get_trace(trace_id)
        if raw.get("error"):
            return {"ok": False, "error": raw["error"]}
        meta = _extract_metadata(raw)
        origin = str(meta.get("trace_origin") or "").lower()
        cpf = bool(meta.get("canonical_player_flow"))
        if origin != "live_ui" or not cpf:
            return {
                "ok": False,
                "error": "trace_not_live_evidence",
                "reason": (
                    "build_opening_quality_context only interprets live_ui traces "
'''
