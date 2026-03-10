from flask import jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from app.api.v1 import api_v1_bp
from app.extensions import limiter
from app.services import verify_user, create_user


@api_v1_bp.route("/auth/register", methods=["POST"])
@limiter.limit("10 per minute")
def register():
    """Register a new user; return 201 with id and username or error."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    username = (data.get("username") or "").strip()
    password = data.get("password")
    user, err = create_user(username, password)
    if err:
        status = 409 if err == "Username already taken" else 400
        return jsonify({"error": err}), status
    return jsonify({"id": user.id, "username": user.username}), 201


@api_v1_bp.route("/auth/login", methods=["POST"])
@limiter.limit("20 per minute")
def login():
    """Authenticate and return JWT access_token and user info."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    username = (data.get("username") or "").strip()
    password = data.get("password")
    if not username or password is None:
        return jsonify({"error": "Username and password are required"}), 400
    user = verify_user(username, password)
    if user:
        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            "access_token": access_token,
            "user": user.to_dict(),
        }), 200
    return jsonify({"error": "Invalid username or password"}), 401


@api_v1_bp.route("/auth/me", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def me():
    """Return current user from JWT."""
    from app.models import User
    from app.extensions import db
    uid = get_jwt_identity()
    user = db.session.get(User, int(uid))
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict()), 200
