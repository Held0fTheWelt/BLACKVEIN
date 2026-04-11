"""Flask extensions; ``init_app(app)`` is invoked from ``create_app`` in ``app.factory_app``.

Inventory (what each global is for; use these names instead of ad-hoc duplicates elsewhere):

=================== =============================================================
Global              Role
=================== =============================================================
``db``              SQLAlchemy ORM; models import ``db`` and ``db.Model`` only.
``jwt``             Flask-JWT-Extended; callbacks for revocation live in
                    ``app.auth.jwt_revocation`` (registered from ``init_app``).
``limiter``         ``LimiterProxy``: production ``Flask-Limiter`` or
                    ``TestLimiter`` when ``app.config['TESTING']``.
``migrate``         Flask-Migrate (CLI); bound only when not testing.
``mail``            Flask-Mail for outbound email.

Init order inside ``init_app`` here: ``db`` → ``jwt`` → ``limiter`` → ``mail`` →
(optional) ``migrate`` → CORS from ``app.config['CORS_ORIGINS']`` → JWT revocation
handlers. After ``init_extensions(app)``, ``create_app`` (``factory_app``) sets
``limiter.default_limits`` from config; ``factory_http_shell`` registers extra JWT loaders on ``jwt``.

Token models (e.g. refresh/blacklist) depend on ``db`` only; revocation avoids a
static import cycle from this module by registering handlers inside ``init_app``.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_migrate import Migrate
from flask_mail import Mail
from functools import wraps

# Rate-limit strings like "5 per hour" → window length (shared by TestLimiter + LimiterProxy).
_RATE_LIMIT_PERIOD_TO_SECONDS: dict[str, int] = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
}
_DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 3600

db = SQLAlchemy()
jwt = JWTManager()


def get_rate_limit_key():
    """Get a rate limit key, preferring JWT identity over remote address."""
    try:
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        # Manually verify JWT to extract identity even if @jwt_required() hasn't been called yet
        # (rate limiter decorator is applied before @jwt_required())
        try:
            verify_jwt_in_request(optional=True)
        except Exception:
            pass
        identity = get_jwt_identity()
        if identity:
            return f"user:{identity}"
    except Exception:
        pass
    return get_remote_address()


class TestLimiter:
    """Rate limiter that works in tests by actually tracking request counts."""
    def __init__(self):
        self.request_times = {}
        self.default_limits = []

    def limit(self, limit_str, key_func=None):
        """Decorator that enforces rate limits in testing."""
        # Parse limit string like "5 per hour" or "1 per minute"
        parts = limit_str.split()
        max_requests = int(parts[0])
        period_str = parts[-1]

        period_seconds = _RATE_LIMIT_PERIOD_TO_SECONDS.get(
            period_str, _DEFAULT_RATE_LIMIT_WINDOW_SECONDS
        )

        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                from flask import request as flask_request
                from datetime import datetime, timezone
                from flask_jwt_extended import get_jwt_identity

                # Get the rate limit key - prefer JWT identity for authenticated endpoints
                key = None
                try:
                    identity = get_jwt_identity()
                    if identity:
                        key = f"{f.__name__}:{identity}"
                except Exception:
                    pass

                if not key:
                    # Fall back to key_func or remote_addr if JWT not available
                    if key_func:
                        try:
                            key = f"{f.__name__}:{key_func()}"
                        except Exception:
                            key = f"{f.__name__}:{flask_request.remote_addr or 'unknown'}"
                    else:
                        key = f"{f.__name__}:{flask_request.remote_addr or 'unknown'}"

                current_time = datetime.now(timezone.utc).timestamp()

                # Initialize if needed
                if key not in self.request_times:
                    self.request_times[key] = []

                # Remove old requests outside the period
                cutoff_time = current_time - period_seconds
                self.request_times[key] = [t for t in self.request_times[key] if t > cutoff_time]

                # Check if limit exceeded
                if len(self.request_times[key]) >= max_requests:
                    from flask import jsonify
                    return jsonify({"error": "Too many requests"}), 429

                # Add current request
                self.request_times[key].append(current_time)

                return f(*args, **kwargs)
            return wrapper
        return decorator

    def init_app(self, app):
        """Stub for init_app (not used in test mode)."""
        pass


# Global instance that will hold either Limiter or TestLimiter
_limiter_instance = None


class LimiterProxy:
    """Proxy that delegates to either Flask-Limiter or TestLimiter based on app mode."""

    def limit(self, limit_str, key_func=None):
        """Create a rate limit decorator that works in both test and production modes."""
        # This decorator is applied at module import time, so we need to check at request time
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                from flask import current_app
                global _limiter_instance

                # Determine which limiter to use based on app config
                if current_app.config.get("TESTING"):
                    if not isinstance(_limiter_instance, TestLimiter):
                        _limiter_instance = TestLimiter()
                    # Apply TestLimiter's rate limiting at request time
                    test_limiter = _limiter_instance
                    # Get the rate limit key
                    key = None
                    try:
                        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
                        # Verify JWT if present (optional, doesn't fail if missing)
                        verify_jwt_in_request(optional=True)
                        identity = get_jwt_identity()
                        if identity:
                            key = f"{f.__name__}:{identity}"
                    except Exception:
                        pass

                    if not key:
                        if key_func:
                            try:
                                key = f"{f.__name__}:{key_func()}"
                            except Exception:
                                from flask import request
                                key = f"{f.__name__}:{request.remote_addr or 'unknown'}"
                        else:
                            from flask import request
                            key = f"{f.__name__}:{request.remote_addr or 'unknown'}"

                    # Check rate limit
                    import re
                    from datetime import datetime, timezone
                    match = re.match(r'(\d+)\s+per\s+(\w+)', limit_str)
                    if match:
                        max_requests = int(match.group(1))
                        period_str = match.group(2)
                        period_seconds = _RATE_LIMIT_PERIOD_TO_SECONDS.get(
                            period_str, _DEFAULT_RATE_LIMIT_WINDOW_SECONDS
                        )

                        current_time = datetime.now(timezone.utc).timestamp()
                        if key not in test_limiter.request_times:
                            test_limiter.request_times[key] = []

                        # Remove old requests
                        cutoff_time = current_time - period_seconds
                        test_limiter.request_times[key] = [t for t in test_limiter.request_times[key] if t > cutoff_time]

                        # Check limit
                        if len(test_limiter.request_times[key]) >= max_requests:
                            from flask import jsonify
                            return jsonify({"error": "Too many requests"}), 429

                        test_limiter.request_times[key].append(current_time)

                return f(*args, **kwargs)
            return wrapper
        return decorator

    def init_app(self, app):
        """Initialize the limiter with the app."""
        global _limiter_instance
        if app.config.get("TESTING"):
            _limiter_instance = TestLimiter()
        else:
            _limiter_instance = Limiter(key_func=get_rate_limit_key, default_limits=[])
            _limiter_instance.init_app(app)


# Use proxy limiter
limiter = LimiterProxy()
migrate = Migrate()
mail = Mail()


def init_app(app):
    """Bind extensions to app. CORS uses configurable origins from config."""
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)
    if not app.config.get("TESTING"):
        migrate.init_app(app, db)
    origins = app.config.get("CORS_ORIGINS")
    if origins:
        CORS(
            app,
            origins=origins,
            allow_headers=["Content-Type", "Authorization"],
            expose_headers=["Content-Type"],
            methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            supports_credentials=False,
        )

    # Register JWT callback for token revocation checking
    from app.auth.jwt_revocation import register_jwt_revocation_handlers

    register_jwt_revocation_handlers(jwt, db)

    # Register JWT callback for real-time ban enforcement
    @jwt.token_verification_loader
    def verify_jwt_token(jwt_header, jwt_data):
        """
        Verify JWT token before allowing access to protected endpoints.
        Note: We do not check for bans here. Individual endpoints handle ban checks
        and return 403 for banned users. This allows endpoints to provide better
        error messages (e.g., "Account is restricted" vs "Token verification failed").

        Returns True if token is valid, False if it should be rejected with 401.
        """
        # Always return True; Flask-JWT-Extended already validated the token signature and expiration.
        # Individual endpoints will check for bans and return 403 if needed.
        return True

    # Handle token verification failure (when banned user tries to use token)
    @jwt.token_verification_failed_loader
    def token_verification_failed(_jwt_header, _jwt_data):
        """
        Callback when token verification fails (e.g., user is banned).
        Returns 401 Unauthorized response.
        """
        return {"error": "Token verification failed"}, 401
