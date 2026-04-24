"""Player/public frontend routes."""
from __future__ import annotations

from typing import Any

import requests
from flask import (
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from . import player_backend
from .player_backend import BackendApiError
from .auth import require_login
from .frontend_blueprint import frontend_bp

from . import routes_play  # noqa: F401, E402 — registers /play* on frontend_bp


@frontend_bp.route("/health")
def health():
    return jsonify({"status": "ok", "service": "frontend"}), 200


def _clear_auth_state() -> None:
    session.pop("access_token", None)
    session.pop("refresh_token", None)
    session.pop("current_user", None)
    session.modified = True


def _current_user() -> dict[str, Any] | None:
    return session.get("current_user")


def _user_is_admin(user: dict[str, Any] | None) -> bool:
    if not user:
        return False
    return user.get("role") == "admin"


def _fetch_me() -> dict[str, Any]:
    response = player_backend.request_backend("GET", "/api/v1/auth/me")
    payload = player_backend.require_success(response, "Could not fetch user profile.")
    session["current_user"] = payload
    session.modified = True
    return payload


@frontend_bp.route("/")
def home():
    return render_template("home.html")


@frontend_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("access_token"):
            return redirect(url_for("frontend.dashboard"))
        return render_template("login.html")

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if not username or not password:
        flash("Username and password are required.", "error")
        return render_template("login.html"), 400

    response = player_backend.request_backend(
        "POST",
        "/api/v1/auth/login",
        json_data={"username": username, "password": password},
        allow_refresh=False,
    )
    try:
        payload = player_backend.require_success(response, "Login failed.")
    except BackendApiError as exc:
        flash(str(exc), "error")
        return render_template("login.html"), exc.status_code

    session["access_token"] = payload["access_token"]
    session["refresh_token"] = payload["refresh_token"]
    session["current_user"] = payload.get("user")
    session.modified = True
    flash("Logged in successfully.", "success")
    return redirect(url_for("frontend.dashboard"))


@frontend_bp.route("/logout", methods=["POST"])
def logout():
    if session.get("access_token"):
        player_backend.request_backend("POST", "/api/v1/auth/logout")
    _clear_auth_state()
    flash("You have been logged out.", "info")
    return redirect(url_for("frontend.home"))


@frontend_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""

    if not username or not password:
        flash("Username and password are required.", "error")
        return render_template("register.html"), 400
    if password != password_confirm:
        flash("Passwords do not match.", "error")
        return render_template("register.html"), 400

    response = player_backend.request_backend(
        "POST",
        "/api/v1/auth/register",
        json_data={"username": username, "email": email, "password": password},
        allow_refresh=False,
    )
    try:
        player_backend.require_success(response, "Registration failed.")
    except BackendApiError as exc:
        flash(str(exc), "error")
        return render_template("register.html"), exc.status_code

    flash("Registration complete. You can now log in.", "success")
    return redirect(url_for("frontend.register_pending"))


@frontend_bp.route("/register/pending")
def register_pending():
    return render_template("register_pending.html")


@frontend_bp.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    if request.method == "GET":
        return render_template("resend_verification.html")
    email = (request.form.get("email") or "").strip().lower()
    response = player_backend.request_backend(
        "POST",
        "/api/v1/auth/resend-verification",
        json_data={"email": email},
        allow_refresh=False,
    )
    try:
        payload = player_backend.require_success(response, "Could not resend verification email.")
        flash(payload.get("message", "Verification mail request accepted."), "info")
    except BackendApiError as exc:
        flash(str(exc), "error")
        return render_template("resend_verification.html"), exc.status_code
    return redirect(url_for("frontend.login"))


@frontend_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html")
    email = (request.form.get("email") or "").strip().lower()
    response = player_backend.request_backend(
        "POST",
        "/api/v1/auth/forgot-password",
        json_data={"email": email},
        allow_refresh=False,
    )
    try:
        payload = player_backend.require_success(response, "Could not request a reset link.")
        flash(payload.get("message", "If the email exists, a reset link has been sent."), "info")
    except BackendApiError as exc:
        flash(str(exc), "error")
        return render_template("forgot_password.html"), exc.status_code
    return redirect(url_for("frontend.login"))


@frontend_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    if request.method == "GET":
        return render_template("reset_password.html", token=token)
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""
    if password != password_confirm:
        flash("Passwords do not match.", "error")
        return render_template("reset_password.html", token=token), 400
    response = player_backend.request_backend(
        "POST",
        "/api/v1/auth/reset-password",
        json_data={"token": token, "new_password": password},
        allow_refresh=False,
    )
    try:
        payload = player_backend.require_success(response, "Password reset failed.")
        flash(payload.get("message", "Password reset successful."), "success")
    except BackendApiError as exc:
        flash(str(exc), "error")
        return render_template("reset_password.html", token=token), exc.status_code
    return redirect(url_for("frontend.login"))


@frontend_bp.route("/dashboard")
@require_login
def dashboard():
    try:
        user = _fetch_me()
    except BackendApiError as exc:
        if exc.status_code == 401:
            _clear_auth_state()
            return redirect(url_for("frontend.login"))
        flash(str(exc), "error")
        user = _current_user()
    return render_template(
        "dashboard.html",
        current_user=user,
        is_admin=_user_is_admin(user),
    )


@frontend_bp.route("/news")
def news():
    response = player_backend.request_backend("GET", "/api/v1/news", params={"page": 1, "limit": 20}, allow_refresh=False)
    items: list[dict[str, Any]] = []
    if response.ok:
        payload = response.json()
        items = payload.get("items", []) if isinstance(payload, dict) else []
    return render_template("news.html", items=items)


@frontend_bp.route("/wiki")
@frontend_bp.route("/wiki/<path:slug>")
def wiki(slug: str | None = None):
    api_path = f"/api/v1/wiki/{slug}" if slug else "/api/v1/wiki/index"
    response = player_backend.request_backend("GET", api_path, allow_refresh=False)
    page = response.json() if response.ok else None
    return render_template("wiki.html", page=page, slug=slug), response.status_code if response.status_code in (200, 404) else 200


@frontend_bp.route("/community")
def community():
    response = player_backend.request_backend("GET", "/api/v1/forum/categories", allow_refresh=False)
    categories = []
    if response.ok:
        payload = response.json()
        categories = payload.get("items", []) if isinstance(payload, dict) else []
    return render_template("community.html", categories=categories)


@frontend_bp.route("/game-menu")
@require_login
def game_menu():
    user = _current_user()
    return render_template(
        "game_menu.html",
        current_user=user,
        api_base="/api/v1/game",
        play_service_public_url=current_app.config["PLAY_SERVICE_PUBLIC_URL"],
    )


@frontend_bp.route("/api/v1/<path:subpath>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def api_proxy(subpath: str):
    """Compatibility proxy so frontend static assets can call /api/v1/* on same origin."""
    path = f"/api/v1/{subpath}"
    payload = request.get_json(silent=True)
    response = player_backend.request_backend(
        request.method,
        path,
        json_data=payload if request.method in ("POST", "PUT", "PATCH", "DELETE") else None,
        params=request.args.to_dict(flat=True),
    )
    raw_status = getattr(response, "status_code", None)
    if isinstance(raw_status, int):
        status_code = raw_status
    else:
        status_code = 200 if bool(getattr(response, "ok", False)) else 502

    headers = getattr(response, "headers", None)
    content_type = "application/json"
    if hasattr(headers, "get"):
        content_type = headers.get("Content-Type", "application/json")

    raw_content = getattr(response, "content", None)
    if isinstance(raw_content, (bytes, bytearray)):
        return Response(bytes(raw_content), status=status_code, content_type=content_type)
    if isinstance(raw_content, str):
        return Response(raw_content, status=status_code, content_type=content_type)

    if hasattr(response, "json"):
        try:
            return jsonify(response.json()), status_code
        except Exception:
            pass

    return jsonify({}), status_code


@frontend_bp.errorhandler(BackendApiError)
def handle_backend_error(exc: BackendApiError):
    if request.path.startswith("/api/"):
        return jsonify({"error": str(exc), **exc.payload}), exc.status_code
    flash(str(exc), "error")
    return redirect(url_for("frontend.home"))


@frontend_bp.errorhandler(requests.RequestException)
def handle_request_exception(_exc: requests.RequestException):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Backend API unavailable."}), 503
    flash("Backend API unavailable.", "error")
    return redirect(url_for("frontend.home"))
