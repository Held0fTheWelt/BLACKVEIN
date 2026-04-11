"""Lightweight Flask public frontend for World of Shadows.
Serves HTML and static assets only; consumes backend API for data. No database."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from flask import Flask, request, session
import secrets  # Import the secrets module

# Backend API base URL (no trailing slash). Used for login link and for frontend JS.
# IMPORTANT: Defaults to production URL (held0fthewelt.pythonanywhere.com) for live testing.
# For local development: set BACKEND_API_URL=http://127.0.0.1:5000 or uncomment the localhost line below.
# BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:5000").rstrip("/") # LOCALHOST
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "https://held0fthewelt.pythonanywhere.com").rstrip("/")
SUPPORTED_LANGUAGES = ["de", "en"]
DEFAULT_LANGUAGE = "de"


def validate_secret_key(secret_key, is_production=True):
    if not secret_key:
        raise ValueError("secret_key cannot be empty")
    if is_production and len(secret_key) < 32:
        raise ValueError("secret_key must be at least 32 characters in production")
    return True


def validate_service_url(url, required=True):
    if required and not url:
        raise ValueError("service_url is required")
    if url:
        if not url.startswith(('http://', 'https://')):
            raise ValueError("service_url must have http or https scheme")
        # Check that there's something after the scheme (a host)
        parsed_url = url.replace('http://', '').replace('https://', '')
        if not parsed_url or parsed_url.isspace():
            raise ValueError("service_url must have http or https scheme")
    return True


def _load_translations(lang: str) -> dict:
    """Load translation dict for lang from translations/<lang>.json. Fallback to default keys."""
    try:
        from flask import current_app
        root_path = current_app.root_path
    except RuntimeError:
        # Outside of app context, use global app if available
        if 'app' in globals():
            root_path = app.root_path
        else:
            return {}

    base = Path(root_path) / "translations"
    path = base / f"{lang}.json"
    if not path.is_file():
        path = base / f"{DEFAULT_LANGUAGE}.json"
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _resolve_language():
    """Resolve UI language: query lang -> session -> Accept-Language -> default."""
    lang = (request.args.get("lang") or "").strip().lower()
    if lang in SUPPORTED_LANGUAGES:
        session["lang"] = lang
        return lang
    if session.get("lang") in SUPPORTED_LANGUAGES:
        return session["lang"]
    accept = request.headers.get("Accept-Language", "")
    for part in accept.replace(" ", "").split(","):
        code = part.split(";")[0].split("-")[0].lower()
        if code in SUPPORTED_LANGUAGES:
            return code
    return DEFAULT_LANGUAGE


def _backend_origin():
    """Origin (scheme + netloc) of BACKEND_API_URL for CSP connect-src in split frontend/backend setups."""
    parsed = urlparse(BACKEND_API_URL)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


def inject_config():
    """Expose backend URL, frontend config, current language, and UI translations to all templates.

    This is defined at module level for backward compatibility and can be used
    both as a context processor and as a standalone function.
    """
    from flask import current_app
    current_lang = _resolve_language()
    t = _load_translations(current_lang)
    return {
        "backend_api_url": current_app.config["BACKEND_API_URL"],
        "frontend_config": {
            "backendApiUrl": current_app.config["BACKEND_API_URL"],
            # Use same-origin proxy endpoints to avoid browser CORS issues when the backend is on a different origin.
            "apiProxyBase": "/_proxy",
            "supportedLanguages": SUPPORTED_LANGUAGES,
            "defaultLanguage": DEFAULT_LANGUAGE,
            "currentLanguage": current_lang,
        },
        "current_lang": current_lang,
        "supported_languages": SUPPORTED_LANGUAGES,
        "t": t,
    }


_route_registration_module = None


def _get_route_registration():
    global _route_registration_module
    if _route_registration_module is None:
        import importlib.util
        from pathlib import Path as _Path

        _rp = _Path(__file__).resolve().parent / "route_registration.py"
        spec = importlib.util.spec_from_file_location(
            "administration_tool_route_registration", _rp
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("route_registration.py missing")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _route_registration_module = mod
    return _route_registration_module


def _register_routes(app):
    """Register routes via sibling module (DS-015 split)."""
    import sys

    _get_route_registration().register_routes(
        app,
        inject_config=inject_config,
        backend_origin_fn=_backend_origin,
        app_module=sys.modules[__name__],
    )


def create_app(test_config=None):
    """Application factory for creating Flask app instances.

    Args:
        test_config: Optional dict of config overrides for testing.
                    Supports: BACKEND_API_URL, SECRET_KEY, TESTING

    Returns:
        Configured Flask application instance.

    Deterministic: Same inputs produce identical app configurations.
    No import-time side effects: App creation is explicit and controllable.

    Security Policy:
    - Production mode: Requires SECRET_KEY in environment (fail-fast on missing)
    - Test mode (TESTING=True): Allows fallback to generated key with warning
    - Dev mode (create_app() with no test_config and explicit SECRET_KEY env var): Allowed
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="/static",
    )

    # Determine if we're in explicit test mode (TESTING=True in test_config)
    is_test_mode = test_config is not None and test_config.get("TESTING") is True

    # Load environment from .env (local dev convenience) only if NOT using test_config
    # When test_config is provided, we skip .env loading to ensure clean test isolation
    if test_config is None:
        try:
            from dotenv import load_dotenv

            load_dotenv()
            _here = Path(__file__).resolve().parent
            load_dotenv(_here / ".env")
            # Also load repo-root .env so one file can be shared with backend
            _repo_root = _here.parent
            load_dotenv(_repo_root / ".env")
        except ImportError:
            pass

    # Configure backend URL
    if test_config and "BACKEND_API_URL" in test_config:
        backend_url = test_config["BACKEND_API_URL"]
    else:
        backend_url = BACKEND_API_URL

    app.config["BACKEND_API_URL"] = backend_url.rstrip("/")

    # Configure secret key with security validation
    # Production policy: SECRET_KEY must be explicitly provided (fail-fast)
    if test_config and "SECRET_KEY" in test_config:
        # Explicit SECRET_KEY in test_config: use it
        secret = test_config["SECRET_KEY"]
    else:
        # Not in test_config, check environment
        # Note: if test_config is provided, .env is NOT loaded (clean isolation)
        secret = os.environ.get("SECRET_KEY", "").strip()

    if not secret:
        if is_test_mode:
            # Test mode (TESTING=True): allow fallback to generated key with warning
            secret = secrets.token_urlsafe(32)
            print("Warning: SECRET_KEY not found in test config. Generated a temporary test key.")
        else:
            # Production-like mode: require SECRET_KEY to be explicitly set
            raise ValueError(
                "SECRET_KEY must be provided in environment or test_config. "
                "Do not rely on auto-generated keys in production-like mode. "
                "Set the SECRET_KEY environment variable or pass it in test_config."
            )

    app.secret_key = secret

    # Session cookie security hardening
    app.config["SESSION_COOKIE_SECURE"] = True  # Only send over HTTPS
    app.config["SESSION_COOKIE_HTTPONLY"] = True  # No JavaScript access
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # CSRF protection
    app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour

    # Apply test config overrides if provided
    if test_config:
        # Make a copy to avoid modifying the input dict
        config_to_update = test_config.copy()
        # Ensure BACKEND_API_URL doesn't have trailing slashes
        if "BACKEND_API_URL" in config_to_update:
            config_to_update["BACKEND_API_URL"] = config_to_update["BACKEND_API_URL"].rstrip("/")
        app.config.update(config_to_update)

    # Register all routes and handlers
    _register_routes(app)

    return app


# Create global app instance for module-level access and WSGI servers.
# This global app export is provided for WSGI server compatibility (e.g., gunicorn, uWSGI).
# For testing and new code, prefer the create_app() factory function above for better
# testability, determinism, and control over app configuration. The factory function allows
# creating multiple isolated app instances with custom configurations without module reloading.
#
# For WSGI servers: if no SECRET_KEY is set, use a default to allow the module to import.
# This is safe because WSGI servers will override this with explicit config before production use.
if not os.environ.get("SECRET_KEY"):
    os.environ["SECRET_KEY"] = "wsgi-default-insecure-key-replace-in-production"

app = create_app()


if __name__ == "__main__":
    # Use FRONTEND_PORT to avoid clashing with backend's PORT in shared .env
    port = int(os.environ.get("FRONTEND_PORT") or os.environ.get("PORT", 5001))

    # Enable debug mode for better error reporting
    app.config["DEBUG"] = True

    # Show startup info
    print(f"\n{'='*60}")
    print(f"Administration Tool Starting")
    print(f"{'='*60}")
    print(f"Host: 0.0.0.0")
    print(f"Port: {port}")
    print(f"Debug: True (enabled for error diagnosis)")
    print(f"Backend URL: {app.config.get('BACKEND_API_URL')}")
    print(f"Template Folder: {app.template_folder}")
    print(f"Static Folder: {app.static_folder}")
    print(f"{'='*60}")
    print(f"Open: http://127.0.0.1:{port}/manage/login")
    print(f"{'='*60}\n")

    app.run(host="0.0.0.0", port=port, debug=True)
