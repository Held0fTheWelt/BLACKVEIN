"""LangGraph and LangChain orchestration status and settings functions."""

from __future__ import annotations

from .common import *
from .settings_validation import *

def get_orchestration_status(*, trace_id: str | None = None) -> dict[str, Any]:
    runtime_modes = get_runtime_modes()
    world_engine_settings = read_scope_settings("world_engine")
    langgraph_dependency_available = bool(LANGGRAPH_RUNTIME_EXPORT_AVAILABLE)
    langgraph_import_error: str | None = None
    if not langgraph_dependency_available:
        try:
            from ai_stack.langgraph.langgraph_runtime import ensure_langgraph_available

            ensure_langgraph_available()
            langgraph_dependency_available = True
        except Exception as exc:  # pragma: no cover - environment dependent
            langgraph_import_error = str(exc)
    bridge_available = True
    bridge_error: str | None = None
    parser_schema_health = {"runtime_structured_output": True, "writers_room_structured_output": True}
    try:
        from ai_stack.langchain import RuntimeTurnStructuredOutput, WritersRoomStructuredOutput

        RuntimeTurnStructuredOutput.model_validate_json('{"narrative_response":"ok"}')
        WritersRoomStructuredOutput.model_validate_json('{"review_notes":"ok","recommendations":[]}')
    except Exception as exc:  # pragma: no cover - dependency/runtime dependent
        bridge_available = False
        bridge_error = str(exc)
        parser_schema_health = {"runtime_structured_output": False, "writers_room_structured_output": False}

    session_items: list[dict[str, Any]] = []
    diagnostics_errors: list[dict[str, Any]] = []
    graph_error_count = 0
    fallback_marker_count = 0
    parser_error_count = 0
    node_counter: Counter[str] = Counter()
    try:
        sessions_payload = list_story_sessions(trace_id=trace_id)
        for row in list(sessions_payload.get("items") or [])[:3]:
            if not isinstance(row, dict):
                continue
            session_id = str(row.get("session_id") or "").strip()
            if not session_id:
                continue
            try:
                diag = get_story_diagnostics(session_id, trace_id=trace_id)
                session_items.append({"session_id": session_id, "diagnostics": diag})
                for nodes in _extract_values(diag, "nodes_executed"):
                    if isinstance(nodes, list):
                        for node_name in nodes:
                            if isinstance(node_name, str) and node_name:
                                node_counter[node_name] += 1
                for errs in _extract_values(diag, "graph_errors"):
                    if isinstance(errs, list):
                        graph_error_count += len(errs)
                for marks in _extract_values(diag, "fallback_markers"):
                    if isinstance(marks, list):
                        fallback_marker_count += len(marks)
                parser_error_count += len(_extract_parser_errors(diag))
            except GameServiceError as exc:
                diagnostics_errors.append({"session_id": session_id, "message": str(exc), "status_code": exc.status_code})
    except GameServiceError as exc:
        diagnostics_errors.append({"session_id": None, "message": str(exc), "status_code": exc.status_code})
    langgraph_state = "healthy"
    if not langgraph_dependency_available:
        langgraph_state = "blocked"
    elif graph_error_count > 0 or fallback_marker_count > 0 or diagnostics_errors:
        langgraph_state = "degraded"
    langchain_state = "healthy"
    if not bridge_available:
        langchain_state = "blocked"
    elif parser_error_count > 0:
        langchain_state = "degraded"
    overall_state = "healthy"
    if "blocked" in {langgraph_state, langchain_state}:
        overall_state = "blocked"
    elif "degraded" in {langgraph_state, langchain_state}:
        overall_state = "degraded"
    guidance: list[dict[str, str]] = []
    if not langgraph_dependency_available:
        guidance.append(
            {
                "severity": "blocked",
                "message": "LangGraph dependency/runtime export is unavailable.",
                "consequence": "Primary graph execution cannot run as expected.",
                "next_step": "Review orchestration diagnostics and fallback posture before enabling strict runtime paths.",
                "fix_path": "/manage/ai-orchestration",
            }
        )
    if parser_error_count > 0:
        guidance.append(
            {
                "severity": "degraded",
                "message": "Recent parser/schema failures were observed.",
                "consequence": "Structured orchestration output reliability is reduced.",
                "next_step": "Keep corrective feedback enabled and inspect recent diagnostics errors.",
                "fix_path": "/manage/ai-orchestration",
            }
        )
    if str(world_engine_settings.get("runtime_diagnostics_verbosity", "operator")) == "debug":
        guidance.append(
            {
                "severity": "info",
                "message": "Diagnostics verbosity is set to debug (bounded debug-only posture).",
                "consequence": "Operator output can become noisy during normal operation.",
                "next_step": "Return to operator or detailed verbosity when troubleshooting is complete.",
                "fix_path": "/manage/runtime-settings",
            }
        )

    return {
        "overall_state": overall_state,
        "status_semantics": STATUS_SEMANTICS,
        "langgraph": {
            "state": langgraph_state,
            "dependency_available": langgraph_dependency_available,
            "import_error": langgraph_import_error,
            "runtime_profile": runtime_modes.get("runtime_profile"),
            "validation_execution_mode": runtime_modes.get("validation_execution_mode"),
            "max_retry_attempts": world_engine_settings.get("max_retry_attempts", 1),
            "enable_corrective_feedback": bool(world_engine_settings.get("enable_corrective_feedback", True)),
            "runtime_diagnostics_verbosity": world_engine_settings.get("runtime_diagnostics_verbosity", "operator"),
            "fallback_posture": {
                "fallback_marker_count_recent": fallback_marker_count,
                "graph_error_count_recent": graph_error_count,
            },
            "recent_execution_summary": {
                "sessions_sampled": len(session_items),
                "top_nodes_executed": node_counter.most_common(8),
                "diagnostics_errors": diagnostics_errors,
            },
        },
        "langchain": {
            "state": langchain_state,
            "bridge_available": bridge_available,
            "bridge_error": bridge_error,
            "runtime_adapter_bridge_available": bridge_available,
            "retriever_bridge_available": bridge_available,
            "writers_room_bridge_available": bridge_available,
            "tool_bridge_available": bridge_available,
            "parser_schema_health": parser_schema_health,
            "recent_parser_failure_count": parser_error_count,
        },
        "controls": {
            "allowed_runtime_profiles": sorted(_RUNTIME_PROFILE_ALLOWED),
            "allowed_runtime_diagnostics_verbosity": sorted(_VERBOSITY_ALLOWED),
            "max_retry_attempts_range": {"min": 0, "max": 5},
        },
        "comparison": {
            "expected_healthy": {
                "langgraph_dependency_available": True,
                "langchain_bridge_available": True,
                "recent_graph_errors": 0,
                "recent_parser_failures": 0,
            },
            "active": {
                "runtime_profile": runtime_modes.get("runtime_profile"),
                "runtime_diagnostics_verbosity": world_engine_settings.get("runtime_diagnostics_verbosity", "operator"),
                "max_retry_attempts": world_engine_settings.get("max_retry_attempts", 1),
                "recent_graph_errors": graph_error_count,
                "recent_parser_failures": parser_error_count,
            },
        },
        "guidance": guidance,
    }


def get_orchestration_settings() -> dict[str, Any]:
    runtime_modes = get_runtime_modes()
    world_engine_settings = read_scope_settings("world_engine")
    return {
        "runtime_profile": runtime_modes.get("runtime_profile"),
        "enable_corrective_feedback": bool(world_engine_settings.get("enable_corrective_feedback", True)),
        "runtime_diagnostics_verbosity": world_engine_settings.get("runtime_diagnostics_verbosity", "operator"),
        "max_retry_attempts": world_engine_settings.get("max_retry_attempts", 1),
    }


def update_orchestration_settings(payload: dict[str, Any], actor: str) -> dict[str, Any]:
    modes_patch, world_engine_patch = _validate_orchestration_settings_patch(payload)
    if modes_patch:
        update_runtime_modes(modes_patch, actor)
    if world_engine_patch:
        update_scope_settings("world_engine", world_engine_patch, actor)
    return get_orchestration_settings()


__all__ = (
    'get_orchestration_status',
    'get_orchestration_settings',
    'update_orchestration_settings',
)
