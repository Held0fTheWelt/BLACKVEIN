"""Lightweight Flask public frontend for World of Shadows.
Serves HTML and static assets only; consumes backend API for data. No database."""
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from flask import Flask, Response, render_template, request, session
import secrets

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
        if not url.startswith(("http://", "https://")):
            raise ValueError("service_url must have http or https scheme")
        parsed_url = url.replace("http://", "").replace("https://", "")
        if not parsed_url or parsed_url.isspace():
            raise ValueError("service_url must have http or https scheme")
    return True


def _load_translations(lang: str) -> dict:
    try:
        from flask import current_app
        root_path = current_app.root_path
    except RuntimeError:
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
    parsed = urlparse(BACKEND_API_URL)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


PROXY_ALLOWLIST_PREFIXES = ["api/"]
PROXY_DENYLIST_PREFIXES = ["admin"]
PROXY_DANGEROUS_HEADERS = {"Cookie", "Set-Cookie", "Host", "X-Forwarded-For", "X-Real-IP"}
PROXY_ALLOWED_HEADERS = {"Authorization", "Content-Type", "Accept", "Accept-Language", "User-Agent"}


def inject_config():
    from flask import current_app
    current_lang = _resolve_language()
    t = _load_translations(current_lang)
    return {
        "backend_api_url": current_app.config["BACKEND_API_URL"],
        "frontend_config": {
            "backendApiUrl": current_app.config["BACKEND_API_URL"],
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
    @app.context_processor
    def _inject_config_processor():
        return inject_config()

    @app.route("/_proxy/<path:subpath>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    def proxy_api(subpath: str):
        if request.method == "OPTIONS":
            return Response(status=204)
        is_allowed = any(subpath.startswith(prefix) for prefix in PROXY_ALLOWLIST_PREFIXES)
        is_denied = any(subpath.startswith(prefix) for prefix in PROXY_DENYLIST_PREFIXES)
        if not is_allowed or is_denied:
            return Response("Forbidden", status=403, mimetype="text/plain")
        base = (app.config.get("BACKEND_API_URL") or "").rstrip("/")
        if not base:
            return Response("Backend API URL not configured", status=500, mimetype="text/plain")
        path = "/" + subpath.lstrip("/")
        target = base + path
        if request.query_string:
            target = target + "?" + request.query_string.decode("utf-8", errors="ignore")
        body = request.get_data() if request.method in ("POST", "PUT", "PATCH") else None
        headers = {}
        for k, v in request.headers.items():
            if k in PROXY_DANGEROUS_HEADERS:
                continue
            if k in PROXY_ALLOWED_HEADERS:
                headers[k] = v
        req = Request(target, data=body, method=request.method)
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urlopen(req, timeout=20) as resp:
                out = resp.read()
                response = Response(out, status=resp.getcode())
                ct = resp.headers.get("Content-Type")
                if ct:
                    response.headers["Content-Type"] = ct
                else:
                    response.headers["Content-Type"] = "application/json"
                return response
        except HTTPError as e:
            body = e.read()
            response = Response(body, status=e.code)
            ct = e.headers.get("Content-Type") if e.headers else None
            if ct:
                response.headers["Content-Type"] = ct
            return response
        except URLError:
            return Response("Upstream network error", status=502, mimetype="text/plain")

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/news", endpoint="news_list")
    @app.route("/news", endpoint="news")
    def news():
        return render_template("news.html")

    @app.route("/news/<int:article_id>")
    def news_detail(article_id):
        return render_template("news_detail.html", news_id=article_id)

    @app.route("/wiki", endpoint="wiki_index")
    @app.route("/wiki", endpoint="wiki_page")
    @app.route("/wiki/<path:slug>")
    def wiki_page(slug="wiki"):
        return render_template("wiki_public.html", slug=slug)

    @app.route("/forum")
    def forum_index():
        return render_template("forum/index.html")

    @app.route("/forum/categories/<slug>")
    def forum_category(slug):
        return render_template("forum/category.html", category_slug=slug)

    @app.route("/forum/threads/<slug>")
    def forum_thread(slug):
        return render_template("forum/thread.html", thread_slug=slug)

    @app.route("/forum/notifications")
    def forum_notifications():
        return render_template("forum/notifications.html")

    @app.route("/forum/saved")
    def forum_saved_threads():
        return render_template("forum/saved_threads.html")

    @app.route("/users/<int:user_id>/profile")
    def user_profile(user_id):
        return render_template("user/profile.html", user_id=user_id)

    @app.route("/forum/tags/<slug>")
    def forum_tag_detail(slug):
        return render_template("forum/tag_detail.html", tag_slug=slug)

    @app.route("/manage")
    def manage_index():
        return render_template("manage/dashboard.html")

    @app.route("/manage/login")
    def manage_login():
        return render_template("manage/login.html")

    @app.route("/manage/news")
    def manage_news():
        return render_template("manage/news.html")

    @app.route("/manage/users")
    def manage_users():
        return render_template("manage/users.html")

    @app.route("/manage/roles")
    def manage_roles():
        return render_template("manage/roles.html")

    @app.route("/manage/areas")
    def manage_areas():
        return render_template("manage/areas.html")

    @app.route("/manage/feature-areas")
    def manage_feature_areas():
        return render_template("manage/feature_areas.html")

    @app.route("/manage/wiki")
    def manage_wiki():
        return render_template("manage/wiki.html")

    @app.route("/manage/slogans")
    def manage_slogans():
        return render_template("manage/slogans.html")

    @app.route("/manage/data")
    def manage_data():
        return render_template("manage/data.html")

    @app.route("/manage/forum")
    def manage_forum():
        return render_template("manage/forum.html")

    @app.route("/manage/game-content")
    def manage_game_content():
        return render_template("manage/game_content.html")

    @app.route("/manage/game-operations")
    def manage_game_operations():
        return render_template("manage/game_operations.html")

    @app.route("/manage/analytics")
    def manage_analytics():
        return render_template("manage_analytics.html")

    @app.route("/manage/moderator-dashboard")
    def manage_moderator_dashboard():
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
    app = Flask(__name__, template_folder="templates", static_folder="static", static_url_path="/static")

    is_test_mode = test_config is not None and test_config.get("TESTING") is True
    if test_config is None:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            _here = Path(__file__).resolve().parent
            load_dotenv(_here / ".env")
            _repo_root = _here.parent
            load_dotenv(_repo_root / ".env")
        except ImportError:
            pass

    backend_url = test_config["BACKEND_API_URL"] if test_config and "BACKEND_API_URL" in test_config else BACKEND_API_URL
    app.config["BACKEND_API_URL"] = backend_url.rstrip("/")

    if test_config and "SECRET_KEY" in test_config:
        secret = test_config["SECRET_KEY"]
    else:
        secret = os.environ.get("SECRET_KEY", "").strip()
    if not secret:
        if is_test_mode:
            secret = secrets.token_urlsafe(32)
        else:
            raise ValueError("SECRET_KEY must be provided in environment or test_config. Set the SECRET_KEY environment variable or pass it in test_config.")
    app.secret_key = secret
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = 3600
    if test_config:
        config_to_update = test_config.copy()
        if "BACKEND_API_URL" in config_to_update:
            config_to_update["BACKEND_API_URL"] = config_to_update["BACKEND_API_URL"].rstrip("/")
        app.config.update(config_to_update)

    _register_routes(app)
    return app


if not os.environ.get("SECRET_KEY"):
    os.environ["SECRET_KEY"] = "wsgi-default-insecure-key-replace-in-production"

app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("FRONTEND_PORT") or os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "0").strip().lower() in ("1", "true", "yes", "on")
    app.run(host="0.0.0.0", port=port, debug=debug)
