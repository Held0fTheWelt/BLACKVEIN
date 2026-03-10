import logging
import os
from flask import jsonify, render_template, request
from flask_wtf.csrf import CSRFProtect

from app.config import Config
from app.extensions import init_app as init_extensions, limiter
from app.web import web_bp
from app.api import register_api


def _wants_json():
    """True if the current request is for the API (JSON response expected)."""
    return request.path.startswith("/api/")


def create_app(config_object=None):
    from flask import Flask
    _root = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__, template_folder=os.path.join(_root, "web", "templates"), static_folder=os.path.join(_root, "static"))
    app.config.from_object(config_object or Config)
    if not app.config.get("TESTING") and not app.config.get("SECRET_KEY"):
        raise ValueError("SECRET_KEY must be set in environment. Use .env or export.")
    # Logging: DEBUG in test/dev, WARNING in production
    app.logger.setLevel(logging.DEBUG if (app.config.get("TESTING") or app.debug) else logging.WARNING)
    if not app.logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
        app.logger.addHandler(h)
    # Package logger (app.services.user_service etc.) so sub-loggers are captured
    pkg_logger = logging.getLogger("app")
    level = logging.DEBUG if (app.config.get("TESTING") or app.debug) else logging.WARNING
    pkg_logger.setLevel(level)
    if not pkg_logger.handlers:
        ph = logging.StreamHandler()
        ph.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
        pkg_logger.addHandler(ph)
    init_extensions(app)
    limiter.default_limits = [app.config.get("RATELIMIT_DEFAULT", "100 per minute")]

    # JWT error responses (API only)
    from app.extensions import jwt
    @jwt.unauthorized_loader
    def unauthorized_callback(_):
        return jsonify({"error": "Authorization required. Missing or invalid token."}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(_err):
        return jsonify({"error": "Invalid or expired token."}), 401

    app.register_blueprint(web_bp)
    register_api(app)
    csrf = CSRFProtect(app)
    from app.api.v1 import api_v1_bp
    csrf.exempt(api_v1_bp)

    @app.errorhandler(404)
    def not_found(_e):
        if _wants_json():
            return jsonify({"error": "Not found"}), 404
        return render_template("404.html"), 404

    @app.errorhandler(429)
    def ratelimit_handler(_request):
        return jsonify({"error": "Too many requests. Please try again later."}), 429

    @app.errorhandler(500)
    def server_error(_e):
        if _wants_json():
            return jsonify({"error": "Internal server error"}), 500
        return render_template("500.html"), 500

    return app
