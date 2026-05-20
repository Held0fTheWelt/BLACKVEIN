"""Persisted operator control plane for Play-Service connection (application-level only)."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from flask import Flask, has_app_context
from sqlalchemy.orm.attributes import flag_modified

from app.extensions import db
from app.models import SiteSetting

STORAGE_KEY = "play_service_control"
SCHEMA_VERSION = 1

MODE_DISABLED = "disabled"
MODE_LOCAL = "local"
MODE_DOCKER = "docker"
MODE_REMOTE = "remote"
MODES = (MODE_DISABLED, MODE_LOCAL, MODE_DOCKER, MODE_REMOTE)

UPSTREAM_TIMEOUT_S = 0.75

_PLAY_CFG_KEYS = (
    "PLAY_SERVICE_CONTROL_DISABLED",
    "PLAY_SERVICE_ALLOW_NEW_SESSIONS",
    "PLAY_SERVICE_PUBLIC_URL",
    "PLAY_SERVICE_INTERNAL_URL",
    "PLAY_SERVICE_REQUEST_TIMEOUT",
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _empty_document() -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "desired": None,
        "applied_desired": None,
        "apply_ok": None,
        "apply_message": None,
        "applied_at": None,
        "applied_by_user_id": None,
        "last_test": None,
    }


def _load_raw_document() -> dict[str, Any]:
    row = db.session.get(SiteSetting, STORAGE_KEY)
    if not row or not (row.value or "").strip():
        return _empty_document()
    try:
        data = json.loads(row.value)
    except json.JSONDecodeError:
        return _empty_document()
    if not isinstance(data, dict):
        return _empty_document()
    data.setdefault("version", SCHEMA_VERSION)
    for k in ("desired", "applied_desired", "last_test", "apply_ok", "apply_message", "applied_at", "applied_by_user_id"):
        if k not in data:
            data[k] = None
    return data


def _persist_document(doc: dict[str, Any]) -> None:
    row = db.session.get(SiteSetting, STORAGE_KEY)
    payload = json.dumps(doc, separators=(",", ":"), sort_keys=True)
    if row is None:
        db.session.add(SiteSetting(key=STORAGE_KEY, value=payload))
    else:
        row.value = payload
        flag_modified(row, "value")
    db.session.commit()


def _valid_http_url(url: str) -> bool:
    u = (url or "").strip()
    if not u:
        return False
    p = urlparse(u)
    return p.scheme in ("http", "https") and bool(p.netloc)


def validate_desired_payload(body: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """Return (normalized_desired, errors)."""
    errors: list[str] = []
    mode = (body.get("mode") or "").strip().lower()
    if mode not in MODES:
        errors.append(f"mode must be one of: {', '.join(MODES)}")
        return None, errors

    enabled = bool(body.get("enabled"))
    public_url = (body.get("public_url") or "").strip()
    internal_url = (body.get("internal_url") or "").strip()
    try:
        timeout_ms = int(body.get("request_timeout_ms", 30000))
    except (TypeError, ValueError):
        errors.append("request_timeout_ms must be an integer")
        timeout_ms = 30000
    if timeout_ms < 1000 or timeout_ms > 600_000:
        errors.append("request_timeout_ms must be between 1000 and 600000")

    allow_new = bool(body.get("allow_new_sessions", True))

    if mode == MODE_DISABLED:
        if enabled:
            errors.append("When mode is disabled, enabled must be false")
        # URLs may be empty
    else:
        if not enabled:
            errors.append("When mode is not disabled, enabled must be true for a routable configuration")
        if not _valid_http_url(public_url):
            errors.append("public_url must be a valid http(s) URL with host")
        if not _valid_http_url(internal_url):
            errors.append("internal_url must be a valid http(s) URL with host")

    if errors:
        return None, errors

    out = {
        "mode": mode,
        "enabled": enabled if mode != MODE_DISABLED else False,
        "public_url": public_url if mode != MODE_DISABLED else "",
        "internal_url": internal_url if mode != MODE_DISABLED else "",
        "request_timeout_ms": timeout_ms,
        "allow_new_sessions": allow_new,
    }
    return out, []


def _desired_from_env_baseline(app: Flask) -> dict[str, Any]:
    """Implicit desired view when nothing saved yet (operator-safe)."""
    pub = (app.config.get("PLAY_SERVICE_PUBLIC_URL") or "").strip()
    inn = (app.config.get("PLAY_SERVICE_INTERNAL_URL") or "").strip()
    mode = MODE_DISABLED
    if pub or inn:
        mode = MODE_REMOTE
    try:
        timeout_ms = int(float(app.config.get("PLAY_SERVICE_REQUEST_TIMEOUT", 30)) * 1000)
    except (TypeError, ValueError):
        timeout_ms = 30000
    return {
        "mode": mode,
        "enabled": bool(pub and inn and _secret_present_in_app(app)),
        "public_url": pub,
        "internal_url": inn,
        "request_timeout_ms": timeout_ms,
        "allow_new_sessions": True,
        "updated_at": None,
        "updated_by_user_id": None,
        "shared_secret_present": _secret_present_in_app(app),
        "internal_api_key_present": _api_key_present_in_app(app),
    }


def _secret_present_in_app(app: Flask) -> bool:
    return bool((app.config.get("PLAY_SERVICE_SHARED_SECRET") or "").strip())


def _api_key_present_in_app(app: Flask) -> bool:
    return bool((app.config.get("PLAY_SERVICE_INTERNAL_API_KEY") or "").strip())


def _attach_presence_fields(d: dict[str, Any], app: Flask) -> dict[str, Any]:
    out = dict(d)
    out["shared_secret_present"] = _secret_present_in_app(app)
    out["internal_api_key_present"] = _api_key_present_in_app(app)
    return out


def _finalize_desired_record(base: dict[str, Any], *, user_id: int | None) -> dict[str, Any]:
    rec = dict(base)
    rec["updated_at"] = _utc_iso()
    rec["updated_by_user_id"] = user_id
    return rec


def _sync_flask_config_from_desired(app: Flask, desired: dict[str, Any]) -> None:
    """Apply application-level routing (mutable app.config). Secrets stay from env."""
    if desired.get("mode") == MODE_DISABLED or not desired.get("enabled"):
        app.config["PLAY_SERVICE_CONTROL_DISABLED"] = True
        app.config["PLAY_SERVICE_ALLOW_NEW_SESSIONS"] = bool(desired.get("allow_new_sessions", True))
        return
    app.config["PLAY_SERVICE_CONTROL_DISABLED"] = False
    app.config["PLAY_SERVICE_ALLOW_NEW_SESSIONS"] = bool(desired.get("allow_new_sessions", True))
    app.config["PLAY_SERVICE_PUBLIC_URL"] = (desired.get("public_url") or "").strip()
    app.config["PLAY_SERVICE_INTERNAL_URL"] = (desired.get("internal_url") or "").strip()
    app.config["PLAY_SERVICE_REQUEST_TIMEOUT"] = max(
        1, int(desired.get("request_timeout_ms", 30000) // 1000)
    )


def _clear_control_flags_default(app: Flask) -> None:
    app.config["PLAY_SERVICE_CONTROL_DISABLED"] = False
    app.config["PLAY_SERVICE_ALLOW_NEW_SESSIONS"] = True


def _overlay_play_service_urls_from_environment(app: Flask) -> None:
    """Prefer explicit env URLs over persisted play-service control (fixes Docker DNS vs host localhost).

    Operators often ``Apply`` from a browser session with ``internal_url=http://localhost:8001`` (host port).
    Inside the backend container that address is wrong; compose injects ``PLAY_SERVICE_INTERNAL_URL=http://play-service:8000``.
    """
    for key in ("PLAY_SERVICE_PUBLIC_URL", "PLAY_SERVICE_INTERNAL_URL"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            app.config[key] = raw


def _snapshot_play_config(app: Flask) -> dict[str, Any]:
    return {k: app.config.get(k) for k in _PLAY_CFG_KEYS}


def _restore_play_config(app: Flask, snap: dict[str, Any]) -> None:
    for k, v in snap.items():
        app.config[k] = v


def bootstrap_play_service_control(app: Flask) -> None:
    """Load last applied state from site_settings into app.config (after DB init).

    Safe before tables exist: clears control flags on failure (e.g. tests before create_all).
    """
    try:
        with app.app_context():
            doc = _load_raw_document()
            applied = doc.get("applied_desired")
            if isinstance(applied, dict) and doc.get("apply_ok") is True:
                _sync_flask_config_from_desired(app, applied)
            else:
                _clear_control_flags_default(app)
            _overlay_play_service_urls_from_environment(app)
    except Exception:
        _clear_control_flags_default(app)
        _overlay_play_service_urls_from_environment(app)


def validate_play_service_env_pairing(app: Flask) -> None:
    """Fail fast if public URL is set without shared secret (after control bootstrap)."""
    if app.config.get("PLAY_SERVICE_CONTROL_DISABLED"):
        return
    public_url = (app.config.get("PLAY_SERVICE_PUBLIC_URL") or "").strip()
    shared_secret = (app.config.get("PLAY_SERVICE_SHARED_SECRET") or "").strip()
    if public_url and not shared_secret:
        raise ValueError(
            "PLAY_SERVICE_SHARED_SECRET must be configured when "
            "PLAY_SERVICE_PUBLIC_URL is set. Without the shared secret, "
            "play service integration cannot function."
        )


def get_capabilities() -> dict[str, Any]:
    return {
        "supports_disabled_mode": True,
        "supports_local_mode": True,
        "supports_docker_mode": True,
        "supports_remote_mode": True,
        "secrets_source": "environment_only",
        "no_host_orchestration": True,
    }


def _probe_play_http(internal_base: str, headers: dict[str, str], path: str) -> dict[str, Any]:
    base = internal_base.rstrip("/")
    t0 = time.perf_counter()
    try:
        # Bound connect separately so slow DNS / TCP handshakes cannot outlive the pool deadline
        # used by callers (and avoid ThreadPoolExecutor ``result()`` timeouts on constrained hosts).
        _tmo = httpx.Timeout(
            connect=min(UPSTREAM_TIMEOUT_S, 0.5),
            read=UPSTREAM_TIMEOUT_S,
            write=UPSTREAM_TIMEOUT_S,
            pool=UPSTREAM_TIMEOUT_S,
        )
        with httpx.Client(base_url=base, timeout=_tmo, headers=headers) as client:
            r = client.get(path)
        ms = int((time.perf_counter() - t0) * 1000)
        body = r.json() if r.content else {}
        return {
            "http_status": r.status_code,
            "latency_ms": ms,
            "ok": r.status_code == 200,
            "body_status": body.get("status") if isinstance(body, dict) else None,
        }
    except httpx.TimeoutException:
        return {"ok": False, "error": "timeout", "latency_ms": int((time.perf_counter() - t0) * 1000)}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "latency_ms": int((time.perf_counter() - t0) * 1000)}


def run_connectivity_test(app: Flask, desired: dict[str, Any]) -> dict[str, Any]:
    """Bounded test against world-engine surfaces; does not mutate app config."""
    t0 = time.perf_counter()
    if desired.get("mode") == MODE_DISABLED or not desired.get("enabled"):
        return {
            "overall_ok": True,
            "checks": [
                {
                    "id": "disabled",
                    "ok": True,
                    "message": "Disabled mode: no connectivity checks run",
                }
            ],
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        }
    errs: list[str] = []
    if not _valid_http_url(desired.get("public_url", "")):
        errs.append("public_url invalid")
    if not _valid_http_url(desired.get("internal_url", "")):
        errs.append("internal_url invalid")
    if not _secret_present_in_app(app):
        errs.append("PLAY_SERVICE_SHARED_SECRET not set in environment")
    if errs:
        return {
            "overall_ok": False,
            "checks": [{"id": "validation", "ok": False, "message": "; ".join(errs)}],
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        }

    internal = desired["internal_url"].strip().rstrip("/")
    headers: dict[str, str] = {"Accept": "application/json"}
    key = (app.config.get("PLAY_SERVICE_INTERNAL_API_KEY") or "").strip()
    if key:
        headers["X-Play-Service-Key"] = key

    # Sequential probes: each call is bounded by httpx timeouts; avoids executor ``TimeoutError``
    # when worker threads exceed ``fut.result(timeout=…)`` under slow DNS or platform quirks.
    health = _probe_play_http(internal, headers, "/api/health")
    ready = _probe_play_http(internal, headers, "/api/health/ready")

    checks = [
        {"id": "health", "ok": health.get("ok") and health.get("body_status") == "ok", "detail": health},
        {
            "id": "readiness",
            "ok": ready.get("ok") and ready.get("body_status") == "ready",
            "detail": ready,
        },
    ]
    overall = all(c["ok"] for c in checks)
    return {
        "overall_ok": overall,
        "checks": checks,
        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
    }


def build_observed_state(app: Flask) -> dict[str, Any]:
    """Canonical-derived observed snapshot (uses current app.config)."""
    if not has_app_context():
        with app.app_context():
            return build_observed_state(app)

    disabled = bool(app.config.get("PLAY_SERVICE_CONTROL_DISABLED"))
    complete = False
    if not disabled:
        pub = (app.config.get("PLAY_SERVICE_PUBLIC_URL") or "").strip()
        inn = (app.config.get("PLAY_SERVICE_INTERNAL_URL") or "").strip()
        sec = _secret_present_in_app(app)
        complete = bool(pub and inn and sec)

    health = "unknown"
    readiness = "unknown"
    if complete and not disabled:
        desired_probe = {
            "mode": MODE_REMOTE,
            "enabled": True,
            "public_url": app.config.get("PLAY_SERVICE_PUBLIC_URL"),
            "internal_url": app.config.get("PLAY_SERVICE_INTERNAL_URL"),
            "request_timeout_ms": int(float(app.config.get("PLAY_SERVICE_REQUEST_TIMEOUT", 30)) * 1000),
            "allow_new_sessions": True,
        }
        test_result = run_connectivity_test(app, desired_probe)
        for c in test_result.get("checks") or []:
            if c.get("id") == "health":
                health = "ok" if c.get("ok") else "fail"
            if c.get("id") == "readiness":
                readiness = "ready" if c.get("ok") else "not_ready"

    mode_effective = MODE_DISABLED if disabled else MODE_REMOTE
    if not disabled and complete:
        doc = _load_raw_document()
        ad = doc.get("applied_desired")
        if isinstance(ad, dict) and ad.get("mode"):
            mode_effective = ad["mode"]

    return {
        "effective_mode": mode_effective,
        "effective_enabled": not disabled and complete,
        "config_complete": complete,
        "health": health,
        "readiness": readiness,
        "allow_new_sessions_effective": (
            bool(app.config.get("PLAY_SERVICE_ALLOW_NEW_SESSIONS", True)) and not disabled and complete
        ),
        "shared_secret_present": _secret_present_in_app(app),
        "internal_api_key_present": _api_key_present_in_app(app),
    }


def get_control_payload(app: Flask) -> dict[str, Any]:
    with app.app_context():
        doc = _load_raw_document()
        desired = doc.get("desired")
        if not isinstance(desired, dict):
            desired = _desired_from_env_baseline(app)
        else:
            desired = _attach_presence_fields(dict(desired), app)

        observed = build_observed_state(app)
        last_test = doc.get("last_test")
        last_apply = None
        if doc.get("applied_at"):
            last_apply = {
                "ok": doc.get("apply_ok"),
                "at": doc.get("applied_at"),
                "message": doc.get("apply_message"),
                "by_user_id": doc.get("applied_by_user_id"),
            }

        return {
            "desired_state": desired,
            "observed_state": observed,
            "capabilities": get_capabilities(),
            "last_test_result": last_test,
            "last_apply_result": last_apply,
            "generated_at": _utc_iso(),
        }


def save_desired(app: Flask, body: dict[str, Any], *, user_id: int | None) -> dict[str, Any]:
    normalized, errors = validate_desired_payload(body)
    if errors:
        return {"saved": False, "desired_state": None, "validation_errors": errors}
    assert normalized is not None
    rec = _finalize_desired_record(normalized, user_id=user_id)
    rec = _attach_presence_fields(rec, app)
    with app.app_context():
        doc = _load_raw_document()
        doc["desired"] = {
            k: rec[k] for k in rec if k not in ("shared_secret_present", "internal_api_key_present")
        }
        doc["desired"]["updated_at"] = rec["updated_at"]
        doc["desired"]["updated_by_user_id"] = rec["updated_by_user_id"]
        _persist_document(doc)
    return {
        "saved": True,
        "desired_state": rec,
        "validation_errors": [],
    }


def apply_desired(app: Flask, *, user_id: int | None) -> dict[str, Any]:
    with app.app_context():
        doc = _load_raw_document()
        desired = doc.get("desired")
        if not isinstance(desired, dict):
            return {
                "ok": False,
                "applied_state": None,
                "observed_state": build_observed_state(app),
                "result": {"message": "No saved desired state; save before apply."},
                "generated_at": _utc_iso(),
            }
        normalized, errors = validate_desired_payload(desired)
        if errors or normalized is None:
            return {
                "ok": False,
                "applied_state": None,
                "observed_state": build_observed_state(app),
                "result": {"message": "Invalid desired state", "validation_errors": errors},
                "generated_at": _utc_iso(),
            }

        if normalized["mode"] != MODE_DISABLED and normalized["enabled"] and not _secret_present_in_app(app):
            msg = "Cannot apply: PLAY_SERVICE_SHARED_SECRET is not set in the environment."
            doc["apply_ok"] = False
            doc["apply_message"] = msg
            doc["applied_at"] = _utc_iso()
            doc["applied_by_user_id"] = user_id
            _persist_document(doc)
            return {
                "ok": False,
                "applied_state": None,
                "observed_state": build_observed_state(app),
                "result": {"message": msg},
                "generated_at": _utc_iso(),
            }

        snap = dict(normalized)
        cfg_snap = _snapshot_play_config(app)
        try:
            _sync_flask_config_from_desired(app, normalized)
            _overlay_play_service_urls_from_environment(app)
            validate_play_service_env_pairing(app)
            doc["applied_desired"] = snap
            doc["apply_ok"] = True
            doc["apply_message"] = "Applied at application level."
            doc["applied_at"] = _utc_iso()
            doc["applied_by_user_id"] = user_id
            try:
                _persist_document(doc)
            except Exception:
                _restore_play_config(app, cfg_snap)
                raise
        except ValueError as exc:
            _restore_play_config(app, cfg_snap)
            msg = str(exc)
            doc["apply_ok"] = False
            doc["apply_message"] = msg
            doc["applied_at"] = _utc_iso()
            doc["applied_by_user_id"] = user_id
            try:
                _persist_document(doc)
            except Exception:
                pass
            return {
                "ok": False,
                "applied_state": None,
                "observed_state": build_observed_state(app),
                "result": {"message": msg},
                "generated_at": _utc_iso(),
            }
        except Exception:
            _restore_play_config(app, cfg_snap)
            raise

        observed = build_observed_state(app)
        return {
            "ok": True,
            "applied_state": _attach_presence_fields(dict(snap), app),
            "observed_state": observed,
            "result": {"message": doc["apply_message"]},
            "generated_at": _utc_iso(),
        }


def run_test_persist(app: Flask, *, user_id: int | None) -> dict[str, Any]:
    with app.app_context():
        doc = _load_raw_document()
        desired = doc.get("desired")
        if not isinstance(desired, dict):
            base = _desired_from_env_baseline(app)
            desired = {
                "mode": base["mode"],
                "enabled": base["enabled"],
                "public_url": base["public_url"],
                "internal_url": base["internal_url"],
                "request_timeout_ms": base["request_timeout_ms"],
                "allow_new_sessions": base["allow_new_sessions"],
            }
        normalized, errors = validate_desired_payload(desired)
        if errors or normalized is None:
            result = {
                "overall_ok": False,
                "checks": [{"id": "validation", "ok": False, "message": "; ".join(errors)}],
            }
            doc["last_test"] = {"at": _utc_iso(), "ok": False, "result": result, "by_user_id": user_id}
            _persist_document(doc)
            return {"ok": False, "result": result, "generated_at": _utc_iso()}

        if (
            normalized["mode"] != MODE_DISABLED
            and normalized["enabled"]
            and not _secret_present_in_app(app)
        ):
            result = {
                "overall_ok": False,
                "checks": [
                    {
                        "id": "secret",
                        "ok": False,
                        "message": "PLAY_SERVICE_SHARED_SECRET not set in environment",
                    }
                ],
            }
            doc["last_test"] = {"at": _utc_iso(), "ok": False, "result": result, "by_user_id": user_id}
            _persist_document(doc)
            return {"ok": False, "result": result, "generated_at": _utc_iso()}

        result = run_connectivity_test(app, normalized)
        ok = bool(result.get("overall_ok"))
        doc["last_test"] = {"at": _utc_iso(), "ok": ok, "result": result, "by_user_id": user_id}
        _persist_document(doc)
        return {"ok": ok, "result": result, "generated_at": _utc_iso()}
