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
import hashlib
import json

from app.api.v1 import api_v1_bp
from flask_jwt_extended import get_jwt_identity, jwt_required

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
from app.observability.trace import get_langfuse_trace_id, get_trace_id
from app.observability.audit_log import log_world_engine_bridge
from app.observability.langfuse_adapter import LangfuseAdapter
from app.runtime.input_interpreter import interpret_player_input
from app.config.route_constants import route_session_config, route_status_codes


def _validate_world_engine_turn_contract(turn: dict, trace_id: str | None = None) -> None:
    """PHASE 2: Validate world-engine turn response against canonical contract.

    Ensures all required fields are present. Logs warnings if optional fields are missing.
    Raises GameServiceError if critical fields are missing.
    """
    if not isinstance(turn, dict):
        raise GameServiceError("World-engine turn response is not a dict")

    required_fields = {
        "turn_number": int,
        "turn_kind": str,
        "interpreted_input": dict,
        "narrative_commit": dict,
        "validation_outcome": dict,
        "visible_output_bundle": dict,
    }

    optional_fields = {
        "trace_id": str,
        "raw_input": str,
        "graph": dict,
        "model_route": dict,
        "retrieval": dict,
    }

    missing_required = []
    for field, expected_type in required_fields.items():
        if field not in turn:
            missing_required.append(field)
        elif not isinstance(turn.get(field), expected_type):
            missing_required.append(f"{field} (wrong type: {type(turn.get(field)).__name__})")

    if missing_required:
        msg = f"World-engine turn missing required fields: {', '.join(missing_required)}"
        raise GameServiceError(msg)

    # Warn about missing optional fields (but don't fail)
    missing_optional = [f for f in optional_fields if f not in turn]
    if missing_optional:
        import sys
        print(
            f"[WARN] World-engine turn missing optional fields: {', '.join(missing_optional)}",
            file=sys.stderr,
        )


@api_v1_bp.route("/sessions", methods=["POST"])
@jwt_required(optional=True)
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
        owner_id = get_jwt_identity()
        metadata_updates: dict[str, str] | None = None
        if owner_id is not None:
            metadata_updates = {"play_shell_owner_user_id": str(owner_id)}
        session = create_session(module_id, metadata_updates=metadata_updates)
        body = session.model_dump(mode="json")
        body["warnings"] = [
            "backend_in_process_session_not_authoritative_live_runtime",
            "authoritative_runs_execute_in_world_engine_play_service",
            "in_memory_session_state_is_volatile",
        ]
        return jsonify(body), 201
    except SessionStartError as exc:
        status_code = (
            route_status_codes.not_found if exc.reason == "module_not_found"
            else route_status_codes.unprocessable_entity
        )
        return jsonify({"error": str(exc)}), status_code
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


@api_v1_bp.route("/sessions/<session_id>/play-operator-bundle", methods=["GET"])
@jwt_required()
def get_play_operator_bundle(session_id):
    """JWT-scoped operator snapshot for the in-process play shell (no MCP token).

    Requires the session to have been created with the same JWT identity
    (``play_shell_owner_user_id`` in session metadata).
    """
    owner_claim = get_jwt_identity()
    if owner_claim is None:
        return (
            jsonify({"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}),
            401,
        )

    runtime_session = get_runtime_session(session_id)
    if not runtime_session:
        return (
            jsonify({"error": {"code": "NOT_FOUND", "message": "Session not found"}}),
            404,
        )

    state = runtime_session.current_runtime_state
    meta = state.metadata if isinstance(state.metadata, dict) else {}
    bound_owner = meta.get("play_shell_owner_user_id")
    if bound_owner is None:
        return (
            jsonify(
                {
                    "error": {
                        "code": "OWNER_NOT_BOUND",
                        "message": "Session has no play shell owner; create session with JWT",
                    }
                }
            ),
            403,
        )
    if str(bound_owner) != str(owner_claim):
        return (
            jsonify(
                {
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "Session is bound to another user",
                    }
                }
            ),
            403,
        )

    trace_id = g.get("trace_id") or get_trace_id()
    engine_story_session_id = meta.get("world_engine_story_session_id")
    if not isinstance(engine_story_session_id, str) or not engine_story_session_id.strip():
        return jsonify(
            {
                "session_id": session_id,
                "trace_id": trace_id,
                "world_engine_story_session_id": None,
                "authoritative_state": None,
                "diagnostics": {
                    "diagnostics": [],
                    "warnings": ["story_session_not_initialized_yet"],
                },
                "warnings": ["execute_at_least_one_turn_for_engine_binding"],
            }
        ), 200

    try:
        authoritative_state = get_story_state(engine_story_session_id, trace_id=trace_id)
        diagnostics = get_story_diagnostics(engine_story_session_id, trace_id=trace_id)
    except GameServiceError as exc:
        return jsonify(
            {
                "session_id": session_id,
                "trace_id": trace_id,
                "world_engine_story_session_id": engine_story_session_id,
                "bridge_error": {
                    "failure_class": "world_engine_unreachable",
                    "message": str(exc),
                    "status_code": exc.status_code,
                },
            }
        ), 200

    diag_rows: list = []
    turn_counter = None
    committed_state = None
    if isinstance(diagnostics, dict):
        rows = diagnostics.get("diagnostics")
        if isinstance(rows, list):
            diag_rows = rows[-route_session_config.play_operator_diag_max:]
        turn_counter = diagnostics.get("turn_counter")
        committed_state = diagnostics.get("committed_state")

    return jsonify(
        {
            "session_id": session_id,
            "trace_id": trace_id,
            "world_engine_story_session_id": engine_story_session_id,
            "authoritative_state": authoritative_state if isinstance(authoritative_state, dict) else None,
            "diagnostics": {
                "diagnostics": diag_rows,
                "turn_counter": turn_counter,
                "committed_state": committed_state,
            },
            "warnings": [],
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
    player_input_sha256 = hashlib.sha256(player_input.encode("utf-8")).hexdigest()
    local_interpretation = interpret_player_input(player_input)

    state = runtime_session.current_runtime_state
    metadata = state.metadata if isinstance(state.metadata, dict) else {}
    engine_story_session_id = metadata.get("world_engine_story_session_id")
    trace_id = g.get("trace_id") or get_trace_id()
    langfuse_trace_id = g.get("langfuse_trace_id") or get_langfuse_trace_id()

    created: dict | None = None
    adapter = LangfuseAdapter.get_instance()
    root_span = None

    try:
        # Create root span for this turn execution
        root_span = adapter.start_trace(
            name="backend.turn.execute",
            session_id=session_id,
            turn_id=str(runtime_session.turn_counter) if hasattr(runtime_session, 'turn_counter') else None,
            module_id=state.module_id if state else None,
            metadata={
                "wos_trace_id": trace_id,
                "langfuse_trace_id": langfuse_trace_id,
                "player_input_length": len(player_input),
                "player_input_sha256": player_input_sha256,
                "stage": "turn_execution",
                "route": "/api/v1/sessions/<session_id>/turns",
            },
            trace_id=langfuse_trace_id,
        )

        if not engine_story_session_id:
            compiled = compile_module(state.module_id)
            created = create_story_session(
                module_id=state.module_id,
                runtime_projection=compiled.runtime_projection.model_dump(mode="json"),
                trace_id=trace_id,
                langfuse_trace_id=langfuse_trace_id,
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
            langfuse_trace_id=langfuse_trace_id,
        )
        diagnostics = get_story_diagnostics(engine_story_session_id, trace_id=trace_id)
        current_state = get_story_state(engine_story_session_id, trace_id=trace_id)

        # Update root span with results
        if root_span:
            root_span.update(
                output={
                    "turn_number": runtime_session.turn_counter if hasattr(runtime_session, 'turn_counter') else None,
                    "status": "completed",
                    "player_input_length": len(player_input),
                    "player_input_sha256": player_input_sha256,
                },
            )
    except GameServiceError as exc:
        # Update root span with error
        if root_span:
            root_span.update(output={
                "status": "error",
                "failure_class": "world_engine_unreachable",
                "status_code": exc.status_code,
                "player_input_length": len(player_input),
                "player_input_sha256": player_input_sha256,
            })

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
                "langfuse_trace_id": langfuse_trace_id,
                "failure_class": "world_engine_unreachable",
                "message": str(exc),
                "status_hint": exc.status_code,
            }
        ), 502
    finally:
        # End root span and flush
        if root_span:
            adapter.end_trace(root_span)
        adapter.flush()

    log_world_engine_bridge(
        trace_id,
        operation="execute_story_turn",
        backend_session_id=session_id,
        world_engine_story_session_id=engine_story_session_id,
        outcome="ok",
    )

    # PHASE 2 VALIDATION: Verify turn response contains canonical contract fields
    inner_turn = turn.get("turn") if isinstance(turn, dict) else None
    if not inner_turn:
        raise GameServiceError("World-engine response missing 'turn' wrapper")
    _validate_world_engine_turn_contract(inner_turn, trace_id)

    response_body: dict = {
        "session_id": session_id,
        "trace_id": trace_id,
        "langfuse_trace_id": langfuse_trace_id,
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
    if isinstance(created, dict):
        opening = created.get("opening_turn")
        if isinstance(opening, dict):
            response_body["opening_turn"] = opening
            response_body["world_engine_opening_meta"] = {
                "current_scene_id": created.get("current_scene_id"),
                "turn_counter": created.get("turn_counter"),
                "module_id": created.get("module_id"),
            }
    return jsonify(response_body), 200


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
