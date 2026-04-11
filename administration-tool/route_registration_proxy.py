"""API-Proxy-Routen (DS-015)."""

from __future__ import annotations

from types import ModuleType

from flask import Flask, request, Response
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen as _stdlib_urlopen

PROXY_ALLOWLIST_PREFIXES = [
    "api/",  # /_proxy/api/* → allowed (REST API endpoints)
]

PROXY_DENYLIST_PREFIXES = [
    "admin",  # /_proxy/admin/* → 403 Forbidden (internal admin only)
]

PROXY_DANGEROUS_HEADERS = {
    "Cookie",
    "Set-Cookie",
    "Host",
    "X-Forwarded-For",
    "X-Real-IP",
}

PROXY_ALLOWED_HEADERS = {
    "Authorization",
    "Content-Type",
    "Accept",
    "Accept-Language",
    "User-Agent",
}


def register_proxy_routes(app: Flask, app_module: ModuleType) -> None:
    @app.route("/_proxy/<path:subpath>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    def proxy_api(subpath: str):
        """Proxy API requests to the backend to avoid browser CORS limitations."""
        try:
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
            for header_name in PROXY_ALLOWED_HEADERS:
                header_value = request.headers.get(header_name)
                if header_value:
                    headers[header_name] = header_value

            for header in PROXY_DANGEROUS_HEADERS:
                headers.pop(header, None)

            print(f"\n[PROXY DEBUG] {request.method} /_proxy/{subpath}")
            print(f"[PROXY DEBUG] Target: {target}")
            print(f"[PROXY DEBUG] Headers: {dict(headers)}")
            print(f"[PROXY DEBUG] Body length: {len(body) if body else 0}")
            if body:
                try:
                    print(f"[PROXY DEBUG] Body: {body.decode('utf-8')}")
                except Exception:
                    print(f"[PROXY DEBUG] Body (raw): {body}")

            req = Request(target, data=body, method=request.method, headers=headers)
            urlopen_fn = getattr(app_module, "urlopen", _stdlib_urlopen)
            with urlopen_fn(req, timeout=20) as resp:
                resp_body = resp.read()
                content_type = resp.headers.get("Content-Type", "application/json")
                print(f"[PROXY DEBUG] Response: {resp.status}")
                return Response(resp_body, status=resp.status, content_type=content_type)
        except HTTPError as e:
            err_body = e.read() if hasattr(e, "read") else b""
            print(f"[PROXY DEBUG] HTTPError: {e.code}")
            print(f"[PROXY DEBUG] Error body: {err_body[:200]}")
            content_type = getattr(e, "headers", {}).get("Content-Type", "application/json")
            return Response(err_body, status=int(getattr(e, "code", 502)), content_type=content_type)
        except URLError as e:
            print(f"[PROXY DEBUG] URLError: {e}")
            return Response("Upstream network error", status=502, mimetype="text/plain")
        except Exception as e:
            print(f"\n{'!'*60}")
            print("[PROXY DEBUG] UNEXPECTED ERROR")
            print(f"Error: {e}")
            import traceback

            print(traceback.format_exc())
            print(f"{'!'*60}\n")
            raise
