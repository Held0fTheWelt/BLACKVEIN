"""Web (session) auth helpers. Centralized login requirement for server-rendered routes."""
from functools import wraps
from urllib.parse import urlparse

from flask import flash, redirect, session, url_for

from app.models import User
from app.extensions import db


def is_safe_redirect(url: str) -> bool:
    """Return True only if the URL is internal: path-only, no scheme, no netloc.
    Prevents open-redirect via e.g. /login?next=https://evil.com."""
    if not url or not url.strip():
        return False
    parsed = urlparse(url)
    if parsed.netloc:
        return False
    if parsed.scheme:
        return False
    return parsed.path.startswith("/")


def _user_needs_verification(user) -> bool:
    """True if user has email but is not yet verified."""
    return bool(user and user.email and user.email_verified_at is None)


def require_web_login(f):
    """Redirect to login if no session user or if user is unverified (has email but no verification)."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        uid = session.get("user_id")
        if not uid:
            return redirect(url_for("web.login"))
        user = db.session.get(User, int(uid))
        if user is None or _user_needs_verification(user):
            session.clear()
            flash("Please verify your email to log in.", "error")
            return redirect(url_for("web.login"))
        return f(*args, **kwargs)
    return wrapped
