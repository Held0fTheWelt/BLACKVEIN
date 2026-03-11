"""Permission helpers for API routes. Use after @jwt_required(). Centralized role and ban checks."""

from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models import User

# Role names for validation and checks. Single source for allowed roles.
ALLOWED_ROLES = ("user", "moderator", "admin")


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


def require_jwt_moderator_or_admin(f):
    """Decorator: require valid JWT and moderator or admin role (non-banned). Returns 403 otherwise."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user_can_write_news():
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return jwt_required()(wrapped)
