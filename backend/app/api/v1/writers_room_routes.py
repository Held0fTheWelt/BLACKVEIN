from __future__ import annotations

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.v1 import api_v1_bp
from app.services.writers_room_service import run_writers_room_review


@api_v1_bp.route("/writers-room/reviews", methods=["POST"])
@jwt_required()
def create_writers_room_review():
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400
    module_id = (data.get("module_id") or "").strip()
    focus = (data.get("focus") or "canon consistency and dramaturgy").strip()
    if not module_id:
        return jsonify({"error": "module_id is required"}), 400

    actor_id = str(get_jwt_identity() or "unknown")
    report = run_writers_room_review(module_id=module_id, focus=focus, actor_id=actor_id)
    return jsonify(report), 200
