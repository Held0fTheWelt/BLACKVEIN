"""Internal bootstrap admin user route."""

from __future__ import annotations

from .common import *

@api_v1_bp.route("/internal/bootstrap/admin-user", methods=["POST"])
def internal_bootstrap_admin_user():
    """Internal endpoint for docker-up.py to create default admin user if missing."""
    try:
        from app.models.backend.user import User
        from app.models.backend.role import Role
        from app.extensions import db
        from werkzeug.security import generate_password_hash

        body = request.get_json(silent=True) or {}
        username = body.get("username", "admin")
        password = body.get("password", "Admin123")
        create_if_missing = body.get("create_if_missing", True)

        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return ok({"created": False, "message": "User already exists"})

        if not create_if_missing:
            return ok({"created": False, "message": "User does not exist and create_if_missing=False"})

        # Get or create admin role (per ROLE_HIERARCHY.md: roles are user, qa, moderator, admin)
        admin_role = Role.query.filter_by(name="admin").first()
        if not admin_role:
            admin_role = Role(name="admin", description="Administrator")
            db.session.add(admin_role)
            db.session.commit()

        # Create new admin user
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role_id=admin_role.id,
            role_level=100,  # Super admin level
        )
        db.session.add(new_user)
        db.session.commit()

        return ok({"created": True, "username": username, "message": f"Admin user '{username}' created successfully"})

    except Exception as e:
        return fail(
            "admin_user_creation_error",
            f"Failed to create admin user: {str(e)}",
            500,
            {}
        )

__all__ = (
    'internal_bootstrap_admin_user',
)
