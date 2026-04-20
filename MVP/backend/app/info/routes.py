"""Technical HTML pages for the Flask backend (operators / developers only)."""

from __future__ import annotations

from flask import Blueprint, current_app, render_template, url_for

info_bp = Blueprint(
    "info",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="static",
)


@info_bp.context_processor
def _info_context():
    cfg = current_app.config
    frontend = (cfg.get("FRONTEND_URL") or "").strip().rstrip("/") or None
    admin_tool = (cfg.get("ADMINISTRATION_TOOL_URL") or "").strip().rstrip("/") or None
    play_public = (cfg.get("PLAY_SERVICE_PUBLIC_URL") or "").strip().rstrip("/") or None
    play_internal = (cfg.get("PLAY_SERVICE_INTERNAL_URL") or "").strip().rstrip("/") or None
    return {
        "frontend_url": frontend,
        "admin_tool_url": admin_tool,
        "play_service_public_url": play_public,
        "play_service_internal_url": play_internal,
        "nav_items": [
            (url_for("info.backend_home"), "Home"),
            (url_for("info.api_overview"), "API"),
            (url_for("info.engine_integration"), "Engine"),
            (url_for("info.ai_integration"), "AI"),
            (url_for("info.auth_security"), "Auth"),
            (url_for("info.operations_health"), "Ops"),
        ],
    }


@info_bp.route("/", strict_slashes=False)
def backend_home():
    return render_template("home.html")


@info_bp.route("/api", strict_slashes=False)
def api_overview():
    return render_template("api.html")


@info_bp.route("/engine", strict_slashes=False)
def engine_integration():
    return render_template("engine.html")


@info_bp.route("/ai", strict_slashes=False)
def ai_integration():
    return render_template("ai.html")


@info_bp.route("/auth", strict_slashes=False)
def auth_security():
    return render_template("auth.html")


@info_bp.route("/ops", strict_slashes=False)
def operations_health():
    return render_template("ops.html")
