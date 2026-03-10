"""Web (session) auth helpers. Centralized login requirement for server-rendered routes."""
from functools import wraps
from urllib.parse import urlparse

from flask import redirect, session, url_for


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


def require_web_login(f):
    """Redirect to login if no session user. Use for protected web routes."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("web.login"))
        return f(*args, **kwargs)
    return wrapped
