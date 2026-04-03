"""Authentication helpers for frontend routes."""
from __future__ import annotations

from functools import wraps

from flask import flash, redirect, session, url_for


def is_logged_in() -> bool:
    return bool(session.get("access_token"))


def require_login(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not is_logged_in():
            flash("Please log in first.", "error")
            return redirect(url_for("frontend.login"))
        return view_func(*args, **kwargs)

    return wrapped
