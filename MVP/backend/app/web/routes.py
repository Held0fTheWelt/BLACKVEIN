"""Legacy web compatibility routes.

This blueprint no longer renders player/public HTML.
It provides infrastructure health, a root redirect to the technical
``/backend`` info surface, and compatibility redirects to the dedicated
frontend service for legacy paths (``/login``, ``/play``, …).
"""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, redirect, request, session, url_for

from app.services import log_activity

web_bp = Blueprint("web", __name__)


def _frontend_base() -> str | None:
    value = (current_app.config.get("FRONTEND_URL") or "").strip()
    return value.rstrip("/") if value else None


def _compat_redirect(path: str, *, fallback_status: int = 410):
    base = _frontend_base()
    if not base:
        return jsonify(
            {
                "error": "Legacy UI route disabled.",
                "message": "Configure FRONTEND_URL for compatibility redirects.",
            }
        ), fallback_status
    return redirect(f"{base}{path}", code=302)


@web_bp.route("/health")
def health():
    return {"status": "ok"}, 200


@web_bp.route("/")
def home():
    """Direct browser entry lands on the technical backend info surface, not the player frontend."""
    return redirect(url_for("info.backend_home"))


@web_bp.route("/login", methods=["GET", "POST"])
def login():
    return _compat_redirect("/login")


@web_bp.route("/blocked")
def blocked():
    return _compat_redirect("/login")


@web_bp.route("/logout", methods=["POST"])
def logout():
    uid = session.get("user_id")
    if uid:
        log_activity(
            actor=None,
            category="auth",
            action="logout",
            status="success",
            message="Legacy web logout compatibility redirect",
            route=request.path,
            method=request.method,
            tags=["web", "compatibility"],
        )
    session.clear()
    return _compat_redirect("/")


@web_bp.route("/register", methods=["GET", "POST"])
def register():
    return _compat_redirect("/register")


@web_bp.route("/register/pending", methods=["GET"])
def register_pending():
    return _compat_redirect("/register/pending")


@web_bp.route("/activate/<token>", methods=["GET"])
def activate(token: str):
    from app.services.user_service import verify_email_with_token

    ok, _err = verify_email_with_token(token)
    suffix = "/login?verified=1" if ok else "/login?verified=0"
    return _compat_redirect(suffix)


@web_bp.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    return _compat_redirect("/resend-verification")


@web_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    return _compat_redirect("/forgot-password")


@web_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    return _compat_redirect(f"/reset-password/{token}")


@web_bp.route("/news")
def news():
    return _compat_redirect("/news")


@web_bp.route("/wiki")
@web_bp.route("/wiki/<path:slug>")
def wiki(slug: str | None = None):
    if slug:
        return _compat_redirect(f"/wiki/{slug}")
    return _compat_redirect("/wiki")


@web_bp.route("/community")
def community():
    return _compat_redirect("/community")


@web_bp.route("/game-menu")
def game_menu():
    return _compat_redirect("/game-menu")


@web_bp.route("/dashboard")
def dashboard():
    return _compat_redirect("/dashboard")


@web_bp.route("/play")
def session_start():
    return _compat_redirect("/play")


@web_bp.route("/play/start", methods=["POST"])
def session_create():
    return _compat_redirect("/play")


@web_bp.route("/play/<session_id>")
def session_view(session_id: str):
    return _compat_redirect(f"/play/{session_id}")


@web_bp.route("/play/<session_id>/execute", methods=["POST"])
def session_execute(session_id: str):
    return _compat_redirect(f"/play/{session_id}")
