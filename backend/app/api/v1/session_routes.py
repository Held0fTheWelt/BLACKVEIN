"""W3.1 — Session management API routes (non-authoritative in-process W2 bridge).

**Live play runs in the World Engine**, not in this Flask process. These routes expose
volatile in-memory ``SessionState`` for operators/MCP/tests; they must not be treated as
an equivalent live runtime (see ``docs/technical/architecture/backend-runtime-classification.md``).

- POST /api/v1/sessions — create in-process session (includes explicit JSON warnings)
- GET … — snapshots/diagnostics (volatile; token may be required)
- POST …/turns — proxies execution to World-Engine story runtime host
"""

from flask import request, jsonify, g
from datetime import datetime, timezone
import json

from app.api.v1 import api_v1_bp
from app.api.v1.auth import require_mcp_service_token
from app.services.session_service import (
    create_session,
    get_session,
    execute_turn,
    get_session_logs,
    get_session_state,
)
from app.runtime.session_start import SessionStartError
from app.runtime.session_store import get_session as get_runtime_session
from app.content.compiler import compile_module
from app.services.game_service import (
    GameServiceError,
    create_story_session,
    execute_story_turn as execute_story_turn_in_engine,
    get_story_diagnostics,
    get_story_state,
)
from app.observability.trace import get_trace_id
from app.observability.audit_log import log_world_engine_bridge
from app.runtime.input_interpreter import interpret_player_input

SESSION_START_ERROR_STATUS = {
    "module_not_found": 404,
    "module_invalid": 422,
    "no_start_scene": 422,
}


@api_v1_bp.route("/sessions", methods=["POST"])
def create_new_session():
    """Create a new story session.

    Request body:
        {
            "module_id": "god_of_carnage"
        }

    Response (201 Created):
        {
            "session_id": "...",
            "module_id": "god_of_carnage",
            "module_version": "1.0.0",
            "current_scene_id": "...",
            "status": "active",
            "turn_counter": 0,
            "canonical_state": {...},
            "execution_mode": "mock",
            "adapter_name": "mock",
            "seed": null,
            "created_at": "2026-03-29T...",
            "updated_at": "2026-03-29T...",
            "metadata": {},
            "context_layers": {...},
            "degraded_state": {...}
        }

    Errors:
        400: Missing module_id
        404: Module not found
        422: Module validation failed
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400
    if not isinstance(data, dict):
        return jsonify({"error": "JSON body must be an object"}), 400
    module_id = data.get("module_id")

    if not module_id:
        return jsonify({"error": "module_id is required"}), 400

    try:
        session = create_session(module_id)
        body = session.model_dump(mode="json")
        body["warnings"] = [
            "backend_in_process_session_not_authoritative_live_runtime",
            "authoritative_runs_execute_in_world_engine_play_service",
            "in_memory_session_state_is_volatile",
        ]
        return jsonify(body), 201
    except SessionStartError as exc:
        return jsonify({"error": str(exc)}), SESSION_START_ERROR_STATUS.get(exc.reason, 422)
    except Exception as e:
        # Keep explicit fallback for unexpected failures.
        return jsonify({"error": str(e)}), 500


@api_v1_bp.route("/sessions/<session_id>", methods=["GET"])
@require_mcp_service_token
def get_session_by_id(session_id):
    """Retrieve session snapshot (A1.3 operator endpoint).

    Returns session metadata + canonical state snapshot.
    Requires: Authorization: Bearer <MCP_SERVICE_TOKEN>
    """
    # Get session from runtime store
    session = get_runtime_session(session_id)
    if not session:
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": f"Session {session_id} not found"
            }
        }), 404

    # Get the session state
    state = session.current_runtime_state

    # Determine if canonical_state needs truncation (50KB threshold)
    import json
    state_json = json.dumps(state.canonical_state)
    state_size = len(state_json.encode('utf-8'))
    is_truncated = state_size > 50 * 1024

    response = {
        "session_id": session_id,
        "module_id": session.module.metadata.module_id,
        "module_version": session.module.metadata.version,
        "current_scene_id": state.current_scene_id,
        "status": state.status.value,
        "turn_counter": state.turn_counter,
        "execution_mode": state.execution_mode,
        "adapter_name": state.adapter_name,
        "canonical_state": state.canonical_state if not is_truncated else None,
        "canonical_state_truncated": is_truncated,
        "warnings": [
            "in_memory_session_state_is_volatile",
            "backend_session_snapshot_not_world_engine_run",
        ],
    }
    metadata = state.metadata if isinstance(state.metadata, dict) else {}
    engine_story_session_id = metadata.get("world_engine_story_session_id")
    if isinstance(engine_story_session_id, str) and engine_story_session_id.strip():
        trace_id = g.get("trace_id") or get_trace_id()
        try:
            authoritative_state = get_story_state(engine_story_session_id, trace_id=trace_id)
            if isinstance(authoritative_state, dict):
                response["world_engine_story_session_id"] = engine_story_session_id
                response["current_scene_id"] = authoritative_state.get("current_scene_id", response["current_scene_id"])
                response["turn_counter"] = authoritative_state.get("turn_counter", response["turn_counter"])
                response["authoritative_state"] = authoritative_state
                response["warnings"] = [
                    "world_engine_story_runtime_authoritative_snapshot",
                    "backend_in_memory_snapshot_retained_for_compatibility",
                ]
        except GameServiceError as exc:
            response["bridge_error"] = {
                "failure_class": "world_engine_unreachable",
                "message": str(exc),
                "status_code": exc.status_code,
            }
            response["warnings"].append("world_engine_authoritative_snapshot_unavailable")

    return jsonify(response), 200


@api_v1_bp.route("/sessions/<session_id>/diagnostics", methods=["GET"])
@require_mcp_service_token
def get_session_diagnostics(session_id):
    """Get diagnostics bundle for a session (A1.3 operator endpoint).

    Returns future-proof diagnostics envelope with current runtime indicators.
    Requires: Authorization: Bearer <MCP_SERVICE_TOKEN>
    """
    # Get session from runtime store
    session = get_runtime_session(session_id)
    if not session:
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": f"Session {session_id} not found"
            }
        }), 404

    # Get the session state
    state = session.current_runtime_state

    response = {
        "session_id": session_id,
        "turn_counter": state.turn_counter,
        "current_scene_id": state.current_scene_id,
        "capabilities": {
            "has_turn_history": False,
            "has_guard_outcome": False,
            "has_trace_ids": False
        },
        "guard": {
            "outcome": None,
            "rejected_reasons": [],
            "last_error": None
        },
        "trace": {
            "trace_ids": []
        },
        "warnings": [
            "in_memory_session_state_is_volatile",
            "diagnostics_limited_to_current_runtime",
            "guard_and_trace_not_recorded_yet",
            "backend_diagnostics_not_world_engine_run",
        ],
    }
    metadata = state.metadata if isinstance(state.metadata, dict) else {}
    engine_story_session_id = metadata.get("world_engine_story_session_id")
    if isinstance(engine_story_session_id, str) and engine_story_session_id.strip():
        trace_id = g.get("trace_id") or get_trace_id()
        try:
            authoritative = get_story_diagnostics(engine_story_session_id, trace_id=trace_id)
            if isinstance(authoritative, dict):
                diagnostics_rows = authoritative.get("diagnostics", [])
                response = {
                    "session_id": session_id,
                    "world_engine_story_session_id": engine_story_session_id,
                    "turn_counter": authoritative.get("turn_counter", state.turn_counter),
                    "current_scene_id": (authoritative.get("committed_state", {}) or {}).get(
                        "current_scene_id",
                        state.current_scene_id,
                    ),
                    "committed_state": authoritative.get("committed_state", {}),
                    "diagnostics": diagnostics_rows if isinstance(diagnostics_rows, list) else [],
                    "trace_id": trace_id,
                    "warnings": ["world_engine_story_runtime_authoritative_diagnostics"],
                }
                return jsonify(response), 200
        except GameServiceError as exc:
            response["bridge_error"] = {
                "failure_class": "world_engine_unreachable",
                "message": str(exc),
                "status_code": exc.status_code,
            }
            response["warnings"].append("world_engine_authoritative_diagnostics_unavailable")

    return jsonify(response), 200


@api_v1_bp.route("/sessions/<session_id>/capability-audit", methods=["GET"])
@require_mcp_service_token
def get_session_capability_audit(session_id):
    """Expose capability invocation audit for governance-facing review."""
    runtime_session = get_runtime_session(session_id)
    if not runtime_session:
        return jsonify(
            {
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Session {session_id} not found",
                }
            }
        ), 404

    state = runtime_session.current_runtime_state
    metadata = state.metadata if isinstance(state.metadata, dict) else {}
    engine_story_session_id = metadata.get("world_engine_story_session_id")
    if not engine_story_session_id:
        return jsonify(
            {
                "session_id": session_id,
                "audit": [],
                "total": 0,
                "warnings": [
                    "world_engine_story_session_not_initialized",
                    "capability_audit_not_available_before_first_turn",
                ],
            }
        ), 200

    trace_id = g.get("trace_id") or get_trace_id()
    try:
        diagnostics = get_story_diagnostics(engine_story_session_id, trace_id=trace_id)
    except GameServiceError as exc:
        return jsonify(
            {
                "session_id": session_id,
                "world_engine_story_session_id": engine_story_session_id,
                "audit": [],
                "total": 0,
                "trace_id": trace_id,
                "bridge_error": {
                    "failure_class": "world_engine_unreachable",
                    "message": str(exc),
                    "status_code": exc.status_code,
                },
            }
        ), 200

    entries = diagnostics.get("diagnostics", []) if isinstance(diagnostics, dict) else []
    audit_rows: list[dict] = []
    for entry in entries:
        graph = entry.get("graph", {}) if isinstance(entry, dict) else {}
        capability_audit = graph.get("capability_audit", []) if isinstance(graph, dict) else []
        if isinstance(capability_audit, list):
            for row in capability_audit:
                if isinstance(row, dict):
                    audit_rows.append(row)

    return jsonify(
        {
            "session_id": session_id,
            "world_engine_story_session_id": engine_story_session_id,
            "trace_id": trace_id,
            "audit": audit_rows[-100:],
            "total": len(audit_rows),
        }
    ), 200


@api_v1_bp.route("/sessions/<session_id>/turns", methods=["POST"])
def execute_session_turn(session_id):
    """Execute a turn in World-Engine-hosted story runtime."""
    runtime_session = get_runtime_session(session_id)
    if not runtime_session:
        return jsonify({"error": "Session not found"}), 404

    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400

    player_input = (data.get("player_input") or data.get("operator_input") or data.get("input") or "").strip()
    if not player_input:
        return jsonify({"error": "player_input is required"}), 400
    local_interpretation = interpret_player_input(player_input)

    state = runtime_session.current_runtime_state
    metadata = state.metadata if isinstance(state.metadata, dict) else {}
    engine_story_session_id = metadata.get("world_engine_story_session_id")
    trace_id = g.get("trace_id") or get_trace_id()

    try:
        if not engine_story_session_id:
            compiled = compile_module(state.module_id)
            created = create_story_session(
                module_id=state.module_id,
                runtime_projection=compiled.runtime_projection.model_dump(mode="json"),
                trace_id=trace_id,
            )
            engine_story_session_id = created["session_id"]
            metadata["world_engine_story_session_id"] = engine_story_session_id
            state.metadata = metadata
            log_world_engine_bridge(
                trace_id,
                operation="create_story_session",
                backend_session_id=session_id,
                world_engine_story_session_id=engine_story_session_id,
                outcome="ok",
            )

        turn = execute_story_turn_in_engine(
            session_id=engine_story_session_id,
            player_input=player_input,
            trace_id=trace_id,
        )
        diagnostics = get_story_diagnostics(engine_story_session_id, trace_id=trace_id)
        current_state = get_story_state(engine_story_session_id, trace_id=trace_id)
    except GameServiceError as exc:
        log_world_engine_bridge(
            trace_id,
            operation="execute_or_fetch_story",
            backend_session_id=session_id,
            world_engine_story_session_id=engine_story_session_id if isinstance(engine_story_session_id, str) else None,
            outcome="error",
            failure_class="world_engine_unreachable",
            status_code=exc.status_code,
            message=str(exc),
        )
        return jsonify(
            {
                "session_id": session_id,
                "trace_id": trace_id,
                "failure_class": "world_engine_unreachable",
                "message": str(exc),
                "status_hint": exc.status_code,
            }
        ), 502

    log_world_engine_bridge(
        trace_id,
        operation="execute_story_turn",
        backend_session_id=session_id,
        world_engine_story_session_id=engine_story_session_id,
        outcome="ok",
    )

    return jsonify(
        {
            "session_id": session_id,
            "trace_id": trace_id,
            "world_engine_story_session_id": engine_story_session_id,
            "turn": turn.get("turn"),
            "state": current_state,
            "diagnostics": diagnostics,
            "backend_interpretation_preview": local_interpretation.model_dump(mode="json"),
            "warnings": [
                "backend_proxying_to_world_engine_story_runtime",
                "backend_local_authoritative_turn_execution_deprecated",
            ],
        }
    ), 200


@api_v1_bp.route("/sessions/<session_id>/logs", methods=["GET"])
@require_mcp_service_token
def get_session_event_logs(session_id):
    """Retrieve event logs for a session (A1.3 operator endpoint).

    Returns turn summaries / event history (always empty in A1.3).
    Requires: Authorization: Bearer <MCP_SERVICE_TOKEN>
    """
    # Get session from runtime store to verify it exists
    session = get_runtime_session(session_id)
    if not session:
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": f"Session {session_id} not found"
            }
        }), 404

    response = {
        "session_id": session_id,
        "events": [],
        "total": 0,
        "warnings": [
            "history_not_available_in_current_runtime",
            "in_memory_session_state_is_volatile",
            "backend_logs_not_world_engine_transcript",
        ],
    }

    return jsonify(response), 200


@api_v1_bp.route("/sessions/<session_id>/state", methods=["GET"])
@require_mcp_service_token
def get_session_canonical_state(session_id):
    """Get canonical world state for a session (A1.3 operator endpoint).

    Returns canonical state + current scene + minimal wrapper.
    Requires: Authorization: Bearer <MCP_SERVICE_TOKEN>
    """
    # Get session from runtime store
    session = get_runtime_session(session_id)
    if not session:
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": f"Session {session_id} not found"
            }
        }), 404

    # Get the session state
    state = session.current_runtime_state

    # Determine if canonical_state needs truncation (50KB threshold)
    import json
    state_json = json.dumps(state.canonical_state)
    state_size = len(state_json.encode('utf-8'))
    is_truncated = state_size > 50 * 1024

    response = {
        "session_id": session_id,
        "current_scene_id": state.current_scene_id,
        "canonical_state": state.canonical_state if not is_truncated else None,
        "canonical_state_truncated": is_truncated,
        "warnings": [
            "in_memory_session_state_is_volatile",
            "backend_state_not_world_engine_run",
        ],
    }
    metadata = state.metadata if isinstance(state.metadata, dict) else {}
    engine_story_session_id = metadata.get("world_engine_story_session_id")
    if isinstance(engine_story_session_id, str) and engine_story_session_id.strip():
        trace_id = g.get("trace_id") or get_trace_id()
        try:
            authoritative_state = get_story_state(engine_story_session_id, trace_id=trace_id)
            if isinstance(authoritative_state, dict):
                response = {
                    "session_id": session_id,
                    "world_engine_story_session_id": engine_story_session_id,
                    "current_scene_id": authoritative_state.get("current_scene_id", state.current_scene_id),
                    "turn_counter": authoritative_state.get("turn_counter", state.turn_counter),
                    "committed_state": authoritative_state.get("committed_state", {}),
                    "runtime_projection": authoritative_state.get("runtime_projection"),
                    "warnings": ["world_engine_story_runtime_authoritative_state"],
                }
                return jsonify(response), 200
        except GameServiceError as exc:
            response["bridge_error"] = {
                "failure_class": "world_engine_unreachable",
                "message": str(exc),
                "status_code": exc.status_code,
            }
            response["warnings"].append("world_engine_authoritative_state_unavailable")

    return jsonify(response), 200


@api_v1_bp.route("/sessions/<session_id>/export", methods=["GET"])
@require_mcp_service_token
def export_session_bundle(session_id):
    """Export session bundle for diagnostics and reproducibility (A2 operator endpoint).

    Returns a compact JSON bundle containing snapshot, diagnostics, logs, and metadata.
    Protected by MCP_SERVICE_TOKEN.
    """
    # Get session
    session = get_runtime_session(session_id)
    if not session:
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": f"Session {session_id} not found"
            }
        }), 404

    state = session.current_runtime_state
    trace_id = g.get("trace_id") or get_trace_id()

    # Determine if canonical_state needs truncation (50KB threshold)
    state_json = json.dumps(state.canonical_state)
    state_size = len(state_json.encode('utf-8'))
    is_truncated = state_size > 50 * 1024

    # Build export bundle
    bundle = {
        "session_snapshot": {
            "session_id": session_id,
            "module_id": session.module.metadata.module_id,
            "module_version": session.module.metadata.version,
            "current_scene_id": state.current_scene_id,
            "status": state.status.value,
            "turn_counter": state.turn_counter,
            "execution_mode": state.execution_mode,
            "adapter_name": state.adapter_name,
            "canonical_state": state.canonical_state if not is_truncated else None,
            "canonical_state_truncated": is_truncated,
            "warnings": [
                "in_memory_session_state_is_volatile",
                "backend_snapshot_not_world_engine_run",
            ],
        },
        "diagnostics": {
            "session_id": session_id,
            "turn_counter": state.turn_counter,
            "current_scene_id": state.current_scene_id,
            "capabilities": {
                "has_turn_history": False,
                "has_guard_outcome": False,
                "has_trace_ids": False
            },
            "guard": {
                "outcome": None,
                "rejected_reasons": [],
                "last_error": None
            },
            "trace": {
                "trace_ids": []
            },
            "warnings": [
                "in_memory_session_state_is_volatile",
                "diagnostics_limited_to_current_runtime",
                "guard_and_trace_not_recorded_yet",
                "backend_diagnostics_not_world_engine_run",
            ],
        },
        "logs": {
            "events": [],
            "total": 0,
            "warnings": [
                "history_not_available_in_current_runtime",
                "in_memory_session_state_is_volatile",
                "backend_logs_not_world_engine_transcript",
            ],
        },
        "meta": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "warnings": [
                "in_memory_session_state_is_volatile",
                "audit_logs_not_persisted_in_a2"
            ]
        }
    }

    return jsonify(bundle), 200
