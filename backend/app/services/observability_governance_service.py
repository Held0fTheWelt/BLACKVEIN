"""Service layer for observability configuration and credential management."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.extensions import db
from app.governance.errors import governance_error
from app.models.governance_core import ObservabilityConfig, ObservabilityCredential
from app.services.governance_secret_crypto_service import decrypt_secret, encrypt_secret
from app.utils.time_utils import utc_now


def _default_observability_config() -> dict:
    """Return default Langfuse configuration."""
    return {
        "service_id": "langfuse",
        "service_type": "langfuse",
        "display_name": "Langfuse",
        "is_enabled": False,
        "base_url": "https://cloud.langfuse.com",
        "environment": "development",
        "release": "unknown",
        "sample_rate": 1.0,
        "capture_prompts": True,
        "capture_outputs": True,
        "capture_retrieval": False,
        "redaction_mode": "strict",
        "credential_configured": False,
        "credential_fingerprint": None,
        "health_status": "unknown",
        "last_tested_at": None,
    }


def get_observability_config() -> dict:
    """Get current Langfuse configuration (non-secret values only)."""
    config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
    if not config:
        return _default_observability_config()

    return {
        "service_id": config.service_id,
        "service_type": config.service_type,
        "display_name": config.display_name,
        "is_enabled": config.is_enabled,
        "base_url": config.base_url,
        "environment": config.environment,
        "release": config.release,
        "sample_rate": config.sample_rate,
        "capture_prompts": config.capture_prompts,
        "capture_outputs": config.capture_outputs,
        "capture_retrieval": config.capture_retrieval,
        "redaction_mode": config.redaction_mode,
        "credential_configured": config.credential_configured,
        "credential_fingerprint": config.credential_fingerprint,
        "health_status": config.health_status,
        "last_tested_at": config.last_tested_at.isoformat() if config.last_tested_at else None,
    }


def update_observability_config(updates: dict, actor: str) -> dict:
    """Update Langfuse public configuration."""
    config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
    if not config:
        config = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
        )
        db.session.add(config)

    # Validation
    if "base_url" in updates and updates["base_url"]:
        if not updates["base_url"].startswith(("http://", "https://")):
            raise governance_error(
                "invalid_url",
                "base_url must start with http:// or https://",
                400,
                {},
            )

    if "sample_rate" in updates:
        try:
            sr = float(updates["sample_rate"])
            if not (0.0 <= sr <= 1.0):
                raise ValueError()
        except (TypeError, ValueError):
            raise governance_error(
                "invalid_sample_rate",
                "sample_rate must be a number between 0.0 and 1.0",
                400,
                {},
            )

    if "environment" in updates:
        if updates["environment"] not in ["development", "staging", "production"]:
            raise governance_error(
                "invalid_environment",
                "environment must be development, staging, or production",
                400,
                {},
            )

    if "redaction_mode" in updates:
        if updates["redaction_mode"] not in ["strict", "relaxed", "none"]:
            raise governance_error(
                "invalid_redaction_mode",
                "redaction_mode must be strict, relaxed, or none",
                400,
                {},
            )

    # Update fields
    for key in [
        "is_enabled",
        "base_url",
        "environment",
        "release",
        "sample_rate",
        "capture_prompts",
        "capture_outputs",
        "capture_retrieval",
        "redaction_mode",
    ]:
        if key in updates:
            setattr(config, key, updates[key])

    config.updated_at = utc_now()
    db.session.commit()

    _audit(
        "observability_config_updated",
        "observability",
        "langfuse",
        actor,
        "Observability config updated",
        updates,
    )

    return {"updated": True, "service_id": "langfuse", "requires_restart": False}


def write_observability_credential(
    public_key: str = None,
    secret_key: str = None,
    actor: str = "system",
) -> dict:
    """Write/rotate Langfuse credentials."""
    config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
    if not config:
        config = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
        )
        db.session.add(config)

    result = {}

    # Handle public_key
    if public_key is not None:
        if not public_key.strip():
            raise governance_error(
                "invalid_public_key",
                "public_key cannot be empty",
                400,
                {},
            )

        # Deactivate old public_key credentials
        old_pk = ObservabilityCredential.query.filter_by(
            service_id="langfuse",
            secret_name="public_key",
            is_active=True,
        ).first()
        if old_pk:
            old_pk.is_active = False

        # Create new public_key credential
        record = encrypt_secret(public_key)
        cred = ObservabilityCredential(
            credential_id=f"obs_cred_{uuid4().hex}",
            service_id="langfuse",
            secret_name="public_key",
            encrypted_secret=record.encrypted_secret,
            encrypted_dek=record.encrypted_dek,
            secret_nonce=record.secret_nonce,
            dek_nonce=record.dek_nonce,
            dek_algorithm=record.dek_algorithm,
            secret_fingerprint=record.secret_fingerprint,
            is_active=True,
            rotated_at=utc_now(),
        )
        db.session.add(cred)
        result["public_key_fingerprint"] = record.secret_fingerprint

    # Handle secret_key
    if secret_key is not None:
        if not secret_key.strip():
            raise governance_error(
                "invalid_secret_key",
                "secret_key cannot be empty",
                400,
                {},
            )

        # Deactivate old secret_key credentials
        old_sk = ObservabilityCredential.query.filter_by(
            service_id="langfuse",
            secret_name="secret_key",
            is_active=True,
        ).first()
        if old_sk:
            old_sk.is_active = False

        # Create new secret_key credential
        record = encrypt_secret(secret_key)
        cred = ObservabilityCredential(
            credential_id=f"obs_cred_{uuid4().hex}",
            service_id="langfuse",
            secret_name="secret_key",
            encrypted_secret=record.encrypted_secret,
            encrypted_dek=record.encrypted_dek,
            secret_nonce=record.secret_nonce,
            dek_nonce=record.dek_nonce,
            dek_algorithm=record.dek_algorithm,
            secret_fingerprint=record.secret_fingerprint,
            is_active=True,
            rotated_at=utc_now(),
        )
        db.session.add(cred)
        result["secret_key_fingerprint"] = record.secret_fingerprint

    # Mark credential as configured if both keys present
    if result:
        # Only mark configured if we have at least a secret_key
        if secret_key or (
            secret_key is None
            and ObservabilityCredential.query.filter_by(
                service_id="langfuse", secret_name="secret_key", is_active=True
            ).first()
        ):
            config.credential_configured = True
        config.updated_at = utc_now()

    db.session.commit()
    result["credential_written"] = True
    result["rotated_at"] = utc_now().isoformat()

    _audit(
        "observability_credential_written",
        "observability",
        "langfuse",
        actor,
        "Observability credential rotated",
        result,
    )

    return result


def get_observability_credential_for_runtime(
    secret_name: str = "secret_key",
) -> str | None:
    """Decrypt and return Langfuse credential for runtime use."""
    cred = ObservabilityCredential.query.filter_by(
        service_id="langfuse",
        secret_name=secret_name,
        is_active=True,
    ).first()

    if not cred:
        return None

    try:
        decrypted = decrypt_secret(
            encrypted_secret=cred.encrypted_secret,
            encrypted_dek=cred.encrypted_dek,
            secret_nonce=cred.secret_nonce,
            dek_nonce=cred.dek_nonce,
        )
        return (
            decrypted.get(secret_name)
            if isinstance(decrypted, dict)
            else str(decrypted)
        )
    except Exception:
        return None


def test_observability_connection(actor: str = "system") -> dict:
    """Test Langfuse connection health."""
    config = get_observability_config()

    if not config["credential_configured"]:
        raise governance_error(
            "credential_required",
            "Langfuse credential required before testing",
            400,
            {},
        )

    if not config["is_enabled"]:
        raise governance_error(
            "not_enabled",
            "Langfuse is not enabled",
            400,
            {},
        )

    # Test connection
    status = "healthy"
    message = "Successfully connected to Langfuse"

    try:
        from app.observability.langfuse_adapter import LangfuseAdapter

        public_key = get_observability_credential_for_runtime("public_key")
        secret_key = get_observability_credential_for_runtime("secret_key")

        if not secret_key:
            raise Exception("Secret key not configured")

        adapter = LangfuseAdapter(
            enabled=True,
            public_key=public_key,
            secret_key=secret_key,
            host=config["base_url"],
            environment=config["environment"],
        )

        # Simple health check: create and immediately end a test span
        trace = adapter.start_trace(
            name="admin_health_check", metadata={"test": True}
        )
        adapter.end_trace(trace["trace_id"])
        adapter.flush()

    except Exception as e:
        status = "unhealthy"
        message = f"Connection failed: {str(e)}"

    config_obj = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
    if config_obj:
        config_obj.health_status = status
        config_obj.last_tested_at = utc_now()
        db.session.commit()

    _audit(
        "observability_health_check",
        "observability",
        "langfuse",
        actor,
        message,
        {},
    )

    return {
        "health_status": status,
        "message": message,
        "tested_at": utc_now().isoformat(),
        "details": {
            "base_url": config["base_url"],
            "auth": "configured" if config["credential_configured"] else "missing",
        },
    }


def disable_observability(actor: str = "system") -> dict:
    """Disable Langfuse and clear configuration."""
    config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
    if config:
        config.is_enabled = False
        config.credential_configured = False
        config.credential_fingerprint = None
        config.updated_at = utc_now()
        db.session.commit()

    # Deactivate all credentials
    ObservabilityCredential.query.filter_by(
        service_id="langfuse", is_active=True
    ).update({"is_active": False})
    db.session.commit()

    _audit(
        "observability_disabled",
        "observability",
        "langfuse",
        actor,
        "Langfuse observability disabled",
        {},
    )

    return {"disabled": True, "message": "Langfuse observability disabled"}


def _audit(
    event_type: str,
    scope: str,
    target_ref: str,
    actor: str,
    summary: str,
    metadata: dict,
) -> None:
    """Record an audit event."""
    from app.models.governance_core import SettingAuditEvent

    event = SettingAuditEvent(
        audit_event_id=f"audit_{uuid4().hex}",
        event_type=event_type,
        scope=scope,
        target_ref=target_ref,
        changed_by=actor,
        changed_at=utc_now(),
        summary=summary,
        metadata_json=metadata,
    )
    db.session.add(event)
    db.session.commit()
