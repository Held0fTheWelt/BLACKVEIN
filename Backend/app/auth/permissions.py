"""Permission helpers for API routes. Use after @jwt_required()."""

from flask_jwt_extended import get_jwt_identity

from app.models import User


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
