"""Permission helpers for API routes. Use after @jwt_required()."""

from flask_jwt_extended import get_jwt_identity

from app.models import User


def get_current_user():
    """Return the User for the current JWT identity, or None. Call only after @jwt_required()."""
    try:
        raw = get_jwt_identity()
        if raw is None:
            return None
        return User.query.get(int(raw))
    except (TypeError, ValueError):
        return None


def current_user_is_admin() -> bool:
    """True if the current JWT identity belongs to a user with admin role."""
    user = get_current_user()
    return user is not None and user.role == User.ROLE_ADMIN


def current_user_can_write_news() -> bool:
    """
    True if the current JWT identity belongs to a user with editor or admin role.
    Call only from routes that already applied @jwt_required().
    """
    try:
        raw = get_jwt_identity()
        if raw is None:
            return False
        user_id = int(raw)
    except (TypeError, ValueError):
        return False
    user = User.query.get(user_id)
    if user is None:
        return False
    return user.can_write_news()
