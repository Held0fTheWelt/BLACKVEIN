"""Lightweight Flask public frontend for World of Shadows.
Serves HTML and static assets only; consumes backend API for data. No database."""
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse

from flask import Flask, request, session, render_template, Response
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


# Explicit proxy allowlist and denylist rules for security hardening.
# These define which paths are allowed to be proxied to the backend.
PROXY_DENYLIST_PREFIXES = [
    "admin",           # /_proxy/admin/* → 403 Forbidden
]

PROXY_ALLOWLIST_PREFIXES = [
    "api/",            # /_proxy/api/* → allowed (REST API)
]

# Headers that are dangerous and must NEVER be forwarded to the backend.
# These can be used for header injection or privilege escalation attacks.
PROXY_DANGEROUS_HEADERS = {
    "Cookie",          # Session cookies from frontend (never forward)
    "Set-Cookie",      # Backend cookies (never forward from frontend)
    "Host",            # Host header (prevents host injection attacks)
    "X-Forwarded-For", # Client IP spoofing (not trusted from client)
    "X-Real-IP",       # Client IP spoofing (not trusted from client)
}

# Headers that are safe to forward from client to backend.
# Only these headers will be forwarded; all others are dropped.
PROXY_ALLOWED_HEADERS = {
    "Authorization",   # Bearer tokens, Basic auth
    "Content-Type",    # Request body content type
    "Accept",          # Requested response media type
    "Accept-Language", # Preferred language
    "User-Agent",      # Client information (informational only)
}


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


def _register_routes(app):
    """Register all routes and error handlers to a Flask app.

    This is factored out so routes can be registered on any app instance,
    whether created via the factory or at module level.
    """
    @app.context_processor
    def _inject_config_processor():
        """Register inject_config as a context processor."""
        return inject_config()

    @app.route("/_proxy/<path:subpath>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    def proxy_api(subpath: str):
        """Proxy API requests to the backend to avoid browser CORS limitations.

        Client calls: /_proxy/api/v1/...
        Server forwards to: {BACKEND_API_URL}/api/v1/...

        Security Model:
        - Denylist: Paths starting with any PROXY_DENYLIST_PREFIXES are blocked (403 Forbidden)
        - Headers: Only PROXY_ALLOWED_HEADERS are forwarded; PROXY_DANGEROUS_HEADERS are stripped
        - Timeouts: 20-second timeout prevents hanging requests
        - Error Mapping: HTTP and network errors are mapped consistently
        """
        # Allow preflight to succeed quickly (browser shouldn't need it for same-origin, but harmless).
        if request.method == "OPTIONS":
            return Response(status=204)

        # Security: Check denylist - block paths that start with forbidden prefixes
        for forbidden_prefix in PROXY_DENYLIST_PREFIXES:
            if subpath.startswith(forbidden_prefix):
                return Response("Forbidden", status=403, mimetype="text/plain")

        base = (app.config.get("BACKEND_API_URL") or "").rstrip("/")
        if not base:
            return Response("Backend API URL not configured", status=500, mimetype="text/plain")

        # Preserve query string
        path = "/" + subpath.lstrip("/")
        target = base + path
        if request.query_string:
            target = target + "?" + request.query_string.decode("utf-8", errors="ignore")

        body = request.get_data() if request.method in ("POST", "PUT", "PATCH") else None

        # Forward only explicitly allowed headers, strip all others and dangerous headers
        headers = {}
        for header_name in PROXY_ALLOWED_HEADERS:
            header_value = request.headers.get(header_name)
            if header_value:
                headers[header_name] = header_value

        # Ensure dangerous headers are explicitly not forwarded (defense in depth)
        for header in PROXY_DANGEROUS_HEADERS:
            headers.pop(header, None)

        req = Request(target, data=body, method=request.method, headers=headers)
        try:
            with urlopen(req, timeout=20) as resp:
                resp_body = resp.read()
                content_type = resp.headers.get("Content-Type", "application/json")
                return Response(resp_body, status=resp.status, content_type=content_type)
        except HTTPError as e:
            err_body = e.read() if hasattr(e, "read") else b""
            content_type = getattr(e, "headers", {}).get("Content-Type", "application/json")
            return Response(err_body, status=int(getattr(e, "code", 502)), content_type=content_type)
        except URLError:
            return Response("Upstream network error", status=502, mimetype="text/plain")

    @app.route("/")
    def index():
        """Public home page."""
        return render_template("index.html")

    @app.route("/news")
    def news_list():
        """Public news list page. Data loaded by JS from backend API."""
        return render_template("news.html")

    @app.route("/news/<int:news_id>")
    def news_detail(news_id):
        """Public news detail page. Data loaded by JS from backend API."""
        return render_template("news_detail.html", news_id=news_id)

    @app.route("/wiki")
    @app.route("/wiki/<path:slug>")
    def wiki_index(slug=None):
        """Public wiki page. Default slug 'wiki' for main page. Data loaded by JS from backend API."""
        return render_template("wiki_public.html", slug=slug or "wiki")

    # --- Forum (public; data from backend API) ---

    @app.route("/forum")
    def forum_index():
        """Forum categories list. Data loaded by JS from backend API."""
        return render_template("forum/index.html")

    @app.route("/forum/categories/<slug>")
    def forum_category(slug):
        """Threads in a category. Data loaded by JS from backend API."""
        return render_template("forum/category.html", category_slug=slug)

    @app.route("/forum/threads/<slug>")
    def forum_thread(slug):
        """Thread detail and posts. Data loaded by JS from backend API."""
        return render_template("forum/thread.html", thread_slug=slug)

    @app.route("/forum/notifications")
    def forum_notifications():
        """Notifications list (requires login). Data loaded by JS from backend API."""
        return render_template("forum/notifications.html")

    @app.route("/forum/saved")
    def forum_saved_threads():
        """Saved threads / bookmarks list (requires login). Data loaded by JS from backend API."""
        return render_template("forum/saved_threads.html")

    @app.route("/users/<int:user_id>/profile")
    def user_profile(user_id):
        """User profile page. Data loaded by JS from backend API."""
        return render_template("user/profile.html", user_id=user_id)

    @app.route("/forum/tags/<slug>")
    def forum_tag_detail(slug):
        """Forum tag detail page with threads. Data loaded by JS from backend API."""
        return render_template("forum/tag_detail.html", tag_slug=slug)

    # --- Management / editorial area (protected by frontend auth; backend enforces roles) ---

    @app.route("/manage")
    def manage_index():
        """Management area entry; redirects to login or dashboard (news)."""
        return render_template("manage/dashboard.html")

    @app.route("/manage/login")
    def manage_login():
        """Management login page (JWT via backend API)."""
        return render_template("manage/login.html")

    @app.route("/manage/news")
    def manage_news():
        """News management (list, create, edit, publish, unpublish, delete)."""
        return render_template("manage/news.html")

    @app.route("/manage/users")
    def manage_users():
        """User administration (admin only; table, edit, role, role_level, ban, unban)."""
        return render_template("manage/users.html")

    @app.route("/manage/roles")
    def manage_roles():
        """Role management (admin only): list, create, edit, delete roles."""
        return render_template("manage/roles.html")

    @app.route("/manage/areas")
    def manage_areas():
        """Area management (admin only): list, create, edit, delete areas."""
        return render_template("manage/areas.html")

    @app.route("/manage/feature-areas")
    def manage_feature_areas():
        """Feature/view to area access mapping (admin only)."""
        return render_template("manage/feature_areas.html")

    @app.route("/manage/wiki")
    def manage_wiki():
        """Wiki editor (markdown source, preview, save)."""
        return render_template("manage/wiki.html")

    @app.route("/manage/slogans")
    def manage_slogans():
        """Slogan management (moderator+): CRUD, activate/deactivate, placement resolution."""
        return render_template("manage/slogans.html")

    @app.route("/manage/data")
    def manage_data():
        """Data export/import (admin only)."""
        return render_template("manage/data.html")

    @app.route("/manage/forum")
    def manage_forum():
        """Forum management (moderation, categories, reports)."""
        return render_template("manage/forum.html")

    @app.route("/manage/analytics")
    def manage_analytics():
        """Community analytics dashboard."""
        return render_template("manage_analytics.html")

    @app.route("/manage/moderator-dashboard")
    def manage_moderator_dashboard():
        """Moderator dashboard with queue and recent actions."""
        return render_template("manage_moderator_dashboard.html")

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        connect_src = ["'self'", "https:"]
        origin = _backend_origin()
        if origin and origin not in ("https:", "'self'"):
            connect_src.append(origin)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src " + " ".join(connect_src) + "; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp
        return response


def create_app(test_config=None):
    """Application factory for creating Flask app instances.

    Args:
        test_config: Optional dict of config overrides for testing.
                    Supports: BACKEND_API_URL, SECRET_KEY, TESTING

    Returns:
        Configured Flask application instance.

    Deterministic: Same inputs produce identical app configurations.
    No import-time side effects: App creation is explicit and controllable.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="/static",
    )

    # Load environment from .env (local dev convenience) only if not in test mode
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

    app.config["BACKEND_API_URL"] = backend_url

    # Configure secret key with security validation
    if test_config and "SECRET_KEY" in test_config:
        secret = test_config["SECRET_KEY"]
    else:
        secret = os.environ.get("SECRET_KEY", "").strip()

    if not secret:
        # Generate a secure random key if SECRET_KEY is not set
        secret = secrets.token_urlsafe(32)
        # Only print warning if not in test mode
        if test_config is None or not test_config.get("TESTING"):
            print("Warning: SECRET_KEY not found in environment. Generated a new one.")

    app.secret_key = secret

    # Session cookie security hardening
    app.config["SESSION_COOKIE_SECURE"] = True  # Only send over HTTPS
    app.config["SESSION_COOKIE_HTTPONLY"] = True  # No JavaScript access
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # CSRF protection
    app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour

    # Apply test config overrides if provided
    if test_config:
        app.config.update(test_config)

    # Register all routes and handlers
    _register_routes(app)

    return app


# Create global app instance for module-level access and WSGI servers
# This is loaded at module import time for compatibility with existing deployments
# New code should use create_app() factory function directly for better testability
app = create_app()


if __name__ == "__main__":
    # Use FRONTEND_PORT to avoid clashing with backend's PORT in shared .env
    port = int(os.environ.get("FRONTEND_PORT") or os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "0").strip().lower() in ("1", "true", "yes", "on")
    app.run(host="0.0.0.0", port=port, debug=debug)
