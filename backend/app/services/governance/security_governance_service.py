"""Security governance settings and observable CSRF, Redis, and storage posture."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any
from urllib.parse import urlparse

from flask import current_app

from app.extensions import db
from app.models.backend.site_setting import SiteSetting


STORAGE_KEY = "security_governance_config"

_DEFAULT_SETTINGS: dict[str, Any] = {
    "schema_version": "security_governance.v1",
    "review_status": "approved",
    "target_session_samesite": "Lax",
    "require_backend_web_csrf": True,
    "require_bearer_for_json_api": True,
    "require_proxy_cookie_stripping": True,
    "require_csrf_regression_tests": True,
    "production_secret_store_required": True,
    "secret_store_mode": "production_secret_store",
    "secret_store_provider": "deployment_managed",
    "secret_rotation_interval_days": 90,
    "secret_store_audit_required": True,
    "secret_store_access_separation_required": True,
    "preserve_docker_up_local_bootstrap": True,
    "redis_hardening_profile": "production_compose",
    "require_production_redis_hardening": True,
    "require_redis_tls": True,
    "require_redis_acl_users": True,
    "require_redis_instance_separation": True,
    "require_redis_no_host_ports": True,
    "require_redis_validation_gate": True,
    "storage_encryption_profile": "mixed_evidence_pack",
    "require_storage_encryption_evidence": True,
    "require_backup_encryption_evidence": True,
    "require_storage_key_custody_evidence": True,
    "require_storage_restore_test_evidence": True,
    "storage_encryption_evidence": {},
    "operator_notes": "",
}

_REVIEW_STATUS_VALUES = {"draft", "approved", "needs_review"}
_SAMESITE_VALUES = {"Lax", "Strict"}
_SECRET_STORE_MODE_VALUES = {
    "local_env_bootstrap",
    "external_env_injection",
    "production_secret_store",
}
_SECRET_STORE_PROVIDER_VALUES = {
    "deployment_managed",
    "vault",
    "aws_secrets_manager",
    "gcp_secret_manager",
    "azure_key_vault",
    "1password",
    "doppler",
    "other",
}
_REDIS_HARDENING_PROFILE_VALUES = {
    "local_development",
    "production_compose",
    "managed_service",
}
_STORAGE_ENCRYPTION_PROFILE_VALUES = {
    "local_development",
    "self_hosted_encrypted_volumes",
    "managed_encrypted_services",
    "mixed_evidence_pack",
}
_STORAGE_EVIDENCE_STATUS_VALUES = {
    "not_provided",
    "documented",
    "verified",
    "not_applicable",
}
_STORAGE_CONTROL_TYPE_VALUES = {
    "",
    "host_full_disk",
    "docker_volume_driver",
    "managed_service_kms",
    "database_tde",
    "sqlcipher",
    "aead_file_encryption",
    "server_side_encryption",
    "client_side_backup_encryption",
    "non_persistent",
    "local_dev_only",
    "other",
}
_STORAGE_KEYLESS_CONTROL_TYPES = {"non_persistent", "local_dev_only"}
_STORAGE_EVIDENCE_FIELDS = {
    "status",
    "control_type",
    "evidence_ref",
    "key_ref",
    "last_verified_at",
    "restore_test_ref",
    "notes",
}
_STORAGE_EVIDENCE_TEXT_LIMITS = {
    "control_type": 80,
    "evidence_ref": 240,
    "key_ref": 180,
    "last_verified_at": 80,
    "restore_test_ref": 240,
    "notes": 500,
}
_STORAGE_SURFACES: list[dict[str, Any]] = [
    {
        "id": "backend_sqlite",
        "label": "Backend SQLite database",
        "category": "database",
        "persistence": "backend/instance/wos.db bind-mounted through docker-compose.yml",
    },
    {
        "id": "backend_redis_aof",
        "label": "Backend governance Redis AOF",
        "category": "redis",
        "persistence": "redis-data:/data with appendonly yes",
    },
    {
        "id": "world_engine_json_run_store",
        "label": "World-engine JSON run store",
        "category": "runtime_store",
        "persistence": "RUN_STORE_BACKEND=json local files or RUN_STORE_BACKEND=json_aead AES-256-GCM *.json.enc files",
    },
    {
        "id": "world_engine_sqlalchemy_run_store",
        "label": "World-engine SQLAlchemy run store",
        "category": "runtime_store",
        "persistence": "RUN_STORE_BACKEND=sqlalchemy payload_json rows on an encrypted managed database or encrypted volume-backed database",
    },
    {
        "id": "langfuse_postgres",
        "label": "Langfuse Postgres volume",
        "category": "database",
        "persistence": "langfuse-postgres-data",
    },
    {
        "id": "langfuse_clickhouse",
        "label": "Langfuse ClickHouse volumes",
        "category": "database",
        "persistence": "langfuse-clickhouse-data and langfuse-clickhouse-logs",
    },
    {
        "id": "langfuse_minio",
        "label": "Langfuse MinIO object volume",
        "category": "object_storage",
        "persistence": "langfuse-minio-data",
    },
    {
        "id": "langfuse_redis",
        "label": "Langfuse Redis volume",
        "category": "redis",
        "persistence": "langfuse-redis-data",
    },
    {
        "id": "backups_snapshots",
        "label": "Backups and snapshots",
        "category": "backup",
        "persistence": "database, Redis, object-store, and volume backup artifacts",
        "restore_test_required": True,
    },
]
_BOOL_FIELDS = {
    "preserve_docker_up_local_bootstrap",
    "production_secret_store_required",
    "require_backend_web_csrf",
    "require_bearer_for_json_api",
    "require_proxy_cookie_stripping",
    "require_csrf_regression_tests",
    "require_production_redis_hardening",
    "require_redis_tls",
    "require_redis_acl_users",
    "require_redis_instance_separation",
    "require_redis_no_host_ports",
    "require_redis_validation_gate",
    "require_backup_encryption_evidence",
    "require_storage_encryption_evidence",
    "require_storage_key_custody_evidence",
    "require_storage_restore_test_evidence",
    "secret_store_access_separation_required",
    "secret_store_audit_required",
}


def _load_settings() -> dict[str, Any]:
    row = db.session.get(SiteSetting, STORAGE_KEY)
    if row and row.value:
        try:
            raw = json.loads(row.value)
            if isinstance(raw, dict):
                settings = deepcopy(_DEFAULT_SETTINGS)
                settings.update({k: v for k, v in raw.items() if k in settings})
                return _normalize_settings(settings)
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    return _normalize_settings(deepcopy(_DEFAULT_SETTINGS))


def _save_settings(settings: dict[str, Any]) -> None:
    row = db.session.get(SiteSetting, STORAGE_KEY)
    if row is None:
        row = SiteSetting(key=STORAGE_KEY)
        db.session.add(row)
    row.value = json.dumps(settings, sort_keys=True)
    db.session.commit()


def _normalize_settings(payload: dict[str, Any]) -> dict[str, Any]:
    settings = deepcopy(_DEFAULT_SETTINGS)
    settings.update({k: v for k, v in payload.items() if k in settings})

    if settings["review_status"] not in _REVIEW_STATUS_VALUES:
        raise ValueError("review_status must be draft, approved, or needs_review")
    if settings["target_session_samesite"] not in _SAMESITE_VALUES:
        raise ValueError("target_session_samesite must be Lax or Strict")
    if settings["secret_store_mode"] not in _SECRET_STORE_MODE_VALUES:
        raise ValueError("secret_store_mode must be local_env_bootstrap, external_env_injection, or production_secret_store")
    if settings["secret_store_provider"] not in _SECRET_STORE_PROVIDER_VALUES:
        raise ValueError("secret_store_provider is not supported")
    if settings["redis_hardening_profile"] not in _REDIS_HARDENING_PROFILE_VALUES:
        raise ValueError(
            "redis_hardening_profile must be local_development, production_compose, or managed_service"
        )
    if settings["storage_encryption_profile"] not in _STORAGE_ENCRYPTION_PROFILE_VALUES:
        raise ValueError(
            "storage_encryption_profile must be local_development, self_hosted_encrypted_volumes, "
            "managed_encrypted_services, or mixed_evidence_pack"
        )

    for key in _BOOL_FIELDS:
        settings[key] = bool(settings[key])
    settings["storage_encryption_evidence"] = _normalize_storage_evidence(
        settings.get("storage_encryption_evidence")
    )

    try:
        rotation_days = int(settings.get("secret_rotation_interval_days") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("secret_rotation_interval_days must be an integer") from exc
    if rotation_days < 1 or rotation_days > 365:
        raise ValueError("secret_rotation_interval_days must be between 1 and 365")
    settings["secret_rotation_interval_days"] = rotation_days

    notes = str(settings.get("operator_notes") or "").strip()
    settings["operator_notes"] = notes[:800]
    settings["schema_version"] = _DEFAULT_SETTINGS["schema_version"]
    return settings


def _clean_text(value: Any, max_length: int) -> str:
    return str(value or "").strip()[:max_length]


def _empty_storage_evidence() -> dict[str, str]:
    return {
        "status": "not_provided",
        "control_type": "",
        "evidence_ref": "",
        "key_ref": "",
        "last_verified_at": "",
        "restore_test_ref": "",
        "notes": "",
    }


def _normalize_storage_evidence(raw: Any) -> dict[str, dict[str, str]]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("storage_encryption_evidence must be an object")

    known_ids = {surface["id"] for surface in _STORAGE_SURFACES}
    unknown = sorted(set(raw) - known_ids)
    if unknown:
        raise ValueError("Unknown storage encryption evidence surface(s): " + ", ".join(unknown))

    normalized: dict[str, dict[str, str]] = {}
    for surface in _STORAGE_SURFACES:
        surface_id = surface["id"]
        item = raw.get(surface_id) or {}
        if not isinstance(item, dict):
            raise ValueError(f"storage_encryption_evidence.{surface_id} must be an object")
        unknown_item_fields = sorted(set(item) - _STORAGE_EVIDENCE_FIELDS)
        if unknown_item_fields:
            raise ValueError(
                f"Unknown storage_encryption_evidence.{surface_id} field(s): "
                + ", ".join(unknown_item_fields)
            )

        evidence = _empty_storage_evidence()
        evidence.update({k: v for k, v in item.items() if k in evidence})
        status = _clean_text(evidence.get("status"), 40) or "not_provided"
        if status not in _STORAGE_EVIDENCE_STATUS_VALUES:
            raise ValueError(
                f"storage_encryption_evidence.{surface_id}.status must be "
                "not_provided, documented, verified, or not_applicable"
            )
        control_type = _clean_text(
            evidence.get("control_type"),
            _STORAGE_EVIDENCE_TEXT_LIMITS["control_type"],
        )
        if control_type not in _STORAGE_CONTROL_TYPE_VALUES:
            raise ValueError(f"storage_encryption_evidence.{surface_id}.control_type is not supported")

        evidence["status"] = status
        evidence["control_type"] = control_type
        for key, limit in _STORAGE_EVIDENCE_TEXT_LIMITS.items():
            if key != "control_type":
                evidence[key] = _clean_text(evidence.get(key), limit)
        normalized[surface_id] = evidence

    return normalized


def _effective_posture() -> dict[str, Any]:
    cfg = current_app.config
    return {
        "backend_session_cookie": {
            "secure": bool(cfg.get("SESSION_COOKIE_SECURE")),
            "httponly": bool(cfg.get("SESSION_COOKIE_HTTPONLY")),
            "samesite": cfg.get("SESSION_COOKIE_SAMESITE") or None,
        },
        "backend_csrf": {
            "flask_wtf_enabled": bool(cfg.get("WTF_CSRF_ENABLED", True)),
            "api_v1_exempt": True,
            "web_routes_protected_when_enabled": True,
        },
        "json_api_auth": {
            "expected_credential": "Authorization: Bearer",
            "cookie_auth_allowed": False,
        },
        "same_origin_proxies": {
            "admin_proxy_cookie_forwarding_allowed": False,
            "frontend_backend_calls_forward_cookies": False,
        },
    }


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _redis_url_parts(url: str | None) -> dict[str, Any]:
    raw = (url or "").strip()
    if not raw:
        return {
            "configured": False,
            "scheme": None,
            "host": None,
            "username_present": False,
            "password_present": False,
            "uses_tls": False,
        }
    parsed = urlparse(raw)
    return {
        "configured": True,
        "scheme": parsed.scheme or None,
        "host": parsed.hostname or None,
        "username_present": bool(parsed.username),
        "password_present": bool(parsed.password),
        "uses_tls": parsed.scheme == "rediss",
    }


def _redis_governance_posture(settings: dict[str, Any]) -> dict[str, Any]:
    backend_redis_url = (
        current_app.config.get("REDIS_URL")
        or os.environ.get("REDIS_URL")
        or ""
    )
    app_redis_url = os.environ.get("APP_REDIS_URL") or backend_redis_url
    langfuse_redis_url = os.environ.get("LANGFUSE_REDIS_CONNECTION_STRING") or ""

    backend = _redis_url_parts(backend_redis_url)
    app = _redis_url_parts(app_redis_url)
    langfuse = _redis_url_parts(langfuse_redis_url)
    app_host = app["host"] or backend["host"]
    langfuse_host = (
        langfuse["host"]
        or os.environ.get("LANGFUSE_REDIS_HOST")
        or os.environ.get("REDIS_HOST")
    )

    tls_ready = (
        app["uses_tls"]
        and langfuse["uses_tls"]
        and _env_truthy("APP_REDIS_TLS_ENABLED")
        and _env_truthy("LANGFUSE_REDIS_TLS_ENABLED")
        and _env_truthy("LANGFUSE_REDIS_TLS_REJECT_UNAUTHORIZED")
    )
    acl_ready = (
        bool(os.environ.get("APP_REDIS_USERNAME") or app["username_present"])
        and bool(os.environ.get("LANGFUSE_REDIS_USERNAME") or langfuse["username_present"])
        and bool(os.environ.get("APP_REDIS_PASSWORD") or app["password_present"])
        and bool(os.environ.get("LANGFUSE_REDIS_PASSWORD") or langfuse["password_present"])
    )
    separated = bool(app_host and langfuse_host and app_host != langfuse_host)

    checks = [
        {
            "id": "redis_hardening_profile",
            "label": "Production Redis hardening profile is selected",
            "required": bool(settings["require_production_redis_hardening"]),
            "pass": settings["redis_hardening_profile"] != "local_development",
            "detail": settings["redis_hardening_profile"],
        },
        {
            "id": "app_redis_rediss",
            "label": "App Redis uses rediss://",
            "required": bool(settings["require_redis_tls"]),
            "pass": app["uses_tls"],
            "detail": app["scheme"] or "not configured",
        },
        {
            "id": "langfuse_redis_rediss",
            "label": "Langfuse Redis uses rediss://",
            "required": bool(settings["require_redis_tls"]),
            "pass": langfuse["uses_tls"],
            "detail": langfuse["scheme"] or "not configured",
        },
        {
            "id": "redis_acl_users",
            "label": "App and Langfuse Redis have named ACL credentials",
            "required": bool(settings["require_redis_acl_users"]),
            "pass": acl_ready,
            "detail": "APP_REDIS_USERNAME / LANGFUSE_REDIS_USERNAME",
        },
        {
            "id": "redis_instance_separation",
            "label": "App Redis and Langfuse Redis use separate hosts",
            "required": bool(settings["require_redis_instance_separation"]),
            "pass": separated,
            "detail": f"{app_host or '-'} vs {langfuse_host or '-'}",
        },
        {
            "id": "redis_no_host_ports",
            "label": "Production Redis containers do not publish host ports",
            "required": bool(settings["require_redis_no_host_ports"]),
            "pass": True,
            "detail": "docker-compose.redis-production.yml keeps Redis internal-only",
        },
        {
            "id": "redis_validation_gate",
            "label": "docker-up validation command is documented",
            "required": bool(settings["require_redis_validation_gate"]),
            "pass": True,
            "detail": "python docker-up.py validate-production-redis",
        },
    ]
    status = "ready" if all((not row["required"]) or row["pass"] for row in checks) else "needs_attention"
    if not settings["require_production_redis_hardening"]:
        status = "local_allowed"

    return {
        "profile": settings["redis_hardening_profile"],
        "status": status,
        "editable_from_admin": True,
        "compose_override": "docker-compose.redis-production.yml",
        "generated_asset_root": ".docker/redis-production/",
        "commands": [
            "python docker-up.py init-production-redis",
            "python docker-up.py validate-production-redis",
            "python docker-up.py --production-redis up",
        ],
        "acl_files": [
            ".docker/redis-production/app-users.acl",
            ".docker/redis-production/langfuse-users.acl",
        ],
        "cert_dirs": [
            ".docker/redis-production/certs/app",
            ".docker/redis-production/certs/langfuse",
        ],
        "observed": {
            "backend_redis_url": backend,
            "app_redis_url": app,
            "langfuse_redis_connection": langfuse,
            "app_redis_tls_enabled": _env_truthy("APP_REDIS_TLS_ENABLED"),
            "langfuse_redis_tls_enabled": _env_truthy("LANGFUSE_REDIS_TLS_ENABLED"),
            "langfuse_redis_tls_reject_unauthorized": _env_truthy("LANGFUSE_REDIS_TLS_REJECT_UNAUTHORIZED"),
            "app_redis_username_present": bool(os.environ.get("APP_REDIS_USERNAME") or app["username_present"]),
            "langfuse_redis_username_present": bool(os.environ.get("LANGFUSE_REDIS_USERNAME") or langfuse["username_present"]),
            "separate_hosts": separated,
            "tls_ready": tls_ready,
            "acl_ready": acl_ready,
            "no_host_ports_expected": bool(settings["require_redis_no_host_ports"]),
        },
        "checks": checks,
        "note": (
            "Admin governance stores policy and review posture. "
            "docker-up.py materializes .env secrets, ACL files, and TLS certificates on the host."
        ),
    }


def _storage_surface_required(surface: dict[str, Any], settings: dict[str, Any]) -> bool:
    if surface["category"] == "backup":
        return bool(settings["require_backup_encryption_evidence"])
    return bool(settings["require_storage_encryption_evidence"])


def _storage_surface_posture(
    *,
    surface: dict[str, Any],
    evidence: dict[str, str],
    settings: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    required = _storage_surface_required(surface, settings)
    status = evidence["status"]
    control_type = evidence["control_type"]
    has_evidence_ref = bool(evidence["evidence_ref"])
    active_encryption_status = status in {"documented", "verified"}
    not_applicable_status = status == "not_applicable"
    acceptable_status = active_encryption_status or not_applicable_status
    acceptable_control = bool(control_type)
    if active_encryption_status and control_type in _STORAGE_KEYLESS_CONTROL_TYPES:
        acceptable_control = False
    if not_applicable_status and control_type not in {"non_persistent", "local_dev_only", "other"}:
        acceptable_control = False

    evidence_complete = acceptable_status and acceptable_control and has_evidence_ref
    key_required = (
        required
        and bool(settings["require_storage_key_custody_evidence"])
        and active_encryption_status
        and control_type not in _STORAGE_KEYLESS_CONTROL_TYPES
    )
    key_complete = bool(evidence["key_ref"])
    restore_required = (
        required
        and bool(surface.get("restore_test_required"))
        and bool(settings["require_storage_restore_test_evidence"])
    )
    restore_complete = bool(evidence["restore_test_ref"])

    checks = [
        {
            "id": f"storage_evidence_{surface['id']}",
            "surface_id": surface["id"],
            "label": f"{surface['label']} has storage encryption evidence",
            "required": required,
            "pass": evidence_complete,
            "detail": evidence["evidence_ref"] or "missing evidence_ref",
        },
        {
            "id": f"storage_key_custody_{surface['id']}",
            "surface_id": surface["id"],
            "label": f"{surface['label']} has key custody reference",
            "required": key_required,
            "pass": (not key_required) or key_complete,
            "detail": evidence["key_ref"] or "missing key_ref",
        },
        {
            "id": f"storage_restore_test_{surface['id']}",
            "surface_id": surface["id"],
            "label": f"{surface['label']} has restore-test evidence",
            "required": restore_required,
            "pass": (not restore_required) or restore_complete,
            "detail": evidence["restore_test_ref"] or "missing restore_test_ref",
        },
    ]
    surface_pass = all((not check["required"]) or check["pass"] for check in checks)
    missing = [check["id"] for check in checks if check["required"] and not check["pass"]]
    return (
        {
            "id": surface["id"],
            "label": surface["label"],
            "category": surface["category"],
            "persistence": surface["persistence"],
            "required": required,
            "status": status,
            "control_type": control_type or None,
            "evidence_ref": evidence["evidence_ref"] or None,
            "key_ref": evidence["key_ref"] or None,
            "last_verified_at": evidence["last_verified_at"] or None,
            "restore_test_ref": evidence["restore_test_ref"] or None,
            "notes": evidence["notes"] or None,
            "pass": surface_pass,
            "missing": missing,
        },
        checks,
    )


def _storage_encryption_governance(settings: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = [
        {
            "id": "storage_encryption_profile",
            "label": "Production storage encryption profile is selected",
            "required": bool(
                settings["require_storage_encryption_evidence"]
                or settings["require_backup_encryption_evidence"]
            ),
            "pass": settings["storage_encryption_profile"] != "local_development",
            "detail": settings["storage_encryption_profile"],
        }
    ]
    surfaces: list[dict[str, Any]] = []
    evidence_pack = _normalize_storage_evidence(settings.get("storage_encryption_evidence"))
    for surface in _STORAGE_SURFACES:
        surface_row, surface_checks = _storage_surface_posture(
            surface=surface,
            evidence=evidence_pack[surface["id"]],
            settings=settings,
        )
        surfaces.append(surface_row)
        checks.extend(surface_checks)

    failed_required = [check for check in checks if check["required"] and not check["pass"]]
    if not settings["require_storage_encryption_evidence"] and not settings["require_backup_encryption_evidence"]:
        status = "local_allowed"
    elif not failed_required:
        status = "ready"
    else:
        status = "needs_attention"

    return {
        "profile": settings["storage_encryption_profile"],
        "status": status,
        "editable_from_admin": True,
        "evidence_doc": "docs/security/AT_REST_ENCRYPTION.md",
        "adr": "docs/ADR/adr-0051-storage-layer-encryption-governance.md",
        "api_endpoint": "/api/v1/admin/security/governance",
        "diagnosis_check": "storage_layer_encryption",
        "evidence_fields": [
            "status",
            "control_type",
            "evidence_ref",
            "key_ref",
            "last_verified_at",
            "restore_test_ref",
            "notes",
        ],
        "allowed_statuses": sorted(_STORAGE_EVIDENCE_STATUS_VALUES),
        "allowed_control_types": sorted(_STORAGE_CONTROL_TYPE_VALUES - {""}),
        "surfaces": surfaces,
        "checks": checks,
        "coverage": {
            "surface_count": len(surfaces),
            "required_surface_count": sum(1 for surface in surfaces if surface["required"]),
            "complete_surface_count": sum(1 for surface in surfaces if surface["pass"]),
            "evidenced_surface_count": sum(1 for surface in surfaces if surface["status"] != "not_provided"),
            "verified_surface_count": sum(1 for surface in surfaces if surface["status"] == "verified"),
            "not_applicable_surface_count": sum(1 for surface in surfaces if surface["status"] == "not_applicable"),
            "required_check_count": sum(1 for check in checks if check["required"]),
            "failed_required_check_count": len(failed_required),
        },
        "note": (
            "This service stores operator evidence and validates coverage. "
            "It does not encrypt host disks or Docker volumes by itself."
        ),
    }


def _csrf_matrix_rows() -> list[dict[str, str]]:
    return [
        {
            "flow": "backend_web",
            "credential": "backend session cookie",
            "mutation": "browser form POST routes",
            "policy": "Flask-WTF CSRF when WTF_CSRF_ENABLED=True",
            "test": "backend/tests/test_csrf_protection.py",
        },
        {
            "flow": "backend_api_v1",
            "credential": "Authorization: Bearer",
            "mutation": "JSON POST/PUT/PATCH/DELETE",
            "policy": "CSRF-exempt by design; route auth and roles apply",
            "test": "backend/tests/test_csrf_protection.py",
        },
        {
            "flow": "player_frontend",
            "credential": "frontend session cookie -> server-side bearer lookup",
            "mutation": "auth, reset, play start, play execute",
            "policy": "same-origin form posts; backend calls use bearer without cookies",
            "test": "frontend/tests/test_csrf_matrix.py",
        },
        {
            "flow": "admin_proxy",
            "credential": "bearer header; admin cookie stays local",
            "mutation": "/_proxy/api/* mutating requests",
            "policy": "allowlist proxy strips Cookie, Set-Cookie, Host",
            "test": "administration-tool/tests/test_proxy_contract.py",
        },
    ]


def _editable_fields() -> list[dict[str, Any]]:
    return [
        {
            "name": "review_status",
            "kind": "select",
            "choices": sorted(_REVIEW_STATUS_VALUES),
            "description": "Operator review state for this security governance policy.",
        },
        {
            "name": "target_session_samesite",
            "kind": "select",
            "choices": sorted(_SAMESITE_VALUES),
            "description": "Desired SameSite posture for Flask session cookies.",
        },
        {
            "name": "secret_store_mode",
            "kind": "select",
            "choices": sorted(_SECRET_STORE_MODE_VALUES),
            "description": "Desired production secret-source boundary.",
        },
        {
            "name": "secret_store_provider",
            "kind": "select",
            "choices": sorted(_SECRET_STORE_PROVIDER_VALUES),
            "description": "Expected production secret-store provider or platform owner.",
        },
        {
            "name": "secret_rotation_interval_days",
            "kind": "integer",
            "min": 1,
            "max": 365,
            "description": "Maximum planned rotation interval for production secrets.",
        },
        {
            "name": "redis_hardening_profile",
            "kind": "select",
            "choices": sorted(_REDIS_HARDENING_PROFILE_VALUES),
            "description": "Operator-selected Redis security posture.",
        },
        {
            "name": "storage_encryption_profile",
            "kind": "select",
            "choices": sorted(_STORAGE_ENCRYPTION_PROFILE_VALUES),
            "description": "Operator-selected storage-layer encryption evidence posture.",
        },
        {
            "name": "storage_encryption_evidence",
            "kind": "object",
            "surface_ids": [surface["id"] for surface in _STORAGE_SURFACES],
            "description": "Evidence pack for persisted storage surfaces.",
        },
        *[
            {
                "name": key,
                "kind": "boolean",
                "description": key.replace("_", " "),
            }
            for key in sorted(_BOOL_FIELDS)
        ],
        {
            "name": "operator_notes",
            "kind": "text",
            "max_length": 800,
            "description": "Short audit note for operators.",
        },
    ]


def get_security_governance() -> dict[str, Any]:
    settings = _load_settings()
    effective = _effective_posture()
    redis_governance = _redis_governance_posture(settings)
    storage_encryption_governance = _storage_encryption_governance(settings)
    warnings: list[str] = []
    actual_samesite = effective["backend_session_cookie"]["samesite"]
    if actual_samesite != settings["target_session_samesite"]:
        warnings.append(
            "target_session_samesite differs from backend SESSION_COOKIE_SAMESITE"
        )
    if settings["require_backend_web_csrf"] and not effective["backend_csrf"]["web_routes_protected_when_enabled"]:
        warnings.append("backend web CSRF protection is not available")
    if settings["production_secret_store_required"] and settings["secret_store_mode"] != "production_secret_store":
        warnings.append("production secret store is required but secret_store_mode is not production_secret_store")
    if not settings["preserve_docker_up_local_bootstrap"]:
        warnings.append("local docker-up.py bootstrap preservation is disabled")
    if settings["secret_rotation_interval_days"] > 180:
        warnings.append("secret rotation interval is longer than 180 days")
    if not settings["secret_store_audit_required"]:
        warnings.append("production secret-store audit requirement is disabled")
    if not settings["secret_store_access_separation_required"]:
        warnings.append("production secret-store access separation requirement is disabled")
    for check in redis_governance["checks"]:
        if check["required"] and not check["pass"]:
            warnings.append(f"Redis governance: {check['label']} is not satisfied ({check['detail']}).")
    for check in storage_encryption_governance["checks"]:
        if check["required"] and not check["pass"]:
            warnings.append(
                f"Storage encryption governance: {check['label']} is not satisfied ({check['detail']})."
            )

    return {
        "contract": "security_governance.v1",
        "settings": settings,
        "effective_posture": effective,
        "redis_governance": redis_governance,
        "storage_encryption_governance": storage_encryption_governance,
        "secret_management_governance": {
            "local_bootstrap": {
                "source": "repo-root .env",
                "preserved": settings["preserve_docker_up_local_bootstrap"],
                "commands": [
                    "python docker-up.py init-env",
                    "python docker-up.py up",
                    "python docker-up.py build",
                    "python docker-up.py restart",
                ],
                "rule": "local Compose must not require Vault, KMS, cloud login, or production secret-store access",
            },
            "production": {
                "required": settings["production_secret_store_required"],
                "mode": settings["secret_store_mode"],
                "provider": settings["secret_store_provider"],
                "rotation_interval_days": settings["secret_rotation_interval_days"],
                "audit_required": settings["secret_store_audit_required"],
                "access_separation_required": settings["secret_store_access_separation_required"],
            },
        },
        "csrf_matrix": _csrf_matrix_rows(),
        "editable_fields": _editable_fields(),
        "non_editable_boundaries": [
            "api_v1 CSRF exemption is code-owned in factory_app.py",
            "proxy cookie stripping is code-owned in administration-tool/route_registration_proxy.py",
            "Bearer-token API auth is owned by backend auth decorators and clients",
            "docker-up.py local .env bootstrap must remain independent from production secret stores",
            "Redis password/TLS/ACL materialization is host-owned by docker-up.py, not executed from the admin browser",
            "Storage-layer encryption evidence is operator-owned; the admin UI records evidence but does not encrypt host disks, Docker volumes, managed services, or backups",
        ],
        "warnings": warnings,
    }


def update_security_governance(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object")
    current = _load_settings()
    allowed = set(_DEFAULT_SETTINGS)
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError("Unknown security governance field(s): " + ", ".join(unknown))
    current.update(payload)
    settings = _normalize_settings(current)
    _save_settings(settings)
    return get_security_governance()
