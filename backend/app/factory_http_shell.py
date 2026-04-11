"""Error handlers, HTTPS redirect, security headers, JWT API loaders (DS-042)."""

from __future__ import annotations

from urllib.parse import urlparse

from flask import Flask, jsonify, redirect, request

from app.extensions import jwt


def _wants_json() -> bool:
    return request.path.startswith("/api/")


def register_http_shell(app: Flask) -> None:
    @jwt.unauthorized_loader
    def unauthorized_callback(_):
        return jsonify({"error": "Authorization required. Missing or invalid token."}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(_err):
        return jsonify({"error": "Invalid or expired token."}), 401

    if app.config.get("ENFORCE_HTTPS") and not app.config.get("TESTING"):

        @app.before_request
        def enforce_https():
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
