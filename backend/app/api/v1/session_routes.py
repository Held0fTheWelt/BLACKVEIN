"""W3.1 — Session management API routes.

Provides the canonical REST API for session lifecycle:
- POST /api/v1/sessions - Create a new session
- GET /api/v1/sessions/<session_id> - Retrieve session state
- POST /api/v1/sessions/<session_id>/turns - Execute a turn
- GET /api/v1/sessions/<session_id>/logs - Retrieve event logs
- GET /api/v1/sessions/<session_id>/state - Get canonical world state

Routes expose W2 runtime capabilities while deferring persistence operations
to W3.2. The create endpoint is fully implemented; others return 501 Not
Implemented pending persistence layer.
"""

from flask import request, jsonify

from app.api.v1 import api_v1_bp
from app.services.session_service import (
    create_session,
    get_session,
    execute_turn,
    get_session_logs,
    get_session_state,
)


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
    data = request.get_json() or {}
    module_id = data.get("module_id")

    if not module_id:
        return jsonify({"error": "module_id is required"}), 400

    try:
        session = create_session(module_id)
        return jsonify(session.model_dump(mode='json')), 201
    except Exception as e:
        # Error handling deferred to W3.2 comprehensive error handler
        return jsonify({"error": str(e)}), 500


@api_v1_bp.route("/sessions/<session_id>", methods=["GET"])
def get_session_by_id(session_id):
    """Retrieve session state by session_id."""
    from app.runtime.session_store import get_session as get_runtime_session

    runtime_session = get_runtime_session(session_id)
    if not runtime_session:
        return jsonify({"error": "Session not found"}), 404

    state = runtime_session.current_runtime_state
    return jsonify({
        "session_id": session_id,
        "module_id": state.module_id if state else None,
        "module_version": state.module_version if state else None,
        "turn_counter": runtime_session.turn_counter,
        "status": state.status.value if state and hasattr(state, 'status') else "active",
        "canonical_state": state.canonical_state if state else {},
        "context_layers": {
            "has_session_history": bool(state and state.context_layers and state.context_layers.session_history),
            "has_short_term": bool(state and state.context_layers and state.context_layers.short_term_context),
            "current_scene": state.canonical_state.get("scene_id") if state and state.canonical_state else None
        }
    }), 200


@api_v1_bp.route("/sessions/<session_id>/turns", methods=["POST"])
def execute_session_turn(session_id):
    """Execute a turn in an active session."""
    import asyncio
    from app.runtime.session_store import get_session as get_runtime_session
    from app.runtime.turn_dispatcher import dispatch_turn
    from app.content.module_loader import load_module

    data = request.get_json() or {}
    operator_input = data.get("operator_input", "")

    runtime_session = get_runtime_session(session_id)
    if not runtime_session:
        return jsonify({"error": "Session not found"}), 404

    state = runtime_session.current_runtime_state
    if not state:
        return jsonify({"error": "Session has no runtime state"}), 400

    # Load the content module
    try:
        module = load_module(state.module_id)
    except Exception as e:
        return jsonify({"error": f"Could not load module: {str(e)}"}), 404

    # Execute turn (async call wrapped in sync context)
    try:
        result = asyncio.run(dispatch_turn(
            state,
            runtime_session.turn_counter + 1,
            module,
            operator_input=operator_input
        ))
    except Exception as e:
        return jsonify({"error": f"Turn execution failed: {str(e)}"}), 500

    return jsonify({
        "turn_number": runtime_session.turn_counter,
        "result_status": result.get("status", "success") if isinstance(result, dict) else "success",
        "guard_outcome": result.get("guard_outcome", "unknown") if isinstance(result, dict) else "unknown",
        "updated_state": {
            "scene_id": state.canonical_state.get("scene_id") if state.canonical_state else None,
            "turn_counter": runtime_session.turn_counter
        }
    }), 200


@api_v1_bp.route("/sessions/<session_id>/logs", methods=["GET"])
def get_session_event_logs(session_id):
    """Retrieve event logs for a session."""
    from app.runtime.session_store import get_session as get_runtime_session

    runtime_session = get_runtime_session(session_id)
    if not runtime_session:
        return jsonify({"error": "Session not found"}), 404

    state = runtime_session.current_runtime_state
    if not state or not state.context_layers:
        return jsonify({"events": [], "total_turns": 0}), 200

    # Return events from context layers
    events = []
    if state.context_layers.short_term_context:
        events.append({
            "type": "turn_executed",
            "turn": state.context_layers.short_term_context.turn_number if hasattr(state.context_layers.short_term_context, 'turn_number') else 0,
            "outcome": state.context_layers.short_term_context.guard_outcome if hasattr(state.context_layers.short_term_context, 'guard_outcome') else "unknown"
        })

    return jsonify({"events": events, "total_turns": runtime_session.turn_counter}), 200


@api_v1_bp.route("/sessions/<session_id>/state", methods=["GET"])
def get_session_canonical_state(session_id):
    """Get canonical world state for a session."""
    from app.runtime.session_store import get_session as get_runtime_session

    runtime_session = get_runtime_session(session_id)
    if not runtime_session:
        return jsonify({"error": "Session not found"}), 404

    state = runtime_session.current_runtime_state
    if not state or not state.canonical_state:
        return jsonify({}), 200

    return jsonify(state.canonical_state), 200
