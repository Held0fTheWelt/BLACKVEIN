"""Globale Fehlerbehandlung und Security-Header (DS-015)."""

from __future__ import annotations

from typing import Any, Callable

from flask import Flask


def register_security_hooks(
    app: Flask,
    *,
    backend_origin_fn: Callable[[], str | None],
) -> None:
    @app.errorhandler(500)
    def handle_500_error(error: Any):
        """Log 500 errors with full details for debugging."""
        import traceback

        print(f"\n{'!'*60}")
        print("500 ERROR OCCURRED")
        print(f"{'!'*60}")
        print(f"Error: {error}")
        print("Traceback:")
        print(traceback.format_exc())
        print(f"{'!'*60}\n")
        return "Internal Server Error", 500

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        connect_src = ["'self'", "https:"]
        origin = backend_origin_fn()
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
