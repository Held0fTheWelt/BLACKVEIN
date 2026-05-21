"""Langfuse verify source segment: handler_runtime_summary_views.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
        matrix = _runtime_aspect_matrix(arguments)
        rows = [
            {
                key: row.get(key)
                for key in (
                    "session_id",
                    "trace_id",
                    "turn_number",
                    "raw_input",
                    "selected_capabilities",
                    "realized_capabilities",
                    "forbidden_capability_realized",
                    "main_failure",
                    "recommended_repair",
                )
            }
            for row in matrix.get("rows", [])
        ]
        return {**matrix, "count": len(rows), "rows": rows, "summary_kind": "capability_realization"}

    def summarize_visible_projection_origin_loss(arguments: dict[str, Any]) -> dict[str, Any]:
        matrix = _runtime_aspect_matrix(arguments)
        rows = [
            row for row in matrix.get("rows", [])
            if row.get("visible_origin_present") not in {True, 1, 1.0}
        ]
        return {**matrix, "count": len(rows), "rows": rows, "summary_kind": "visible_projection_origin_loss"}

    return {
        "run_projection_tests": run_projection_tests,
        "fetch_langfuse_trace": fetch_langfuse_trace,
        "query_langfuse_traces": query_langfuse_traces,
        "assert_langfuse_opening_contract": assert_langfuse_opening_contract,
        "summarize_live_opening_matrix": summarize_live_opening_matrix,
        "fetch_langfuse_trace_scores": fetch_langfuse_trace_scores,
        "summarize_opening_judge_scores": summarize_opening_judge_scores,
        "build_opening_quality_context": build_opening_quality_context,
        "summarize_runtime_aspect_matrix": summarize_runtime_aspect_matrix,
        "summarize_beat_realization_failures": summarize_beat_realization_failures,
        "summarize_narrator_npc_authority": summarize_narrator_npc_authority,
        "summarize_capability_realization": summarize_capability_realization,
        "summarize_visible_projection_origin_loss": summarize_visible_projection_origin_loss,
    }
'''
