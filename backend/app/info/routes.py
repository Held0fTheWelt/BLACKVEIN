"""Technical HTML pages for the Flask backend (operators / developers only)."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, abort, current_app, render_template, send_file, url_for

info_bp = Blueprint(
    "info",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="static",
)

_REL_OPENAPI = Path("docs") / "api" / "openapi.yaml"


def _resolve_openapi_yaml_path() -> Path | None:
    """Locate openapi.yaml for monorepo checkout and Docker /app layout (see backend/Dockerfile)."""
    cfg = (current_app.config.get("OPENAPI_SPEC_PATH") or "").strip()
    if cfg:
        p = Path(cfg)
        if p.is_file():
            return p
    here = Path(__file__).resolve()
    # .../repo/backend/app/info/routes.py -> parents[3] == repo root
    # .../app/app/info/routes.py (Docker) -> parents[2] == /app with docs/ copied under /app/docs
    for depth in (3, 2):
        if depth < len(here.parents):
            candidate = here.parents[depth] / _REL_OPENAPI
            if candidate.is_file():
                return candidate
    return None


@info_bp.context_processor
def _info_context():
    cfg = current_app.config
    frontend = (cfg.get("FRONTEND_URL") or "").strip().rstrip("/") or None
    admin_tool = (cfg.get("ADMINISTRATION_TOOL_URL") or "").strip().rstrip("/") or None
    play_public = (cfg.get("PLAY_SERVICE_PUBLIC_URL") or "").strip().rstrip("/") or None
    play_internal = (cfg.get("PLAY_SERVICE_INTERNAL_URL") or "").strip().rstrip("/") or None
    docs = (cfg.get("DOCS_SITE_URL") or "").strip().rstrip("/") or None
    return {
        "frontend_url": frontend,
        "admin_tool_url": admin_tool,
        "play_service_public_url": play_public,
        "play_service_internal_url": play_internal,
        "docs_site_url": docs,
        "nav_items": [
            (url_for("info.backend_home"), "Home"),
            (url_for("info.api_overview"), "API"),
            (url_for("info.api_explorer"), "API Explorer"),
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


@info_bp.route("/openapi.yaml", strict_slashes=False)
def openapi_spec():
    """Serve the repo OpenAPI document (same inventory as drift-checked spec)."""
    path = _resolve_openapi_yaml_path()
    if path is None:
        abort(404)
    return send_file(path, mimetype="application/yaml")


@info_bp.route("/api-explorer", strict_slashes=False)
def api_explorer():
    return render_template("api_explorer.html")


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
