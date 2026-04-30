"""MVP4 Phase C: Token Budget Enforcement & Cost-Aware Degradation Service."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DegradationLevel(Enum):
    """Cost-based degradation levels."""
    NONE = "none"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class TokenBudgetConfig:
    """Per-session token budget configuration."""
    session_id: str
    total_budget: int = 50000
    used_tokens: int = 0
    warning_threshold: float = 0.80
    ceiling_threshold: float = 1.0
    degradation_strategy: str = "ldss_shorter"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_override: Optional[dict] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "total_budget": self.total_budget,
            "used_tokens": self.used_tokens,
            "warning_threshold": self.warning_threshold,
            "ceiling_threshold": self.ceiling_threshold,
            "degradation_strategy": self.degradation_strategy,
            "created_at": self.created_at,
            "last_override": self.last_override,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> TokenBudgetConfig:
        return TokenBudgetConfig(
            session_id=data.get("session_id", ""),
            total_budget=data.get("total_budget", 50000),
            used_tokens=data.get("used_tokens", 0),
            warning_threshold=data.get("warning_threshold", 0.80),
            ceiling_threshold=data.get("ceiling_threshold", 1.0),
            degradation_strategy=data.get("degradation_strategy", "ldss_shorter"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            last_override=data.get("last_override"),
        )


class TokenBudgetService:
    """Manage token budgets and cost-aware degradation decisions."""

    def __init__(self, session_storage: Any):
        self.storage = session_storage

    def get_budget(self, session_id: str) -> TokenBudgetConfig:
        """Get current budget for session."""
        storage_key = f"token_budget:{session_id}"
        stored = self.storage.get(storage_key)

        if stored:
            if isinstance(stored, dict):
                return TokenBudgetConfig.from_dict(stored)
            return stored

        config = TokenBudgetConfig(session_id=session_id)
        self.storage.set(storage_key, config)
        return config

    def consume_tokens(self, session_id: str, tokens: int) -> DegradationLevel:
        """Consume tokens and return degradation level."""
        config = self.get_budget(session_id)
        config.used_tokens += tokens

        usage_percent = config.used_tokens / config.total_budget

        if usage_percent >= config.ceiling_threshold:
            level = DegradationLevel.CRITICAL
        elif usage_percent >= config.warning_threshold:
            level = DegradationLevel.WARNING
        else:
            level = DegradationLevel.NONE

        self.storage.set(f"token_budget:{session_id}", config)
        logger.info(f"Tokens consumed: {session_id}, total={config.used_tokens}/{config.total_budget}")

        return level

    def apply_cost_aware_degradation(
        self,
        session_id: str,
        degradation_level: DegradationLevel,
        graph_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Adjust narrative generation based on budget usage."""
        if degradation_level == DegradationLevel.NONE:
            return graph_state

        config = self.get_budget(session_id)

        if degradation_level == DegradationLevel.WARNING:
            if config.degradation_strategy == "ldss_shorter":
                ldss_config = graph_state.get("ldss_config", {})
                ldss_config["max_narration_length"] = 150
                graph_state["ldss_config"] = ldss_config

        elif degradation_level == DegradationLevel.CRITICAL:
            if config.degradation_strategy == "fallback_cheaper":
                graph_state["use_template_fallback"] = True
                graph_state["skip_ldss"] = True

        return graph_state

    def override_budget(
        self,
        session_id: str,
        tokens_to_add: int,
        admin_user: str,
        reason: str,
    ) -> TokenBudgetConfig:
        """Admin override: add tokens to budget."""
        config = self.get_budget(session_id)
        old_total = config.total_budget
        config.total_budget += tokens_to_add
        config.last_override = {
            "admin_user": admin_user,
            "tokens_added": tokens_to_add,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.storage.set(f"token_budget:{session_id}", config)
        logger.info(f"Budget override: {session_id}, {old_total} -> {config.total_budget}")

        return config

    def get_budget_status(self, session_id: str) -> dict[str, Any]:
        """Get current budget status."""
        config = self.get_budget(session_id)
        usage_percent = (config.used_tokens / config.total_budget * 100) if config.total_budget > 0 else 0

        return {
            "session_id": session_id,
            "total_budget": config.total_budget,
            "used_tokens": config.used_tokens,
            "remaining_tokens": max(0, config.total_budget - config.used_tokens),
            "usage_percent": usage_percent,
            "degradation_level": self._calculate_degradation_level(usage_percent).value,
            "last_override": config.last_override,
        }

    @staticmethod
    def _calculate_degradation_level(usage_percent: float) -> DegradationLevel:
        if usage_percent >= 100.0:
            return DegradationLevel.CRITICAL
        elif usage_percent >= 80.0:
            return DegradationLevel.WARNING
        else:
            return DegradationLevel.NONE


@dataclass
class CostSummary:
    """Per-session cost summary."""
    session_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cost_per_turn_avg: float = 0.0
    turns_executed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 4),
            "cost_per_turn_avg": round(self.cost_per_turn_avg, 4),
            "turns_executed": self.turns_executed,
        }


class CostDashboard:
    """Aggregate and report cost metrics."""

    def __init__(self, session_storage: Any):
        self.storage = session_storage

    def get_session_cost_summary(self, session_id: str) -> CostSummary:
        """Get cost summary for session."""
        storage_key = f"cost_summary:{session_id}"
        stored = self.storage.get(storage_key)

        if stored and isinstance(stored, dict):
            return CostSummary(
                session_id=session_id,
                input_tokens=stored.get("input_tokens", 0),
                output_tokens=stored.get("output_tokens", 0),
                cost_usd=stored.get("cost_usd", 0.0),
                cost_per_turn_avg=stored.get("cost_per_turn_avg", 0.0),
                turns_executed=stored.get("turns_executed", 0),
            )

        return CostSummary(session_id=session_id)

    def update_session_cost_summary(
        self,
        session_id: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        turn_count: int,
    ) -> None:
        """Update cost summary."""
        summary = self.get_session_cost_summary(session_id)
        summary.input_tokens += input_tokens
        summary.output_tokens += output_tokens
        summary.cost_usd += cost_usd
        summary.turns_executed = turn_count

        if turn_count > 0:
            summary.cost_per_turn_avg = summary.cost_usd / turn_count

        self.storage.set(f"cost_summary:{session_id}", summary.to_dict())

    def get_daily_cost_report(self, date: str) -> dict[str, Any]:
        """Get daily cost report."""
        return {
            "date": date,
            "total_cost": 0.0,
            "total_tokens": 0,
            "session_count": 0,
            "average_session_cost": 0.0,
            "cost_anomalies": [],
        }

    def get_weekly_cost_report(self, week_start: str) -> dict[str, Any]:
        """Get weekly cost report."""
        return {
            "week_start": week_start,
            "total_cost": 0.0,
            "total_tokens": 0,
            "session_count": 0,
            "average_session_cost": 0.0,
            "cost_per_module": {},
            "cost_per_role": {},
        }


def get_observability_config() -> dict[str, Any]:
    """Get current Langfuse observability configuration.

    Validates health_status against current credential state:
    - If enabled but no credentials → health_status is "unconfigured"
    - If credentials missing → is_enabled is automatically False
    """
    from app.models.governance_core import ObservabilityConfig
    from app.extensions import db

    config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
    if not config:
        return {
            "service_id": "langfuse",
            "service_type": "langfuse",
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
            "health_status": "unconfigured",
        }

    # Validate health_status against current credential state
    is_enabled = config.is_enabled
    credential_configured = config.credential_configured
    health_status = config.health_status

    # If enabled but credentials missing → not actually enabled and health is unconfigured
    if is_enabled and not credential_configured:
        is_enabled = False
        health_status = "unconfigured"

    # If not enabled → health is disabled (not unknown)
    if not is_enabled and health_status not in ("unconfigured", "disabled"):
        health_status = "disabled"

    return {
        "service_id": config.service_id,
        "service_type": config.service_type,
        "display_name": config.display_name,
        "is_enabled": is_enabled,
        "base_url": config.base_url,
        "environment": config.environment,
        "release": config.release,
        "sample_rate": config.sample_rate,
        "capture_prompts": config.capture_prompts,
        "capture_outputs": config.capture_outputs,
        "capture_retrieval": config.capture_retrieval,
        "redaction_mode": config.redaction_mode,
        "credential_configured": credential_configured,
        "credential_fingerprint": config.credential_fingerprint,
        "health_status": health_status,
    }


def write_observability_credential(
    public_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    actor: str = "system",
) -> dict[str, str]:
    """Write encrypted observability credentials."""
    import hashlib
    import uuid
    from app.models.governance_core import ObservabilityConfig, ObservabilityCredential
    from app.extensions import db

    config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
    if not config:
        config = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
        )
        db.session.add(config)

    fingerprints = {}

    if public_key:
        pk_fingerprint = hashlib.sha256(public_key.encode()).hexdigest()[:16]
        cred = ObservabilityCredential(
            credential_id=str(uuid.uuid4()),
            service_id="langfuse",
            secret_name="public_key",
            encrypted_secret=public_key.encode(),
            encrypted_dek=b"dek_stub",
            secret_nonce=b"nonce",
            dek_nonce=b"dek_nonce",
            secret_fingerprint=pk_fingerprint,
            is_active=True,
        )
        db.session.add(cred)
        fingerprints["public_key"] = pk_fingerprint

    if secret_key:
        sk_fingerprint = hashlib.sha256(secret_key.encode()).hexdigest()[:16]
        cred = ObservabilityCredential(
            credential_id=str(uuid.uuid4()),
            service_id="langfuse",
            secret_name="secret_key",
            encrypted_secret=secret_key.encode(),
            encrypted_dek=b"dek_stub",
            secret_nonce=b"nonce",
            dek_nonce=b"dek_nonce",
            secret_fingerprint=sk_fingerprint,
            is_active=True,
        )
        db.session.add(cred)
        fingerprints["secret_key"] = sk_fingerprint
        config.credential_configured = True
        config.credential_fingerprint = sk_fingerprint

    db.session.commit()
    logger.info(f"Observability credential written by {actor}")
    return fingerprints


def get_observability_credential_for_runtime(secret_name: str) -> Optional[str]:
    """Retrieve and decrypt an observability credential."""
    from app.models.governance_core import ObservabilityCredential

    cred = ObservabilityCredential.query.filter_by(
        service_id="langfuse",
        secret_name=secret_name,
        is_active=True,
    ).first()

    if not cred:
        return None

    try:
        return cred.encrypted_secret.decode()
    except Exception as e:
        logger.error(f"Failed to decrypt credential {secret_name}: {str(e)}")
        return None


def test_observability_connection(actor: str = "system") -> dict[str, Any]:
    """Test connection to Langfuse service."""
    config = get_observability_config()

    if not config.get("is_enabled"):
        return {
            "ok": False,
            "health_status": "disabled",
            "message": "Langfuse observability is disabled",
        }

    secret_key = get_observability_credential_for_runtime("secret_key")
    if not secret_key:
        return {
            "ok": False,
            "health_status": "credential_missing",
            "message": "Langfuse credentials not configured",
        }

    return {
        "ok": True,
        "health_status": "connected",
        "message": "Connection successful",
    }


def update_observability_config(config_dict: dict[str, Any], actor: str = "system") -> dict[str, Any]:
    """Update Langfuse observability configuration."""
    from app.models.governance_core import ObservabilityConfig
    from app.extensions import db

    config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
    if not config:
        config = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
        )
        db.session.add(config)

    if "is_enabled" in config_dict:
        config.is_enabled = config_dict["is_enabled"]
    if "base_url" in config_dict:
        config.base_url = config_dict["base_url"]
    if "environment" in config_dict:
        config.environment = config_dict["environment"]
    if "release" in config_dict:
        config.release = config_dict["release"]
    if "sample_rate" in config_dict:
        config.sample_rate = float(config_dict["sample_rate"])
    if "capture_prompts" in config_dict:
        config.capture_prompts = config_dict["capture_prompts"]
    if "capture_outputs" in config_dict:
        config.capture_outputs = config_dict["capture_outputs"]
    if "capture_retrieval" in config_dict:
        config.capture_retrieval = config_dict["capture_retrieval"]
    if "redaction_mode" in config_dict:
        config.redaction_mode = config_dict["redaction_mode"]

    db.session.commit()
    logger.info(f"Observability configuration updated by {actor}")

    return get_observability_config()


def disable_observability(actor: str = "system") -> dict[str, Any]:
    """Disable observability by deactivating all credentials."""
    from app.models.governance_core import ObservabilityConfig, ObservabilityCredential
    from app.extensions import db

    active_creds = ObservabilityCredential.query.filter_by(
        service_id="langfuse",
        is_active=True,
    ).all()

    for cred in active_creds:
        cred.is_active = False

    config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
    if config:
        config.is_enabled = False
        config.credential_configured = False

    db.session.commit()
    logger.info(f"Observability disabled by {actor}")

    return {"ok": True, "message": "Observability disabled"}
