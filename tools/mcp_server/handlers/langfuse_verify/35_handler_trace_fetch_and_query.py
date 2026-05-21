"""Langfuse verify source segment: handler_trace_fetch_and_query.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
            "ok": bool(world_engine_result["ok"] and ai_stack_result["ok"]),
            "world_engine": world_engine_result,
            "ai_stack": ai_stack_result,
        }

    def fetch_langfuse_trace(arguments: dict[str, Any]) -> dict[str, Any]:
        trace_id = str(arguments.get("langfuse_trace_id") or "").strip()
        if not trace_id:
            return {"error": "langfuse_trace_id required"}
        raw = _langfuse_get_trace(trace_id)
        if raw.get("error"):
            return {"ok": False, "error": raw["error"], "details": raw}
        evidence, sources = _extract_normalized_wos_evidence(raw)
        return {
            "ok": True,
            "trace": _trace_summary(raw),
            "raw_trace": raw,
            "normalized_wos_evidence": evidence,
            "evidence_sources": sources,
        }

    def query_langfuse_traces(arguments: dict[str, Any]) -> dict[str, Any]:
        limit = int(arguments.get("limit") or 10)
        trace_origin = arguments.get("trace_origin")
        cpf_raw = arguments.get("canonical_player_flow")
        canonical_player_flow = (
            bool(cpf_raw)
            if isinstance(cpf_raw, bool)
            else None
        )
        exec_tier = arguments.get("execution_tier")
        trace_nm = arguments.get("trace_name")
        env_arg = arguments.get("environment")
        rows = _langfuse_query_traces(
            limit=limit,
            trace_origin=str(trace_origin) if isinstance(trace_origin, str) else None,
            canonical_player_flow=canonical_player_flow,
            execution_tier=str(exec_tier).strip()
            if isinstance(exec_tier, str) and str(exec_tier).strip()
            else None,
            trace_name=str(trace_nm).strip()
            if isinstance(trace_nm, str) and str(trace_nm).strip()
            else None,
            environment=str(env_arg).strip()
            if isinstance(env_arg, str) and str(env_arg).strip()
            else None,
        )
        if rows and isinstance(rows[0], dict) and rows[0].get("error"):
            return {"ok": False, "error": rows[0]["error"], "details": rows[0].get("body")}
        return {"ok": True, "count": len(rows), "traces": [_trace_summary(x) for x in rows]}

    def assert_langfuse_opening_contract(arguments: dict[str, Any]) -> dict[str, Any]:
        mode = str(arguments.get("mode") or "live").strip().lower()
        if mode not in {"live", "test"}:
            return {"ok": False, "error": "mode must be live or test"}
        trace_id = str(arguments.get("langfuse_trace_id") or "").strip()
        if trace_id:
            raw = _langfuse_get_trace(trace_id)
            if raw.get("error"):
                return {"ok": False, "error": raw["error"], "missing_field": "trace"}
        else:
            origin = "live_ui" if mode == "live" else "pytest"
            rows = _langfuse_query_traces(
                limit=int(arguments.get("limit") or 10),
                trace_origin=origin,
                canonical_player_flow=True if mode == "live" else False,
            )
            if not rows or (isinstance(rows[0], dict) and rows[0].get("error")):
                return {"ok": False, "error": "no_matching_trace_found", "missing_field": "trace"}
            raw = rows[0]
            trace_id = str(raw.get("id") or "")

'''
