"""Langfuse verify source segment: handler_quality_context_finish.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
            cat = (detail or {}).get("category")
            norm = _normalize_judge_category_label(jname, str(cat) if cat is not None else None)
            sev = _category_severity(jname, norm)
            entry["normalized_category"] = norm
            entry["category_severity"] = sev
            evidence_judges[jname] = entry
            if sev in {"failure", "warning"}:
                qualitative_concerns.append(f"{jname}:{norm or cat}({sev})")
            elif sev == "neutral":
                neutral_judge_labels.append(f"{jname}:{norm or cat}")
        enriched_det = dict(det_scores)
        enriched_det["live_opening_contract_pass"] = lo_val
        det_gate_fail = bool(lo_val != "not_applicable" and lo_val < 1.0) or live_runtime < 1.0
        return {
            "ok": True,
            "trace_id": trace_id,
            "is_opening_trace": is_opening,
            "trace_name": raw.get("name"),
            "ai_context_summary": " ".join(summary_parts),
            "recommended_next_card": recommended_next_card,
            "must_not_change": must_not_change,
            "evidence": {"deterministic": enriched_det, "judges": evidence_judges},
            "canonical_evaluator_definition_doc": LLM_AS_A_JUDGE_DOC_RELATIVE_PATH,
            "llm_judge_interpretation": _build_llm_judge_interpretation(
                judge_scores,
                trace_context=str(raw.get("name") or ""),
            ),
            "judge_score_coverage_gaps": _judge_score_coverage_gaps(
                is_opening=is_opening,
                judge_scores=judge_scores,
            ),
            "deterministic_vs_qualitative": {
                "deterministic_gate_failure": det_gate_fail,
                "qualitative_concerns": qualitative_concerns,
                "neutral_or_missing_evidence_labels": neutral_judge_labels,
            },
        }

    def summarize_runtime_aspect_matrix(arguments: dict[str, Any]) -> dict[str, Any]:
        return _runtime_aspect_matrix(arguments)

    def summarize_beat_realization_failures(arguments: dict[str, Any]) -> dict[str, Any]:
        matrix = _runtime_aspect_matrix(arguments)
        rows = [
            row for row in matrix.get("rows", [])
            if row.get("selected_beat") and row.get("beat_realized") not in {True, 1, 1.0}
        ]
        return {**matrix, "count": len(rows), "rows": rows, "summary_kind": "beat_realization_failures"}

    def summarize_narrator_npc_authority(arguments: dict[str, Any]) -> dict[str, Any]:
        matrix = _runtime_aspect_matrix(arguments)
        rows = [
            {
                key: row.get(key)
                for key in (
                    "session_id",
                    "trace_id",
                    "turn_number",
                    "raw_input",
                    "narrator_required",
                    "narrator_present",
                    "npc_policy",
                    "npc_takeover_detected",
                    "main_failure",
                    "recommended_repair",
                )
            }
            for row in matrix.get("rows", [])
        ]
        return {**matrix, "count": len(rows), "rows": rows, "summary_kind": "narrator_npc_authority"}

    def summarize_capability_realization(arguments: dict[str, Any]) -> dict[str, Any]:
'''
