"""Response envelope helpers for governance routes."""

from __future__ import annotations

from typing import Any

from flask import jsonify

from app.governance.errors import GovernanceError


def ok(data: dict[str, Any], status_code: int = 200):
    """Return a standard success envelope."""
    response = jsonify({"ok": True, "data": data})
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response, status_code


def fail(code: str, message: str, status_code: int, details: dict[str, Any] | None = None):
    """Return a standard error envelope."""
    return (
        jsonify(
            {
                "ok": False,
                "error": {
                    "code": code,
                    "message": message,
                    "details": details or {},
                },
            }
        ),
        status_code,
    )


def fail_from_error(err: GovernanceError):
    """Convert GovernanceError to response envelope."""
    return fail(err.code, err.message, err.status_code, err.details)
