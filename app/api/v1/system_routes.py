from flask import jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.v1 import api_v1_bp
from app.extensions import limiter
from app.models import User


@api_v1_bp.route("/health")
@limiter.limit("100 per minute")
def health():
    """API health check."""
    return jsonify({"status": "ok"}), 200


@api_v1_bp.route("/test/protected", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def protected_test():
    """Example protected route; returns message and user id."""
    from app.extensions import db
    uid = get_jwt_identity()
    user = db.session.get(User, int(uid))
    return jsonify({
        "message": "ok",
        "user_id": int(uid),
        "username": user.username if user else None,
    }), 200
