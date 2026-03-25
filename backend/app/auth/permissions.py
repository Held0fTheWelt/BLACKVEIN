"""Permission helpers for API routes. Use after @jwt_required(). Centralized role, role_level, and ban checks."""

import hmac
import os
from functools import wraps

from flask import current_app, g, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_jwt_extended import create_access_token as _create_access_token_orig

from app.models import User
from app.models.user import SUPERADMIN_THRESHOLD

# Role names for validation and checks. Single source for allowed roles.
ALLOWED_ROLES = ("user", "moderator", "admin", "qa")


def create_access_token(identity, **kwargs):
    """Wrapper for Flask-JWT-Extended's create_access_token that ensures identity is a string.

    PyJWT requires the 'sub' claim to be a string, so we convert identity to str() if needed.
    """
    # Ensure identity is a string (PyJWT requirement)
    if identity is not None and not isinstance(identity, str):
        identity = str(identity)
    return _create_access_token_orig(identity=identity, **kwargs)


def get_current_user():
    """Return the User for the current JWT identity, or None. Call only after @jwt_required()."""
    try:
        raw = get_jwt_identity()
        if raw is None:
            return None
        return User.query.get(int(raw))
    except (TypeError, ValueError):
        return None


def current_user_has_role(role_name: str) -> bool:
    """True if the current JWT user has the given role. Banned users are not granted role privileges."""
    user = get_current_user()
    if user is None or user.is_banned:
        return False
    return user.has_role(role_name)


def current_user_has_any_role(role_names) -> bool:
    """True if the current JWT user has any of the given roles. Banned users return False."""
    user = get_current_user()
    if user is None or user.is_banned:
        return False
    return user.has_any_role(role_names)


def current_user_is_admin() -> bool:
    """True if the current JWT identity belongs to a non-banned user with admin role."""
    user = get_current_user()
    return user is not None and not user.is_banned and user.is_admin


def current_user_role_level() -> int:
    """Return the current JWT user's role_level, or 0 if none or banned."""
    user = get_current_user()
    if user is None or user.is_banned:
        return 0
    return getattr(user, "role_level", 0) or 0


def current_user_is_super_admin() -> bool:
    """True if the current JWT user is admin with role_level >= SUPERADMIN_THRESHOLD."""
    user = get_current_user()
    return user is not None and not user.is_banned and getattr(user, "is_super_admin", False)


def admin_may_edit_target(actor_level: int, target_level: int) -> bool:
    """True if an admin with actor_level may edit a user with target_level (strictly lower only)."""
    return actor_level > target_level


def admin_may_assign_role_level(actor_level: int, target_user_id: int, new_level: int, actor_id: int) -> bool:
    """
    True if the admin may set target's role_level to new_level.
    - Editing another user: new_level < actor_level.
    - Editing self: only SuperAdmin may set own role_level, and only to >= SUPERADMIN_THRESHOLD.
    """
    if target_user_id == actor_id:
        return new_level >= SUPERADMIN_THRESHOLD  # Caller must also check current_user_is_super_admin()
    return new_level < actor_level


def current_user_is_moderator() -> bool:
    """True if the current JWT user has moderator role (and is not banned)."""
    return current_user_has_role(User.ROLE_MODERATOR)


def current_user_is_moderator_or_admin() -> bool:
    """True if the current JWT user has moderator or admin role (and is not banned)."""
    return current_user_has_any_role((User.ROLE_MODERATOR, User.ROLE_ADMIN))


def current_user_can_write_news() -> bool:
    """
    True if the current JWT identity belongs to a non-banned user with moderator or admin role.
    Call only from routes that already applied @jwt_required().
    """
    user = get_current_user()
    if user is None or user.is_banned:
        return False
    return user.can_write_news()


def current_user_is_banned() -> bool:
    """True if the current JWT identity belongs to a banned user. Useful for login/response checks."""
    user = get_current_user()
    return user is not None and user.is_banned


def require_jwt_admin(f):
    """Decorator: require valid JWT and admin role (non-banned). Returns 403 if not admin."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user_is_admin():
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return jwt_required()(wrapped)


def require_feature(feature_id: str):
    """Decorator: require valid JWT and area-based access to the feature. Use after @jwt_required() or with require_jwt_* that already applied jwt."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            from app.auth.feature_registry import user_can_access_feature
            user = get_current_user()
            if not user_can_access_feature(user, feature_id):
                return jsonify({"error": "Forbidden. You do not have access to this feature."}), 403
            return f(*args, **kwargs)
        return wrapped
    return decorator


def require_jwt_moderator_or_admin(f):
    """Decorator: require valid JWT and moderator or admin role (non-banned). Returns 403 otherwise."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user_can_write_news():
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return jwt_required()(wrapped)


def _is_n8n_service_request() -> bool:
    """True if request has valid X-Service-Key matching N8N_SERVICE_TOKEN."""
    token = current_app.config.get("N8N_SERVICE_TOKEN") or os.getenv("N8N_SERVICE_TOKEN")
    if not token or not token.strip():
        return False
    key = (request.headers.get("X-Service-Key") or "").strip()
    return hmac.compare_digest(key, token) if key else False


def require_editor_or_n8n_service(f):
    """
    Decorator: allow either (1) valid JWT + moderator/admin, or (2) valid X-Service-Key (n8n).
    When X-Service-Key is used, set g.is_n8n_service = True so the view can restrict to machine_draft only.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        if _is_n8n_service_request():
            g.is_n8n_service = True
            return f(*args, **kwargs)
        g.is_n8n_service = False
        if get_jwt_identity() is None:
            return jsonify({"error": "Authorization required"}), 401
        if not current_user_can_write_news():
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return jwt_required(optional=True)(wrapped)