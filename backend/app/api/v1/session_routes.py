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
    """Retrieve session state by session_id.

    W3.2 Deferral: Requires persistence layer.

    Response (501 Not Implemented):
        {
            "error": "get_session requires W3.2 session persistence layer"
        }
    """
    return jsonify(
        {"error": "get_session requires W3.2 session persistence layer"}
    ), 501


@api_v1_bp.route("/sessions/<session_id>/turns", methods=["POST"])
def execute_session_turn(session_id):
    """Execute a turn in an active session.

    W3.2 Deferral: Requires persistence layer and turn dispatcher.

    Request body:
        {
            "decision": {...}
        }

    Response (501 Not Implemented):
        {
            "error": "execute_turn requires W3.2 turn execution and persistence"
        }
    """
    return jsonify(
        {"error": "execute_turn requires W3.2 turn execution and persistence"}
    ), 501


@api_v1_bp.route("/sessions/<session_id>/logs", methods=["GET"])
def get_session_event_logs(session_id):
    """Retrieve event logs for a session.

    W3.2 Deferral: Requires persistence layer.

    Query parameters:
        - limit: Maximum number of entries (default 100)
        - offset: Starting position (default 0)

    Response (501 Not Implemented):
        {
            "error": "get_session_logs requires W3.2 event log persistence"
        }
    """
    return jsonify(
        {"error": "get_session_logs requires W3.2 event log persistence"}
    ), 501


@api_v1_bp.route("/sessions/<session_id>/state", methods=["GET"])
def get_session_canonical_state(session_id):
    """Get canonical world state for a session.

    W3.2 Deferral: Requires persistence layer.

    Response (501 Not Implemented):
        {
            "error": "get_session_state requires W3.2 state persistence"
        }
    """
    return jsonify(
        {"error": "get_session_state requires W3.2 state persistence"}
    ), 501
