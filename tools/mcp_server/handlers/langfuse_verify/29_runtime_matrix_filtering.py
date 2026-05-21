"""Langfuse verify source segment: runtime_matrix_filtering.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
    if trace_origin is not None:
        actual_origin = str(
            meta.get("trace_origin") or path_summary.get("trace_origin") or ""
        ).strip().lower()
        if actual_origin != str(trace_origin).strip().lower():
            return False
    execution_tier = arguments.get("execution_tier")
    if execution_tier is not None:
        actual_tier = str(
            meta.get("execution_tier") or path_summary.get("execution_tier") or ""
        ).strip().lower()
        if actual_tier != str(execution_tier).strip().lower():
            return False
    environment = arguments.get("environment")
    if environment is not None:
        env_target = str(environment).strip().lower()
        env_candidates = (
            raw_trace.get("environment"),
            meta.get("environment"),
            meta.get("langfuse_environment"),
            meta.get("wos_langfuse_environment"),
            path_summary.get("environment"),
            path_summary.get("langfuse_environment"),
        )
        if not any(str(value or "").strip().lower() == env_target for value in env_candidates):
            return False
    if arguments.get("canonical_player_flow") is not None:
        expected = bool(arguments.get("canonical_player_flow"))
        actual = meta.get("canonical_player_flow")
        if actual is None:
            actual = path_summary.get("canonical_player_flow")
        if bool(actual) is not expected:
            return False
    return True


def _runtime_aspect_matrix(arguments: dict[str, Any]) -> dict[str, Any]:
    trace_id = str(arguments.get("trace_id") or arguments.get("langfuse_trace_id") or "").strip()
    if trace_id:
        raw_rows = [_langfuse_get_trace(trace_id)]
    else:
        raw_rows = _langfuse_query_traces(
            limit=int(arguments.get("limit") or 20),
            trace_origin=arguments.get("trace_origin"),
            canonical_player_flow=arguments.get("canonical_player_flow"),
            execution_tier=arguments.get("execution_tier"),
            environment=arguments.get("environment"),
            trace_name=arguments.get("trace_name"),
            trace_names=("backend.turn.execute", "world-engine.turn.execute"),
        )
        raw_rows = [
            _langfuse_get_trace(str(row.get("id") or row.get("trace_id") or "").strip())
            if isinstance(row, dict) and not row.get("observations")
            else row
            for row in raw_rows
            if isinstance(row, dict)
        ]
        if not raw_rows and any(
            arguments.get(key) is not None
            for key in ("trace_origin", "execution_tier", "environment", "canonical_player_flow")
        ):
            broad_rows = _langfuse_query_traces(
                limit=int(arguments.get("limit") or 20),
                trace_origin=None,
                canonical_player_flow=None,
                execution_tier=None,
                environment=None,
                trace_name=arguments.get("trace_name"),
                trace_names=("backend.turn.execute", "world-engine.turn.execute"),
            )
            raw_rows = [
                _langfuse_get_trace(str(row.get("id") or row.get("trace_id") or "").strip())
'''
