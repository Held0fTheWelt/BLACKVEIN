"""Aggregated system diagnosis for administration-tool operator view (single backend endpoint)."""

from __future__ import annotations

import copy
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from typing import Any

import httpx
from flask import current_app
from sqlalchemy import text

from app.extensions import db
from app.services.ai_stack_evidence_service import build_release_readiness_report
from app.services.game_content_service import list_published_experience_payloads
from app.services.game_service import has_complete_play_service_config

UPSTREAM_TIMEOUT_S = 0.75
INTERNAL_TIMEOUT_S = 0.25
CACHE_TTL_S = 5.0

_cache_lock = threading.Lock()
_cached_payload: dict[str, Any] | None = None
_cached_at_monotonic: float = 0.0
_cached_at_wall: float = 0.0


def _run_with_app_ctx(app, fn):
    with app.app_context():
        return fn()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _play_internal_headers_from_config(cfg: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    api_key = (cfg.get("PLAY_SERVICE_INTERNAL_API_KEY") or "").strip()
    if api_key:
        headers["X-Play-Service-Key"] = api_key
    return headers


def _internal_base_url_from_config(cfg: dict[str, Any]) -> str | None:
    u = (cfg.get("PLAY_SERVICE_INTERNAL_URL") or "").strip().rstrip("/")
    return u or None


def _check_backend_api(self_base_url: str) -> dict[str, Any]:
    """GET /api/v1/health on this backend (self-check)."""
    url = f"{self_base_url.rstrip('/')}/api/v1/health"
    t0 = time.perf_counter()
    timed_out = False
    try:
        with httpx.Client(timeout=INTERNAL_TIMEOUT_S) as client:
            r = client.get(url)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        if r.status_code != 200:
            return {
                "id": "backend_api",
                "label": "Backend API",
                "status": "fail",
                "message": f"GET /api/v1/health returned HTTP {r.status_code}",
                "latency_ms": latency_ms,
                "timed_out": False,
                "critical": True,
                "source": "GET /api/v1/health",
                "details": {"http_status": r.status_code, "endpoint": "/api/v1/health"},
            }
        body = r.json() if r.content else {}
        if not isinstance(body, dict) or body.get("status") != "ok":
            return {
                "id": "backend_api",
                "label": "Backend API",
                "status": "fail",
                "message": "Health response missing status ok",
                "latency_ms": latency_ms,
                "timed_out": False,
                "critical": True,
                "source": "GET /api/v1/health",
                "details": {"endpoint": "/api/v1/health", "body": body},
            }
        return {
            "id": "backend_api",
            "label": "Backend API",
            "status": "running",
            "message": "GET /api/v1/health returned status ok",
            "latency_ms": latency_ms,
            "timed_out": False,
            "critical": True,
            "source": "GET /api/v1/health",
            "details": {"endpoint": "/api/v1/health"},
        }
    except httpx.TimeoutException:
        timed_out = True
        latency_ms = int((time.perf_counter() - t0) * 1000)
    except Exception as exc:
        return {
            "id": "backend_api",
            "label": "Backend API",
            "status": "fail",
            "message": f"Health check failed: {exc}",
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "timed_out": False,
            "critical": True,
            "source": "GET /api/v1/health",
            "details": {"endpoint": "/api/v1/health", "error": str(exc)},
        }
    return {
        "id": "backend_api",
        "label": "Backend API",
        "status": "fail",
        "message": "timeout",
        "latency_ms": latency_ms,
        "timed_out": timed_out,
        "critical": True,
        "source": "GET /api/v1/health",
        "details": {"endpoint": "/api/v1/health", "reason": "timeout"},
    }


def _check_database() -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        db.session.execute(text("SELECT 1")).scalar()
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "id": "database",
            "label": "Database",
            "status": "running",
            "message": "Database query succeeded",
            "latency_ms": latency_ms,
            "timed_out": False,
            "critical": True,
            "source": "SQL SELECT 1",
            "details": {},
        }
    except Exception as exc:
        return {
            "id": "database",
            "label": "Database",
            "status": "fail",
            "message": str(exc),
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "timed_out": False,
            "critical": True,
            "source": "SQL SELECT 1",
            "details": {"error": str(exc)},
        }


def _check_play_service_configuration() -> dict[str, Any]:
    if not has_complete_play_service_config():
        return {
            "id": "play_service_configuration",
            "label": "Play-service configuration",
            "status": "fail",
            "message": "Required PLAY_SERVICE_PUBLIC_URL, PLAY_SERVICE_INTERNAL_URL, and PLAY_SERVICE_SHARED_SECRET are not all set",
            "critical": True,
            "source": "app.config play-service keys",
            "details": {},
        }
    return {
        "id": "play_service_configuration",
        "label": "Play-service configuration",
        "status": "running",
        "message": "Play-service integration URLs and shared secret are configured",
        "critical": True,
        "source": "app.config play-service keys",
        "details": {},
    }


def _check_play_http(
    *,
    internal_base_url: str,
    headers: dict[str, str],
    path: str,
    check_id: str,
    label: str,
    ready_semantics: bool,
) -> dict[str, Any]:
    base = internal_base_url.rstrip("/")
    url = f"{base}{path}"
    t0 = time.perf_counter()
    timed_out = False
    try:
        with httpx.Client(base_url=base, timeout=UPSTREAM_TIMEOUT_S, headers=headers) as client:
            r = client.get(path)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        if r.status_code != 200:
            return {
                "id": check_id,
                "label": label,
                "status": "fail",
                "message": f"HTTP {r.status_code} from play service",
                "latency_ms": latency_ms,
                "timed_out": False,
                "critical": True,
                "source": f"GET {path}",
                "details": {"url": url, "http_status": r.status_code},
            }
        body = r.json() if r.content else {}
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
    except httpx.TimeoutException:
        timed_out = True
        latency_ms = int((time.perf_counter() - t0) * 1000)
    except Exception as exc:
        return {
            "id": check_id,
            "label": label,
            "status": "fail",
            "message": str(exc),
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "timed_out": False,
            "critical": True,
            "source": f"GET {path}",
            "details": {"url": url, "error": str(exc)},
        }
    return {
        "id": check_id,
        "label": label,
        "status": "fail",
        "message": "timeout",
        "latency_ms": latency_ms,
        "timed_out": timed_out,
        "critical": True,
        "source": f"GET {path}",
        "details": {"url": url, "reason": "timeout"},
    }


def _check_published_feed() -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        items = list_published_experience_payloads()
        latency_ms = int((time.perf_counter() - t0) * 1000)
        if not items:
            return {
                "id": "published_experiences_feed",
                "label": "Published experiences feed",
                "status": "initialized",
                "message": "Feed is reachable but no published experiences yet",
                "latency_ms": latency_ms,
                "timed_out": False,
                "critical": False,
                "source": "list_published_experience_payloads",
                "details": {"count": 0},
            }
        return {
            "id": "published_experiences_feed",
            "label": "Published experiences feed",
            "status": "running",
            "message": f"{len(items)} published experience(s) available",
            "latency_ms": latency_ms,
            "timed_out": False,
            "critical": False,
            "source": "list_published_experience_payloads",
            "details": {"count": len(items)},
        }
    except Exception as exc:
        return {
            "id": "published_experiences_feed",
            "label": "Published experiences feed",
            "status": "fail",
            "message": str(exc),
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "timed_out": False,
            "critical": False,
            "source": "list_published_experience_payloads",
            "details": {"error": str(exc)},
        }


def _check_ai_stack_readiness(trace_id: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        report = build_release_readiness_report(trace_id=trace_id)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        overall = report.get("overall_status") if isinstance(report, dict) else None
        if overall == "ready":
            return {
                "id": "ai_stack_release_readiness",
                "label": "AI stack release readiness",
                "status": "running",
                "message": "Release readiness aggregate reports ready",
                "latency_ms": latency_ms,
                "timed_out": False,
                "critical": False,
                "source": "build_release_readiness_report",
                "details": {"overall_status": overall},
            }
        if overall == "partial":
            return {
                "id": "ai_stack_release_readiness",
                "label": "AI stack release readiness",
                "status": "initialized",
                "message": "Release readiness aggregate is partial (not fully closed)",
                "latency_ms": latency_ms,
                "timed_out": False,
                "critical": False,
                "source": "build_release_readiness_report",
                "details": {"overall_status": overall},
            }
        return {
            "id": "ai_stack_release_readiness",
            "label": "AI stack release readiness",
            "status": "initialized",
            "message": f"Unexpected readiness state: {overall!r}",
            "latency_ms": latency_ms,
            "timed_out": False,
            "critical": False,
            "source": "build_release_readiness_report",
            "details": {"overall_status": overall},
        }
    except Exception as exc:
        return {
            "id": "ai_stack_release_readiness",
            "label": "AI stack release readiness",
            "status": "fail",
            "message": str(exc),
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "timed_out": False,
            "critical": False,
            "source": "build_release_readiness_report",
            "details": {"error": str(exc)},
        }


def _run_with_timeout(fn, timeout_s: float):
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn)
        try:
            return fut.result(timeout=timeout_s)
        except FuturesTimeoutError:
            return None


def _check_ai_stack_readiness_bounded(app, trace_id: str) -> dict[str, Any]:
    """Enforce internal timeout using a worker thread."""

    def _work():
        with app.app_context():
            return _check_ai_stack_readiness(trace_id)

    t0 = time.perf_counter()
    result = _run_with_timeout(_work, INTERNAL_TIMEOUT_S)
    if result is None:
        return {
            "id": "ai_stack_release_readiness",
            "label": "AI stack release readiness",
            "status": "fail",
            "message": "timeout",
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "timed_out": True,
            "critical": False,
            "source": "build_release_readiness_report",
            "details": {"reason": "timeout"},
        }
    return result


def _check_published_feed_bounded(app) -> dict[str, Any]:
    def _work():
        with app.app_context():
            return _check_published_feed()

    t0 = time.perf_counter()
    result = _run_with_timeout(_work, INTERNAL_TIMEOUT_S)
    if result is None:
        return {
            "id": "published_experiences_feed",
            "label": "Published experiences feed",
            "status": "fail",
            "message": "timeout",
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "timed_out": True,
            "critical": False,
            "source": "list_published_experience_payloads",
            "details": {"reason": "timeout"},
        }
    return result


def _check_database_bounded(app) -> dict[str, Any]:
    def _work():
        with app.app_context():
            return _check_database()

    t0 = time.perf_counter()
    result = _run_with_timeout(_work, INTERNAL_TIMEOUT_S)
    if result is None:
        return {
            "id": "database",
            "label": "Database",
            "status": "fail",
            "message": "timeout",
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "timed_out": True,
            "critical": True,
            "source": "SQL SELECT 1",
            "details": {"reason": "timeout"},
        }
    return result


def _prereq_skip_play_runtime(reason: str) -> dict[str, Any]:
    return {
        "id": "play_service_health",
        "label": "Play-service health",
        "status": "fail",
        "message": reason,
        "critical": True,
        "source": "GET /api/health",
        "details": {"skipped": True},
    }


def _prereq_skip_play_ready(reason: str) -> dict[str, Any]:
    return {
        "id": "play_service_readiness",
        "label": "Play-service readiness",
        "status": "fail",
        "message": reason,
        "critical": True,
        "source": "GET /api/health/ready",
        "details": {"skipped": True},
    }


def _resolve_overall(checks: list[dict[str, Any]]) -> str:
    critical = [c for c in checks if c.get("critical")]
    if any(c["status"] == "fail" for c in critical):
        return "fail"
    if any(c["status"] == "fail" for c in checks):
        return "initialized"
    if any(c["status"] == "initialized" for c in checks):
        return "initialized"
    if all(c["status"] == "running" for c in checks):
        return "running"
    return "initialized"


def _summary_counts(checks: list[dict[str, Any]]) -> dict[str, int]:
    out = {"running": 0, "initialized": 0, "fail": 0}
    for c in checks:
        st = c.get("status")
        if st in out:
            out[st] += 1
    return out


def _build_diagnosis(app, self_base_url: str, trace_id: str) -> dict[str, Any]:
    generated_at = _utc_now_iso()

    def _backend():
        return _check_backend_api(self_base_url)

    with app.app_context():
        cfg_snapshot = dict(current_app.config)
        play_internal_base = _internal_base_url_from_config(cfg_snapshot)
        play_hdrs = _play_internal_headers_from_config(cfg_snapshot)

    with ThreadPoolExecutor(max_workers=6) as pool:
        f_backend = pool.submit(_backend)
        f_db = pool.submit(_check_database_bounded, app)
        f_cfg = pool.submit(_run_with_app_ctx, app, _check_play_service_configuration)
        f_pub = pool.submit(_check_published_feed_bounded, app)
        f_ai = pool.submit(_check_ai_stack_readiness_bounded, app, trace_id)

        backend = f_backend.result()
        database = f_db.result()
        play_cfg = f_cfg.result()
        published = f_pub.result()
        ai = f_ai.result()

        if play_cfg["status"] != "running":
            play_health = _prereq_skip_play_runtime("Skipped: play-service configuration incomplete")
            play_ready = _prereq_skip_play_ready("Skipped: play-service configuration incomplete")
        elif not play_internal_base:
            play_health = _prereq_skip_play_runtime("PLAY_SERVICE_INTERNAL_URL missing despite config check")
            play_ready = _prereq_skip_play_ready("PLAY_SERVICE_INTERNAL_URL missing despite config check")
        else:
            f_ph = pool.submit(
                _check_play_http,
                internal_base_url=play_internal_base,
                headers=play_hdrs,
                path="/api/health",
                check_id="play_service_health",
                label="Play-service health",
                ready_semantics=False,
            )
            f_pr = pool.submit(
                _check_play_http,
                internal_base_url=play_internal_base,
                headers=play_hdrs,
                path="/api/health/ready",
                check_id="play_service_readiness",
                label="Play-service readiness",
                ready_semantics=True,
            )
            play_health = f_ph.result()
            play_ready = f_pr.result()

    checks_order = [
        backend,
        database,
        play_cfg,
        play_health,
        play_ready,
        published,
        ai,
    ]
    overall = _resolve_overall(checks_order)
    summary = _summary_counts(checks_order)

    groups: list[dict[str, Any]] = [
        {
            "id": "core_platform",
            "label": "Core platform",
            "checks": [backend, database],
        },
        {
            "id": "runtime_integration",
            "label": "Runtime integration",
            "checks": [play_cfg, play_health, play_ready],
        },
        {
            "id": "content_operations",
            "label": "Content and operations",
            "checks": [published],
        },
        {
            "id": "ai_governance",
            "label": "AI and governance",
            "checks": [ai],
        },
    ]

    return {
        "generated_at": generated_at,
        "overall_status": overall,
        "summary": summary,
        "groups": groups,
        "cache": {"ttl_seconds": int(CACHE_TTL_S), "hit": False},
    }


def get_system_diagnosis(app, *, self_base_url: str, refresh: bool, trace_id: str) -> dict[str, Any]:
    """Return diagnosis payload; optional 5s cache unless refresh is True."""
    global _cached_payload, _cached_at_monotonic, _cached_at_wall
    now = time.monotonic()
    with _cache_lock:
        if (
            not refresh
            and _cached_payload is not None
            and (now - _cached_at_monotonic) < CACHE_TTL_S
        ):
            out = copy.deepcopy(_cached_payload)
            out["cache"] = {"ttl_seconds": int(CACHE_TTL_S), "hit": True}
            out["cached"] = True
            wall = _cached_at_wall
            out["stale_seconds"] = max(0, int(time.time() - wall))
            return out

    payload = _build_diagnosis(app, self_base_url, trace_id)
    payload["cached"] = False
    payload["stale_seconds"] = 0
    with _cache_lock:
        _cached_payload = copy.deepcopy(payload)
        _cached_at_monotonic = time.monotonic()
        _cached_at_wall = time.time()
    return payload


def reset_diagnosis_cache_for_tests() -> None:
    """Clear process-local cache (tests only)."""
    global _cached_payload, _cached_at_monotonic, _cached_at_wall
    with _cache_lock:
        _cached_payload = None
        _cached_at_monotonic = 0.0
        _cached_at_wall = 0.0
