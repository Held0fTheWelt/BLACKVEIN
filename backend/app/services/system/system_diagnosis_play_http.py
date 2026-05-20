"""Play-service internal HTTP GET + response mapping for system diagnosis (DS-018)."""

from __future__ import annotations

import time
from typing import Any

import httpx


def fetch_play_internal_get(
    *,
    internal_base_url: str,
    path: str,
    headers: dict[str, str],
    timeout_s: float,
) -> tuple[str, int, httpx.Response]:
    """GET ``path`` on play internal base; returns ``(absolute_url, latency_ms, response)``."""
    base = internal_base_url.rstrip("/")
    url = f"{base}{path}"
    t0 = time.perf_counter()
    with httpx.Client(base_url=base, timeout=timeout_s, headers=headers) as client:
        r = client.get(path)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    return url, latency_ms, r


def play_http_check_result_from_response(
    *,
    check_id: str,
    label: str,
    path: str,
    url: str,
    latency_ms: int,
    response: httpx.Response,
    ready_semantics: bool,
) -> dict[str, Any]:
    """Map a successful transport-layer response to a diagnosis check dict."""
    if response.status_code != 200:
        return {
            "id": check_id,
            "label": label,
            "status": "fail",
            "message": f"HTTP {response.status_code} from play service",
            "latency_ms": latency_ms,
            "timed_out": False,
            "critical": True,
            "source": f"GET {path}",
            "details": {"url": url, "http_status": response.status_code},
        }
    body = response.json() if response.content else {}
    if not isinstance(body, dict):
        return {
            "id": check_id,
            "label": label,
            "status": "fail",
            "message": "Invalid JSON from play service",
            "latency_ms": latency_ms,
            "timed_out": False,
            "critical": True,
            "source": f"GET {path}",
            "details": {"url": url},
        }
    st = body.get("status")
    if st != "ok" and not ready_semantics:
        return {
            "id": check_id,
            "label": label,
            "status": "fail",
            "message": f"Unexpected status field: {st!r}",
            "latency_ms": latency_ms,
            "timed_out": False,
            "critical": True,
            "source": f"GET {path}",
            "details": {"url": url, "body": body},
        }
    if ready_semantics:
        if st == "ready":
            return {
                "id": check_id,
                "label": label,
                "status": "running",
                "message": "Play-service readiness reports ready",
                "latency_ms": latency_ms,
                "timed_out": False,
                "critical": True,
                "source": f"GET {path}",
                "details": {"url": url},
            }
        if st in ("initializing", "partial", "degraded"):
            return {
                "id": check_id,
                "label": label,
                "status": "initialized",
                "message": f"Readiness status is {st!r}",
                "latency_ms": latency_ms,
                "timed_out": False,
                "critical": True,
                "source": f"GET {path}",
                "details": {"url": url, "body": body},
            }
        return {
            "id": check_id,
            "label": label,
            "status": "initialized",
            "message": f"Readiness not confirmed (status={st!r})",
            "latency_ms": latency_ms,
            "timed_out": False,
            "critical": True,
            "source": f"GET {path}",
            "details": {"url": url, "body": body},
        }
    return {
        "id": check_id,
        "label": label,
        "status": "running",
        "message": "Play-service health returned status ok",
        "latency_ms": latency_ms,
        "timed_out": False,
        "critical": True,
        "source": f"GET {path}",
        "details": {"url": url},
    }


def play_http_check_failure_result(
    *,
    check_id: str,
    label: str,
    path: str,
    url: str,
    message: str,
    latency_ms: int,
    timed_out: bool,
    details: dict[str, Any],
) -> dict[str, Any]:
    """Uniform failure dict after transport or unexpected errors."""
    return {
        "id": check_id,
        "label": label,
        "status": "fail",
        "message": message,
        "latency_ms": latency_ms,
        "timed_out": timed_out,
        "critical": True,
        "source": f"GET {path}",
        "details": details,
    }
