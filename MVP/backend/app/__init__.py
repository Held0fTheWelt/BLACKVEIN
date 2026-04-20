import logging
import os
import sys
import threading
import time
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from flask import jsonify, request
from flask_wtf.csrf import CSRFProtect

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from app.config import Config
from app.extensions import init_app as init_extensions, limiter
from app.api import register_api
from app.info import info_bp
from app.web import web_bp


def _wants_json():
    """True if the current request is for the API (JSON response expected)."""
    return request.path.startswith("/api/")


def _schedule_token_blacklist_cleanup(app):
    """Schedule a daily cleanup task for expired JWT tokens.

    Runs once per day to delete expired tokens from the blacklist.
    Prevents unbounded growth of the token_blacklist table in production.

    Args:
        app: Flask application instance
    """
    logger = logging.getLogger(__name__)

    def cleanup_worker():
        """Worker thread that periodically cleans up expired tokens."""
        next_cleanup = None
        cleanup_interval = 24 * 3600  # 24 hours in seconds

        while True:
            try:
                now = datetime.now(timezone.utc)

                # Initialize or calculate next cleanup time
                if next_cleanup is None:
                    # Schedule for next day at a fixed time (e.g., 2 AM UTC)
                    # to minimize impact on active users
                    next_cleanup = now.replace(hour=2, minute=0, second=0, microsecond=0)
                    if next_cleanup <= now:
                        next_cleanup += timedelta(days=1)

                # Wait until cleanup time
                wait_seconds = (next_cleanup - datetime.now(timezone.utc)).total_seconds()
                if wait_seconds > 0:
                    time.sleep(min(wait_seconds, 60))  # Check every minute for graceful shutdown
                    continue

                # Run cleanup within app context
                with app.app_context():
                    from app.models.token_blacklist import TokenBlacklist

                    deleted_count = TokenBlacklist.cleanup_expired()
                    if deleted_count > 0:
                        logger.info(
                            f"Token blacklist maintenance: deleted {deleted_count} "
                            f"expired tokens at {datetime.now(timezone.utc).isoformat()}"
                        )

                # Schedule next cleanup for 24 hours later
                next_cleanup = next_cleanup + timedelta(days=1)

            except Exception as e:
                # Log error but continue running; don't crash the background thread
                logger.error(
                    f"Error during token blacklist cleanup: {e}",
                    exc_info=True
                )
                # Retry in 5 minutes if error occurs
                time.sleep(300)

    # Start cleanup worker as daemon thread (won't block shutdown)
    if not app.config.get("TESTING"):
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.name = "TokenBlacklistCleanup"
        cleanup_thread.start()
        logger.debug("Started token blacklist cleanup scheduler (daily at 2 AM UTC)")


def create_app(config_object=None):
    from flask import Flask, redirect, url_for
    _root = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__)
    app.config.from_object(config_object or Config)
    # Handle SECRET_KEY: auto-generate in dev if missing or placeholder
    secret_key = app.config.get("SECRET_KEY", "")
    if not secret_key or secret_key == "change-me-in-production":
        if app.config.get("TESTING"):
            app.config["SECRET_KEY"] = "test-secret-key-for-testing"
        elif app.config.get("ENV") != "production":
            import secrets
            app.config["SECRET_KEY"] = secrets.token_urlsafe(32)
        else:
            raise ValueError("SECRET_KEY must be set in environment. Use .env or export.")
    # Validate JWT_SECRET_KEY meets cryptographic security standards (32+ bytes / 256 bits)
    jwt_secret = app.config.get("JWT_SECRET_KEY", "")

    # Auto-generate key if placeholder or missing in non-TESTING mode
    if not jwt_secret or jwt_secret == "change-me-in-production-jwt" or len(jwt_secret.encode("utf-8")) < 32:
        if app.config.get("TESTING"):
            # In testing, use a fixed fallback
            jwt_secret = "test-key-32-bytes-minimum-value"
            app.config["JWT_SECRET_KEY"] = jwt_secret
        elif app.config.get("ENV") != "production":
            # In development, auto-generate
            import secrets
            jwt_secret = secrets.token_urlsafe(32)
            app.config["JWT_SECRET_KEY"] = jwt_secret
            app.logger.warning("Generated JWT_SECRET_KEY automatically. Update .env to persist across restarts.")
        else:
            # In production, fail hard
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 bytes (256 bits). "
                "Generate a strong key with: python -c 'import secrets; print(secrets.token_urlsafe(32))' "
                "and set it in your .env file."
            )

    # Verify email verification is enforced in production (strict check only in production env)
    if app.config.get("ENV") == "production":
        if not app.config.get("REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN"):
            raise ValueError(
                "SECURITY VIOLATION: Email verification MUST be enforced in production. "
                "Set REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN=true in your environment. "
                "This prevents unauthorized account access and protects user accounts."
            )

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

    # Startup log: always show which mode we're in (INFO in tests to avoid WARNING noise in pytest output)
    if app.config.get("TESTING"):
        mode = "TESTING"
    elif app.config.get("MAIL_ENABLED"):
        mode = "NORMAL (MAIL_ENABLED=1)"
    else:
        mode = "DEV (MAIL_ENABLED=0)"
    _startup_msg = "Running BETTER TOMORROW Backend [mode: %s]"
    # Use Flask's testing flag so startup is INFO (no pytest WARNING noise), not WARNING.
    if app.testing:
        app.logger.info(_startup_msg, mode)
    else:
        app.logger.warning(_startup_msg, mode)

    init_extensions(app)
    limiter.default_limits = [app.config.get("RATELIMIT_DEFAULT", "100 per minute")]

    from app.services.play_service_control_service import (
        bootstrap_play_service_control,
        validate_play_service_env_pairing,
    )

    bootstrap_play_service_control(app)
    validate_play_service_env_pairing(app)

    # Schedule daily cleanup of expired JWT tokens from blacklist
    _schedule_token_blacklist_cleanup(app)

    # JWT error responses (API only)
    from app.extensions import jwt
    @jwt.unauthorized_loader
    def unauthorized_callback(_):
        return jsonify({"error": "Authorization required. Missing or invalid token."}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(_err):
        return jsonify({"error": "Invalid or expired token."}), 401

    app.register_blueprint(info_bp, url_prefix="/backend")
    app.register_blueprint(web_bp)
    register_api(app)

    from app.runtime.routing_registry_bootstrap import init_routing_registry_bootstrap

    init_routing_registry_bootstrap(app)

    csrf = CSRFProtect(app)
    from app.api.v1 import api_v1_bp
    csrf.exempt(api_v1_bp)

    # HTTPS enforcement: redirect HTTP to HTTPS in production
    if app.config.get("ENFORCE_HTTPS") and not app.config.get("TESTING"):
        @app.before_request
        def enforce_https():
            """Redirect HTTP requests to HTTPS in production."""
            if request.scheme == "http" and not app.debug:
                url = request.url.replace("http://", "https://", 1)
                return redirect(url, code=301)

    @app.errorhandler(404)
    def not_found(_e):
        if _wants_json():
            return jsonify({"error": "Not found"}), 404
        return "Not found", 404

    @app.errorhandler(429)
    def ratelimit_handler(_request):
        return jsonify({"error": "Too many requests. Please try again later."}), 429

    @app.errorhandler(500)
    def server_error(_e):
        if _wants_json():
            return jsonify({"error": "Internal server error"}), 500
        return "Internal server error", 500

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        connect_sources = ["'self'", "https:"]
        play_service_public_url = (app.config.get("PLAY_SERVICE_PUBLIC_URL") or "").strip()
        if play_service_public_url:
            parsed = urlparse(play_service_public_url)
            if parsed.scheme and parsed.netloc:
                connect_sources.append(f"{parsed.scheme}://{parsed.netloc}")
                ws_scheme = "wss" if parsed.scheme == "https" else "ws"
                connect_sources.append(f"{ws_scheme}://{parsed.netloc}")
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdnjs.cloudflare.com; "
            "style-src 'self' https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://fonts.gstatic.com; "
            f"connect-src {' '.join(connect_sources)}; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        if app.config.get("ENFORCE_HTTPS") and not app.config.get("TESTING"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    return app
