"""Governance for Hugging Face Hub read tokens (encrypted DB storage, HF_TOKEN process env).

Tokens are stored in ``observability_credentials`` with ``service_id=huggingface_hub``,
same envelope encryption as Langfuse credentials. At backend startup the decrypted
token is copied into ``os.environ[\"HF_TOKEN\"]`` when present so ``huggingface_hub`` /
``fastembed`` pick it up without code changes.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import requests

from app.governance.errors import governance_error

logger = logging.getLogger(__name__)

HF_HUB_SERVICE_ID = "huggingface_hub"
HF_HUB_SECRET_NAME = "hub_token"


def _decrypt_observability_secret(service_id: str, secret_name: str) -> Optional[str]:
    from app.models.governance_core import ObservabilityCredential
    from app.services.governance_secret_crypto_service import decrypt_secret

    cred = ObservabilityCredential.query.filter_by(
        service_id=service_id,
        secret_name=secret_name,
        is_active=True,
    ).first()
    if not cred:
        return None
    try:
        if cred.encrypted_dek == b"dek_stub":
            return cred.encrypted_secret.decode()
        return decrypt_secret(
            encrypted_secret=cred.encrypted_secret,
            encrypted_dek=cred.encrypted_dek,
            secret_nonce=cred.secret_nonce,
            dek_nonce=cred.dek_nonce,
        )
    except Exception as exc:
        logger.error("Failed to decrypt HF hub credential: %s", exc)
        return None


def get_hf_hub_token_for_runtime() -> Optional[str]:
    """Return decrypted HF Hub read token from governance store, or ``None``."""
    return _decrypt_observability_secret(HF_HUB_SERVICE_ID, HF_HUB_SECRET_NAME)


def get_hf_hub_status() -> dict[str, Any]:
    """Public status for admin UI (no plaintext secrets)."""
    from app.models.governance_core import ObservabilityConfig, ObservabilityCredential

    config = ObservabilityConfig.query.filter_by(service_id=HF_HUB_SERVICE_ID).first()
    active = ObservabilityCredential.query.filter_by(
        service_id=HF_HUB_SERVICE_ID,
        secret_name=HF_HUB_SECRET_NAME,
        is_active=True,
    ).first()
    env_set = bool((os.environ.get("HF_TOKEN") or "").strip())
    return {
        "service_id": HF_HUB_SERVICE_ID,
        "credential_configured": bool(active),
        "credential_fingerprint": (config.credential_fingerprint if config else None),
        "health_status": (config.health_status if config else "unconfigured"),
        "last_tested_at": (config.last_tested_at.isoformat() if config and config.last_tested_at else None),
        "process_env_hf_token_set": env_set,
    }


def write_hf_hub_token(token: str, actor: str = "system") -> dict[str, str]:
    """Encrypt and store HF Hub read token; returns fingerprint only."""
    import uuid
    from datetime import datetime, timezone

    from app.extensions import db
    from app.models.governance_core import ObservabilityConfig, ObservabilityCredential
    from app.services.governance_secret_crypto_service import encrypt_secret

    raw = (token or "").strip()
    if not raw:
        raise governance_error("credential_invalid", "token is required and cannot be blank.", 400, {})

    config = ObservabilityConfig.query.filter_by(service_id=HF_HUB_SERVICE_ID).first()
    if not config:
        config = ObservabilityConfig(
            service_id=HF_HUB_SERVICE_ID,
            service_type="huggingface_hub",
            display_name="Hugging Face Hub",
            base_url="https://huggingface.co",
            is_enabled=True,
        )
        db.session.add(config)

    ObservabilityCredential.query.filter_by(
        service_id=HF_HUB_SERVICE_ID,
        secret_name=HF_HUB_SECRET_NAME,
        is_active=True,
    ).update({"is_active": False})

    record = encrypt_secret(raw)
    cred = ObservabilityCredential(
        credential_id=str(uuid.uuid4()),
        service_id=HF_HUB_SERVICE_ID,
        secret_name=HF_HUB_SECRET_NAME,
        encrypted_secret=record.encrypted_secret,
        encrypted_dek=record.encrypted_dek,
        secret_nonce=record.secret_nonce,
        dek_nonce=record.dek_nonce,
        dek_algorithm=record.dek_algorithm,
        secret_fingerprint=record.secret_fingerprint,
        is_active=True,
    )
    db.session.add(cred)
    config.credential_configured = True
    config.credential_fingerprint = record.secret_fingerprint
    config.is_enabled = True
    config.health_status = "unknown"
    config.last_tested_at = None
    db.session.commit()
    logger.info("HF hub token written by %s", actor)
    sync_hf_token_from_store_to_os_environ()
    return {"hub_token": record.secret_fingerprint}


def clear_hf_hub_token(actor: str = "system") -> dict[str, Any]:
    """Deactivate stored token; does not clear ``HF_TOKEN`` from process env (restart to drop)."""
    from app.extensions import db
    from app.models.governance_core import ObservabilityConfig, ObservabilityCredential

    ObservabilityCredential.query.filter_by(
        service_id=HF_HUB_SERVICE_ID,
        secret_name=HF_HUB_SECRET_NAME,
        is_active=True,
    ).update({"is_active": False})
    config = ObservabilityConfig.query.filter_by(service_id=HF_HUB_SERVICE_ID).first()
    if config:
        config.credential_configured = False
        config.credential_fingerprint = None
        config.health_status = "unconfigured"
        config.last_tested_at = None
    db.session.commit()
    logger.info("HF hub token cleared by %s", actor)
    return {"cleared": True}


def test_hf_hub_connection(actor: str = "system") -> dict[str, Any]:
    """Verify token against Hugging Face ``whoami-v2`` (uses stored token or ``HF_TOKEN`` env)."""
    from datetime import datetime, timezone

    from app.extensions import db
    from app.models.governance_core import ObservabilityConfig

    token = get_hf_hub_token_for_runtime() or (os.environ.get("HF_TOKEN") or "").strip()
    if not token:
        return {
            "ok": False,
            "health_status": "credential_missing",
            "message": "No Hugging Face token in governance store or HF_TOKEN environment variable.",
        }

    try:
        response = requests.get(
            "https://huggingface.co/api/whoami-v2",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20.0,
        )
    except Exception as exc:
        return {
            "ok": False,
            "health_status": "error",
            "message": f"Request failed: {exc}",
        }

    config = ObservabilityConfig.query.filter_by(service_id=HF_HUB_SERVICE_ID).first()
    now = datetime.now(timezone.utc)
    if response.status_code != 200:
        msg = (response.text or "")[:500] if response.text else "unknown error"
        if config:
            config.health_status = "error"
            config.last_tested_at = now
            db.session.commit()
        return {
            "ok": False,
            "health_status": "error",
            "message": f"Hugging Face API returned HTTP {response.status_code}: {msg}",
        }

    try:
        body = response.json()
    except Exception:
        body = {}
    name = body.get("name") or body.get("fullname") or "unknown"
    if config:
        config.health_status = "connected"
        config.last_tested_at = now
        db.session.commit()
    logger.info("HF hub connection test ok for actor=%s identity=%s", actor, name)
    return {
        "ok": True,
        "health_status": "connected",
        "message": "Hugging Face Hub accepted the token.",
        "identity": name,
    }


def sync_hf_token_from_store_to_os_environ() -> None:
    """If a token exists in the governance store, set ``HF_TOKEN`` for this process."""
    tok = get_hf_hub_token_for_runtime()
    if tok:
        os.environ["HF_TOKEN"] = tok
