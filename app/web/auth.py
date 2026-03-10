"""Web (session) auth helpers. Centralized login requirement for server-rendered routes."""
from functools import wraps
from flask import redirect, session, url_for


def require_web_login(f):
    """Redirect to login if no session user. Use for protected web routes."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("web.login"))
        return f(*args, **kwargs)
    return wrapped
