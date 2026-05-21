"""Langfuse verify source segment: handler_quality_context_start.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
                    "with canonical_player_flow=true"
                ),
                "actual": {
                    "trace_origin": meta.get("trace_origin"),
                    "canonical_player_flow": meta.get("canonical_player_flow"),
                },
            }
        det_scores, judge_scores = _extract_scores_split(raw)
        is_opening = _is_opening_trace(raw)
        score_meta = _first_score_metadata(raw)
        role = str(
            meta.get("selected_player_role") or score_meta.get("selected_player_role") or ""
        ).strip().title() or "Unknown"
        lo_val = _live_opening_value(det_scores, raw)
        live_runtime = float(det_scores.get("live_runtime_contract_pass") or 0.0)

        def _jcat(name: str) -> str | None:
            j = judge_scores.get(name)
            return (j or {}).get("category") if j else None

        recommended_next_card: str | None = None
        must_not_change = [
            "Do not weaken live_opening_contract_pass",
            "Do not let LLM judge override deterministic actor-lane gates",
        ]
        summary_parts: list[str] = [f"This {role} live opening"] if is_opening else [f"This {role} live continuation trace"]
        if lo_val == "not_applicable":
            summary_parts.append(
                "is a continuation turn (turn 1+); live_opening_contract_pass is not evaluated here."
            )
        elif lo_val < 1.0:
            recommended_next_card = "RUNTIME-CONTRACT-01"
            summary_parts.append(
                "failed deterministic runtime gates — contract repair required before quality work."
            )
            must_not_change.append("Do not attempt style/content repairs until runtime gates pass")
        elif live_runtime < 1.0:
            recommended_next_card = "RUNTIME-CONTRACT-01"
            summary_parts.append("failed live_runtime_contract_pass — runtime repair required.")
        else:
            summary_parts.append("passed deterministic runtime gates")
            judge_issue_labels: list[str] = []
            detail_parts: list[str] = []
            for full in WOS_CATEGORICAL_JUDGES_ORDER:
                cat = _jcat(full)
                short = _JUDGE_DISPLAY_SHORT.get(full, full.replace("_", " "))
                if cat:
                    sev = _category_severity(full, cat)
                    detail_parts.append(f"{short}: {cat} ({sev})")
                if _judge_category_triggers_issue(full, cat):
                    judge_issue_labels.append(short.replace("-", "_").replace(" ", "_"))
                    if not recommended_next_card:
                        recommended_next_card = _JUDGE_TO_REPAIR_CARD.get(full)
                    if full == "actor_lane_narrative_violation_judge":
                        must_not_change.append(
                            "Deterministic actor-lane gate is authoritative — judge is advisory only"
                        )
            if detail_parts:
                summary_parts.append(f"({', '.join(detail_parts)})")
            if judge_issue_labels:
                summary_parts.append(
                    f". Main improvement targets: {', '.join(judge_issue_labels)}."
                )
            else:
                summary_parts.append(". No judge issues detected.")
        evidence_judges: dict[str, Any] = {}
        qualitative_concerns: list[str] = []
        neutral_judge_labels: list[str] = []
        for jname, detail in judge_scores.items():
            entry: dict[str, Any] = {"category": detail.get("category"), "value": detail.get("value")}
            if include_raw_reasoning and detail.get("reasoning"):
                entry["reasoning"] = detail["reasoning"]
'''
