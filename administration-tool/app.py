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

# Load environment from .env (local dev convenience)
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


app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)
app.config["BACKEND_API_URL"] = BACKEND_API_URL

# CRITICAL SECURITY: Session secret must be explicitly configured via environment variable.
# Never use hardcoded defaults; always require explicit configuration.
_secret = os.environ.get("SECRET_KEY", "").strip()
if not _secret:
    # Generate a secure random key if SECRET_KEY is not set
    _secret = secrets.token_urlsafe(32)
    print("Warning: SECRET_KEY not found in environment. Generated a new one.")
app.secret_key = _secret

# Session cookie security hardening
app.config["SESSION_COOKIE_SECURE"] = True  # Only send over HTTPS
app.config["SESSION_COOKIE_HTTPONLY"] = True  # No JavaScript access
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # CSRF protection
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour


def _load_translations(lang: str) -> dict:
    """Load translation dict for lang from translations/<lang>.json. Fallback to default keys."""
    base = Path(app.root_path) / "translations"
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


@app.context_processor
def inject_config():
    """Expose backend URL, frontend config, current language, and UI translations to all templates."""
    current_lang = _resolve_language()
    t = _load_translations(current_lang)
    return {
        "backend_api_url": app.config["BACKEND_API_URL"],
        "frontend_config": {
            "backendApiUrl": app.config["BACKEND_API_URL"],
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


@app.route("/_proxy/<path:subpath>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def proxy_api(subpath: str):
    """Proxy API requests to the backend to avoid browser CORS limitations.

    Client calls: /_proxy/api/v1/...
    Server forwards to: {BACKEND_API_URL}/api/v1/...

    Security: Blocks /_proxy/admin/* paths (403 Forbidden).
    """
    # Allow preflight to succeed quickly (browser shouldn't need it for same-origin, but harmless).
    if request.method == "OPTIONS":
        return Response(status=204)

    # Security: Block admin paths
    if subpath.startswith("admin"):
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

    headers = {}
    # Forward only relevant headers, explicitly strip dangerous ones
    dangerous_headers = {"Cookie", "Set-Cookie", "Host"}
    if request.headers.get("Authorization"):
        headers["Authorization"] = request.headers["Authorization"]
    if request.headers.get("Content-Type"):
        headers["Content-Type"] = request.headers["Content-Type"]
    headers["Accept"] = request.headers.get("Accept", "application/json")
    # Ensure dangerous headers are not forwarded
    for header in dangerous_headers:
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


def _backend_origin():
    """Origin (scheme + netloc) of BACKEND_API_URL for CSP connect-src in split frontend/backend setups."""
    parsed = urlparse(BACKEND_API_URL)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


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


if __name__ == "__main__":
    # Use FRONTEND_PORT to avoid clashing with backend's PORT in shared .env
    port = int(os.environ.get("FRONTEND_PORT") or os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "0").strip().lower() in ("1", "true", "yes", "on")
    app.run(host="0.0.0.0", port=port, debug=debug)