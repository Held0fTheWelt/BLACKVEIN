"""Service token authentication for MCP operator endpoints.

Provides the @require_mcp_service_token decorator for protecting
read-only operator endpoints with environment-based token validation.
"""

import os
import hmac
from functools import wraps
from flask import request, jsonify


def require_mcp_service_token(f):
    """Decorator: validate MCP_SERVICE_TOKEN from Authorization header.

    - Reads MCP_SERVICE_TOKEN from environment (required, no fallback).
    - If missing/empty: return 503 JSON (misconfiguration).
    - Expects header: Authorization: Bearer <token>
    - If missing/invalid token: return 401 JSON (unauthorized).
    - Uses constant-time comparison to prevent timing attacks.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if MCP_SERVICE_TOKEN is configured
        token = os.getenv("MCP_SERVICE_TOKEN", "").strip()
        if not token:
            return jsonify({
                "error": {
                    "code": "MISCONFIGURED",
                    "message": "MCP_SERVICE_TOKEN not configured"
                }
            }), 503

        # Extract Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Missing or invalid Authorization header"
                }
            }), 401

        provided_token = auth_header[7:]  # Strip "Bearer " prefix

        # Constant-time comparison
        if not hmac.compare_digest(provided_token, token):
            return jsonify({
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid token"
                }
            }), 401

        return f(*args, **kwargs)
    return decorated_function
