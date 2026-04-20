"""Frontend Flask application factory."""
from __future__ import annotations

from flask import Flask, jsonify, request

from .config import Config
from .routes import frontend_bp


def _wants_json() -> bool:
    return request.path.startswith("/api/")


def create_app(config_object=None) -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(config_object or Config)

    if not app.config.get("SECRET_KEY"):
        raise ValueError("FRONTEND_SECRET_KEY (or SECRET_KEY) must be configured for frontend service.")

    app.register_blueprint(frontend_bp)

    @app.errorhandler(404)
    def not_found(_exc):
        if _wants_json():
            return jsonify({"error": "Not found"}), 404
        return "Not found", 404

    @app.errorhandler(500)
    def server_error(_exc):
        if _wants_json():
            return jsonify({"error": "Internal server error"}), 500
        return "Internal server error", 500

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https: wss: ws:; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        return response

    return app
