"""Player/public frontend routes."""
from __future__ import annotations

from typing import Any

import requests
from flask import (
    Blueprint,
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

from .api_client import BackendApiError, request_backend, require_success
from .auth import require_login

frontend_bp = Blueprint("frontend", __name__)


def _clear_auth_state() -> None:
    session.pop("access_token", None)
    session.pop("refresh_token", None)
    session.pop("current_user", None)
    session.modified = True


def _current_user() -> dict[str, Any] | None:
    return session.get("current_user")


def _fetch_me() -> dict[str, Any]:
    response = request_backend("GET", "/api/v1/auth/me")
    payload = require_success(response, "Could not fetch user profile.")
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

    response = request_backend(
        "POST",
        "/api/v1/auth/login",
        json_data={"username": username, "password": password},
        allow_refresh=False,
    )
    try:
        payload = require_success(response, "Login failed.")
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
        request_backend("POST", "/api/v1/auth/logout")
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

    response = request_backend(
        "POST",
        "/api/v1/auth/register",
        json_data={"username": username, "email": email, "password": password},
        allow_refresh=False,
    )
    try:
        require_success(response, "Registration failed.")
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
    response = request_backend(
        "POST",
        "/api/v1/auth/resend-verification",
        json_data={"email": email},
        allow_refresh=False,
    )
    try:
        payload = require_success(response, "Could not resend verification email.")
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
    response = request_backend(
        "POST",
        "/api/v1/auth/forgot-password",
        json_data={"email": email},
        allow_refresh=False,
    )
    try:
        payload = require_success(response, "Could not request a reset link.")
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
    response = request_backend(
        "POST",
        "/api/v1/auth/reset-password",
        json_data={"token": token, "new_password": password},
        allow_refresh=False,
    )
    try:
        payload = require_success(response, "Password reset failed.")
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
    return render_template("dashboard.html", current_user=user)


@frontend_bp.route("/news")
def news():
    response = request_backend("GET", "/api/v1/news", params={"page": 1, "limit": 20}, allow_refresh=False)
    items: list[dict[str, Any]] = []
    if response.ok:
        payload = response.json()
        items = payload.get("items", []) if isinstance(payload, dict) else []
    return render_template("news.html", items=items)


@frontend_bp.route("/wiki")
@frontend_bp.route("/wiki/<path:slug>")
def wiki(slug: str | None = None):
    api_path = f"/api/v1/wiki/{slug}" if slug else "/api/v1/wiki/index"
    response = request_backend("GET", api_path, allow_refresh=False)
    page = response.json() if response.ok else None
    return render_template("wiki.html", page=page, slug=slug), response.status_code if response.status_code in (200, 404) else 200


@frontend_bp.route("/community")
def community():
    response = request_backend("GET", "/api/v1/forum/categories", allow_refresh=False)
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


@frontend_bp.route("/play")
@require_login
def play_start():
    response = request_backend("GET", "/api/v1/game/bootstrap")
    bootstrap = response.json() if response.ok else {}
    return render_template("session_start.html", bootstrap=bootstrap)


@frontend_bp.route("/play/start", methods=["POST"])
@require_login
def play_create():
    template_id = (request.form.get("template_id") or "").strip()
    if not template_id:
        flash("Please select a template.", "error")
        return redirect(url_for("frontend.play_start"))
    response = request_backend("POST", "/api/v1/game/runs", json_data={"template_id": template_id})
    try:
        payload = require_success(response, "Could not create play run.")
    except BackendApiError as exc:
        flash(str(exc), "error")
        return redirect(url_for("frontend.play_start"))
    run_id = payload.get("run", {}).get("id")
    if not run_id:
        flash("Run creation returned no run id.", "error")
        return redirect(url_for("frontend.play_start"))
    return redirect(url_for("frontend.play_shell", session_id=run_id))


@frontend_bp.route("/play/<session_id>")
@require_login
def play_shell(session_id: str):
    user = _current_user() or {}
    response = request_backend(
        "POST",
        "/api/v1/game/tickets",
        json_data={"run_id": session_id, "display_name": user.get("username", "Player")},
    )
    ticket_payload = response.json() if response.ok else {}
    if not response.ok:
        flash(ticket_payload.get("error", "Could not create play ticket."), "error")
    return render_template("session_shell.html", session_id=session_id, ticket=ticket_payload)


@frontend_bp.route("/play/<session_id>/execute", methods=["POST"])
@require_login
def play_execute(session_id: str):
    operator_input = (request.form.get("operator_input") or "").strip()
    if not operator_input:
        flash("Please enter an action.", "error")
        return redirect(url_for("frontend.play_shell", session_id=session_id))
    history = session.get("play_shell_history", {})
    entries = history.get(session_id, [])
    entries.append(operator_input)
    history[session_id] = entries[-50:]
    session["play_shell_history"] = history
    session.modified = True
    flash("Action queued on frontend shell. Use live websocket controls for runtime execution.", "info")
    return redirect(url_for("frontend.play_shell", session_id=session_id))


@frontend_bp.route("/api/v1/<path:subpath>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def api_proxy(subpath: str):
    """Compatibility proxy so frontend static assets can call /api/v1/* on same origin."""
    path = f"/api/v1/{subpath}"
    payload = request.get_json(silent=True)
    response = request_backend(
        request.method,
        path,
        json_data=payload if request.method in ("POST", "PUT", "PATCH", "DELETE") else None,
        params=request.args.to_dict(flat=True),
    )
    content_type = response.headers.get("Content-Type", "application/json")
    return Response(response.content, status=response.status_code, content_type=content_type)


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
