"""Langfuse verify source segment: handler_judge_score_summary_start.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
                    },
                },
            },
            "categorical_judge_names": list(WOS_CATEGORICAL_JUDGES_ORDER),
            "canonical_evaluator_definition_doc": LLM_AS_A_JUDGE_DOC_RELATIVE_PATH,
            "llm_judge_interpretation": _build_llm_judge_interpretation(
                judge_scores,
                trace_context=str(raw.get("name") or ""),
            ),
            "judge_score_coverage_gaps": _judge_score_coverage_gaps(
                is_opening=is_opening,
                judge_scores=judge_scores,
            ),
            "evaluator_column_metadata": _evaluator_column_metadata(),
        }

    def summarize_opening_judge_scores(arguments: dict[str, Any]) -> dict[str, Any]:
        trace_origin = str(arguments.get("trace_origin") or "live_ui").strip()
        execution_tier = str(arguments.get("execution_tier") or "live").strip()
        cpf_arg = arguments.get("canonical_player_flow")
        canonical_player_flow = bool(cpf_arg) if isinstance(cpf_arg, bool) else True
        trace_nm = arguments.get("trace_name")
        trace_name_filter = (
            str(trace_nm).strip() if isinstance(trace_nm, str) and str(trace_nm).strip() else None
        )
        roles_raw = arguments.get("roles")
        roles = (
            [str(r).strip().lower() for r in roles_raw if str(r).strip()]
            if isinstance(roles_raw, list)
            else None
        )
        limit_per_role = int(arguments.get("limit_per_role") or 5)
        fetch_limit = min(max(limit_per_role * (len(roles) if roles else 2) * 4, 20), 100)
        rows = _langfuse_query_traces(
            limit=fetch_limit,
            trace_origin=trace_origin,
            canonical_player_flow=canonical_player_flow,
            execution_tier=execution_tier,
            trace_name=trace_name_filter,
        )
        if rows and isinstance(rows[0], dict) and rows[0].get("error"):
            return {"ok": False, "error": rows[0]["error"]}
        matrix: list[dict[str, Any]] = []
        role_counts: dict[str, int] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            meta = _extract_metadata(row)
            score_meta_row = _first_score_metadata(row)
            role = str(
                meta.get("selected_player_role") or score_meta_row.get("selected_player_role") or ""
            ).strip().lower() or None
            if roles is not None and role not in roles:
                continue
            r_key = role or "unknown"
            if role_counts.get(r_key, 0) >= limit_per_role:
                continue
            role_counts[r_key] = role_counts.get(r_key, 0) + 1
            det_scores, judge_scores = _extract_scores_split(row)
            lo_val = _live_opening_value(det_scores, row)
            is_opening = _is_opening_trace(row)

            def _jcat(jname: str, _j: dict = judge_scores) -> str | None:
                j = _j.get(jname)
                if not j:
                    return None
                return j.get("category")

            if lo_val == "not_applicable":
                live_opening_str = "not_applicable"
            elif lo_val == 1.0:
                live_opening_str = "pass"
'''
