"""Lightweight Flask public frontend for World of Shadows.
Serves HTML and static assets only; consumes backend API for data. No database."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, request, session, render_template

# Backend API base URL (no trailing slash). Used for login link and for frontend JS.
# IMPORTANT: Defaults to production URL (held0fthewelt.pythonanywhere.com) for live testing.
# For local development: set BACKEND_API_URL=http://127.0.0.1:5000 or uncomment the localhost line below.
# BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:5000").rstrip("/") # LOCALHOST
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "https://held0fthewelt.pythonanywhere.com").rstrip("/")
SUPPORTED_LANGUAGES = ["de", "en"]
DEFAULT_LANGUAGE = "de"

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)
app.config["BACKEND_API_URL"] = BACKEND_API_URL
_secret = os.environ.get("SECRET_KEY", "").strip()
if not _secret:
    import sys
    if os.environ.get("FLASK_ENV") == "development" or os.environ.get("DEV_SECRETS_OK", "").lower() in ("1", "true", "yes", "on"):
        _secret = os.urandom(32).hex()
        print("Warning: SECRET_KEY not set; using random key for this run. Set SECRET_KEY for production.", file=sys.stderr)
    else:
        raise ValueError("SECRET_KEY must be set in environment for the frontend. Use .env or export.")
app.secret_key = _secret


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
            "supportedLanguages": SUPPORTED_LANGUAGES,
            "defaultLanguage": DEFAULT_LANGUAGE,
            "currentLanguage": current_lang,
        },
        "current_lang": current_lang,
        "supported_languages": SUPPORTED_LANGUAGES,
        "t": t,
    }


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
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "0").strip().lower() in ("1", "true", "yes", "on")
    app.run(host="0.0.0.0", port=port, debug=debug)
