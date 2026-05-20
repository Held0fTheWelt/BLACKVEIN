from __future__ import annotations

from flask import g, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.v1 import api_v1_bp
from app.observability.audit_log import log_workflow_audit
from app.observability.trace import get_trace_id
from app.services.writers_room.writers_room_service import (
    apply_writers_room_decision,
    get_writers_room_review,
    run_writers_room_review,
    submit_writers_room_revision,
)
from app.config.route_constants import route_status_codes, route_pagination_config


@api_v1_bp.route("/writers-room/reviews", methods=["POST"])
@jwt_required()
def create_writers_room_review():
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), route_status_codes.bad_request
    module_id = (data.get("module_id") or "").strip()
    focus = (data.get("focus") or "canon consistency and dramaturgy").strip()
    if not module_id:
        return jsonify({"error": "module_id is required"}), route_status_codes.bad_request

    actor_id = str(get_jwt_identity() or "unknown")
    trace_id = g.get("trace_id") or get_trace_id()
    report = run_writers_room_review(
        module_id=module_id, focus=focus, actor_id=actor_id, trace_id=trace_id
    )
    log_workflow_audit(
        trace_id,
        workflow="writers_room_review",
        actor_id=actor_id,
        outcome="ok",
        resource_id=module_id,
    )
    return jsonify(report), route_status_codes.ok


@api_v1_bp.route("/writers-room/reviews/<review_id>", methods=["GET"])
@jwt_required()
def get_writers_room_review_by_id(review_id: str):
    try:
        review = get_writers_room_review(review_id=review_id)
    except FileNotFoundError:
        return jsonify({"error": "review_not_found"}), route_status_codes.not_found
    return jsonify(review), route_status_codes.ok


@api_v1_bp.route("/writers-room/reviews/<review_id>/revision-submit", methods=["POST"])
@jwt_required()
def submit_writers_room_review_revision(review_id: str):
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        data = {}
    actor_id = str(get_jwt_identity() or "unknown")
    trace_id = g.get("trace_id") or get_trace_id()
    focus_raw = data.get("focus")
    focus = str(focus_raw).strip() if focus_raw is not None else None
    try:
        review = submit_writers_room_revision(
            review_id=review_id,
            actor_id=actor_id,
            focus=focus,
            note=str(data.get("note") or "").strip(),
            trace_id=trace_id,
        )
    except FileNotFoundError:
        return jsonify({"error": "review_not_found"}), route_status_codes.not_found
    except ValueError as exc:
        return jsonify({"error": str(exc)}), route_status_codes.bad_request
    log_workflow_audit(
        trace_id,
        workflow="writers_room_revision_submit",
        actor_id=actor_id,
        outcome="ok",
        resource_id=review_id,
    )
    return jsonify(review), route_status_codes.ok


@api_v1_bp.route("/writers-room/reviews/<review_id>/decision", methods=["POST"])
@jwt_required()
def set_writers_room_review_decision(review_id: str):
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), route_status_codes.bad_request
    decision = str(data.get("decision") or "").strip()
    if not decision:
        return jsonify({"error": "decision is required"}), route_status_codes.bad_request
    actor_id = str(get_jwt_identity() or "unknown")
    trace_id = g.get("trace_id") or get_trace_id()
    try:
        review = apply_writers_room_decision(
            review_id=review_id,
            actor_id=actor_id,
            decision=decision,
            note=str(data.get("note") or "").strip(),
        )
    except FileNotFoundError:
        return jsonify({"error": "review_not_found"}), route_status_codes.not_found
    except ValueError as exc:
        return jsonify({"error": str(exc)}), route_status_codes.bad_request
    log_workflow_audit(
        trace_id,
        workflow="writers_room_review_decision",
        actor_id=actor_id,
        outcome="ok",
        resource_id=review_id,
    )
    return jsonify(review), route_status_codes.ok
