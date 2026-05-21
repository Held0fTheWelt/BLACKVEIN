"""Langfuse verify source segment: handler_opening_contract_assertions.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
        ev, _src = _extract_normalized_wos_evidence(raw)
        failures: list[dict[str, Any]] = []

        def fail(rule: str, message: str, field: str, actual: Any) -> None:
            failures.append(
                {"rule": rule, "message": message, "missing_field": field, "actual": actual}
            )

        if mode == "live":
            if str(ev.get("trace_origin") or "").lower() != "live_ui":
                fail("trace_origin == live_ui", "live trace origin mismatch", "normalized.trace_origin", ev.get("trace_origin"))
            if str(ev.get("execution_tier") or "").lower() != "live":
                fail("execution_tier == live", "execution tier mismatch", "normalized.execution_tier", ev.get("execution_tier"))
            if bool(ev.get("canonical_player_flow")) is not True:
                fail("canonical_player_flow == true", "canonical flow mismatch", "normalized.canonical_player_flow", ev.get("canonical_player_flow"))
            role = str(ev.get("selected_player_role") or "").strip().lower()
            if not role:
                fail("selected_player_role present", "role missing", "normalized.selected_player_role", ev.get("selected_player_role"))
            if str(ev.get("human_actor_id") or "").lower() != role:
                fail("human_actor_id == selected_player_role", "human actor mismatch", "normalized.human_actor_id", ev.get("human_actor_id"))
            for score_name in (
                "opening_shape_contract_pass",
                "live_runtime_contract_pass",
                "live_opening_contract_pass",
            ):
                if float(ev.get(score_name) or 0.0) != 1.0:
                    fail(f"{score_name} == 1", "score mismatch", f"scores.{score_name}", ev.get(score_name))
            if str(ev.get("final_adapter") or "").lower() == "ldss_fallback":
                fail("final_adapter != ldss_fallback", "fallback adapter used", "normalized.final_adapter", ev.get("final_adapter"))
            if str(ev.get("quality_class") or "").lower() in {"degraded", "failed"}:
                fail("quality_class not degraded/failed", "quality class degraded", "normalized.quality_class", ev.get("quality_class"))
        else:
            if str(ev.get("trace_origin") or "").lower() != "pytest":
                fail("trace_origin == pytest", "test trace origin mismatch", "normalized.trace_origin", ev.get("trace_origin"))
            if bool(ev.get("canonical_player_flow")) is not False:
                fail("canonical_player_flow == false", "test flow mismatch", "normalized.canonical_player_flow", ev.get("canonical_player_flow"))
            if float(ev.get("live_opening_contract_pass") or 0.0) != 0.0:
                fail(
                    "live_opening_contract_pass == 0",
                    "test trace has live opening pass",
                    "scores.live_opening_contract_pass",
                    ev.get("live_opening_contract_pass"),
                )

        return {
            "ok": len(failures) == 0,
            "trace_id": trace_id,
            "mode": mode,
            "failures": failures,
            "trace": _trace_summary(raw),
            "assertion_count": len(_assertions_for_mode(mode)),
        }

    def summarize_live_opening_matrix(arguments: dict[str, Any]) -> dict[str, Any]:
        limit = int(arguments.get("limit") or 20)
        exec_tier = arguments.get("execution_tier")
        trace_nm = arguments.get("trace_name")
        rows = _langfuse_query_traces(
            limit=limit,
            trace_origin="live_ui",
            canonical_player_flow=True,
            execution_tier=str(exec_tier).strip()
            if isinstance(exec_tier, str) and str(exec_tier).strip()
            else None,
            trace_name=str(trace_nm).strip()
            if isinstance(trace_nm, str) and str(trace_nm).strip()
            else None,
        )
        if rows and isinstance(rows[0], dict) and rows[0].get("error"):
            return {"ok": False, "error": rows[0]["error"]}
        matrix: list[dict[str, Any]] = []
        for row in rows:
'''
