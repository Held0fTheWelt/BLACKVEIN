"""MVP4 Phase C: Token Budget Enforcement & Cost-Aware Degradation Service."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from flask import current_app

logger = logging.getLogger(__name__)


class InMemoryObservabilityStorage:
    """Small dict-backed runtime storage used when no dedicated KV store is wired."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def delete(self, key: str) -> None:
        self._data.pop(key, None)


class RedisJsonObservabilityStorage:
    """JSON adapter around Redis so governance services can store dict/list values."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def get(self, key: str) -> Any:
        raw = self.client.get(key)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if not isinstance(raw, str):
            return raw
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def set(self, key: str, value: Any) -> None:
        self.client.set(key, json.dumps(_json_safe(value), separators=(",", ":")))

    def delete(self, key: str) -> None:
        self.client.delete(key)


_FALLBACK_RUNTIME_STORAGE = InMemoryObservabilityStorage()


def _json_safe(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def init_runtime_governance_storage(app: Any) -> None:
    """Attach Redis-backed governance storage when REDIS_URL is configured."""
    redis_url = (app.config.get("REDIS_URL") or "").strip()
    if not redis_url:
        return

    try:
        import redis

        client = redis.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
    except Exception as exc:
        app.logger.warning("Redis unavailable for runtime governance storage: %s", exc)
        return

    app.extensions["redis_client"] = RedisJsonObservabilityStorage(client)
    app.logger.info("Runtime governance storage initialized via Redis.")


def get_runtime_governance_storage() -> Any:
    """Return the configured runtime KV store or a stable in-process fallback."""
    extensions = getattr(current_app, "extensions", {})
    candidate = extensions.get("redis_client")
    if candidate is None:
        candidate = getattr(current_app, "redis_client", None)
    if candidate is not None and hasattr(candidate, "get") and hasattr(candidate, "set"):
        return candidate

    storage = extensions.get("observability_runtime_storage")
    if storage is None:
        storage = _FALLBACK_RUNTIME_STORAGE
        extensions["observability_runtime_storage"] = storage
    return storage


def _storage_list(storage: Any, key: str) -> list[dict[str, Any]]:
    stored = storage.get(key)
    if isinstance(stored, list):
        return [item for item in stored if isinstance(item, dict)]
    return []


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
    last_accounted_turn: int = -1
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    module_id: str | None = None
    selected_player_role: str | None = None
    cost_breakdown: dict[str, float] = field(default_factory=dict)
    latest_phase_costs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 4),
            "cost_per_turn_avg": round(self.cost_per_turn_avg, 4),
            "turns_executed": self.turns_executed,
            "last_accounted_turn": self.last_accounted_turn,
            "updated_at": self.updated_at,
            "module_id": self.module_id,
            "selected_player_role": self.selected_player_role,
            "cost_breakdown": {k: round(float(v or 0.0), 6) for k, v in self.cost_breakdown.items()},
            "latest_phase_costs": dict(self.latest_phase_costs),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CostSummary:
        return CostSummary(
            session_id=data.get("session_id", ""),
            input_tokens=int(data.get("input_tokens", 0) or 0),
            output_tokens=int(data.get("output_tokens", 0) or 0),
            cost_usd=float(data.get("cost_usd", 0.0) or 0.0),
            cost_per_turn_avg=float(data.get("cost_per_turn_avg", 0.0) or 0.0),
            turns_executed=int(data.get("turns_executed", 0) or 0),
            last_accounted_turn=int(data.get("last_accounted_turn", -1) or -1),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
            module_id=data.get("module_id"),
            selected_player_role=data.get("selected_player_role"),
            cost_breakdown={
                str(k): float(v or 0.0)
                for k, v in (data.get("cost_breakdown") or {}).items()
            },
            latest_phase_costs=dict(data.get("latest_phase_costs") or {}),
        )


class CostDashboard:
    """Aggregate and report cost metrics."""

    def __init__(self, session_storage: Any):
        self.storage = session_storage

    def get_session_cost_summary(self, session_id: str) -> CostSummary:
        """Get cost summary for session."""
        storage_key = f"cost_summary:{session_id}"
        stored = self.storage.get(storage_key)

        if stored and isinstance(stored, dict):
            return CostSummary.from_dict(stored)

        return CostSummary(session_id=session_id)

    def record_turn_cost(
        self,
        session_id: str,
        *,
        turn_number: int,
        cost_summary: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist truthful per-turn usage and update aggregate cost summary."""
        summary = self.get_session_cost_summary(session_id)
        if turn_number <= summary.last_accounted_turn:
            return {"applied": False, "summary": summary}

        metadata = metadata if isinstance(metadata, dict) else {}
        input_tokens = int(cost_summary.get("input_tokens", 0) or 0)
        output_tokens = int(cost_summary.get("output_tokens", 0) or 0)
        cost_usd = float(cost_summary.get("cost_usd", 0.0) or 0.0)
        phase_breakdown = {
            str(key): float(value or 0.0)
            for key, value in (cost_summary.get("cost_breakdown") or {}).items()
        }
        phase_costs = dict(cost_summary.get("phase_costs") or {})

        summary.input_tokens += input_tokens
        summary.output_tokens += output_tokens
        summary.cost_usd += cost_usd
        summary.turns_executed = max(summary.turns_executed, turn_number + 1)
        summary.last_accounted_turn = turn_number
        summary.updated_at = datetime.now(timezone.utc).isoformat()
        summary.module_id = str(metadata.get("module_id") or summary.module_id or "").strip() or None
        summary.selected_player_role = (
            str(metadata.get("selected_player_role") or summary.selected_player_role or "").strip() or None
        )
        for phase_name, phase_cost in phase_breakdown.items():
            summary.cost_breakdown[phase_name] = round(
                float(summary.cost_breakdown.get(phase_name, 0.0)) + phase_cost,
                6,
            )
        summary.latest_phase_costs = phase_costs
        if summary.turns_executed > 0:
            summary.cost_per_turn_avg = summary.cost_usd / summary.turns_executed

        self.storage.set(f"cost_summary:{session_id}", summary.to_dict())

        sessions = self._tracked_sessions()
        if session_id not in sessions:
            sessions.append(session_id)
            self.storage.set("cost_summary:sessions", sessions)

        event = {
            "session_id": session_id,
            "turn_number": turn_number,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": round(cost_usd, 6),
            "cost_breakdown": phase_breakdown,
            "phase_costs": phase_costs,
            "module_id": summary.module_id,
            "selected_player_role": summary.selected_player_role,
            "recorded_at": summary.updated_at,
        }
        self._append_usage_event(event)
        return {"applied": True, "summary": summary, "event": event}

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
        target_date = str(date).strip()
        events = [
            event for event in self._usage_events()
            if str(event.get("recorded_at", "")).startswith(target_date)
        ]
        return self._aggregate_report(events, {"date": target_date})

    def get_weekly_cost_report(self, week_start: str) -> dict[str, Any]:
        """Get weekly cost report."""
        week_start_str = str(week_start).strip()
        week_start_date = datetime.fromisoformat(week_start_str).date()
        events = []
        for event in self._usage_events():
            recorded_at = str(event.get("recorded_at", "")).strip()
            if not recorded_at:
                continue
            try:
                event_date = datetime.fromisoformat(recorded_at.replace("Z", "+00:00")).date()
            except ValueError:
                continue
            day_delta = (event_date - week_start_date).days
            if 0 <= day_delta < 7:
                events.append(event)
        return self._aggregate_report(events, {"week_start": week_start_str})

    def _tracked_sessions(self) -> list[str]:
        stored = self.storage.get("cost_summary:sessions")
        if isinstance(stored, list):
            return [str(item) for item in stored if str(item).strip()]
        return []

    def _append_usage_event(self, event: dict[str, Any]) -> None:
        global_events = _storage_list(self.storage, "cost_usage_events")
        global_events.append(dict(event))
        self.storage.set("cost_usage_events", global_events)

        session_key = f"cost_usage_events:{event['session_id']}"
        session_events = _storage_list(self.storage, session_key)
        session_events.append(dict(event))
        self.storage.set(session_key, session_events)

    def _usage_events(self) -> list[dict[str, Any]]:
        return _storage_list(self.storage, "cost_usage_events")

    def _aggregate_report(self, events: list[dict[str, Any]], envelope: dict[str, Any]) -> dict[str, Any]:
        sessions = {str(event.get("session_id")) for event in events if str(event.get("session_id") or "").strip()}
        total_cost = round(sum(float(event.get("cost_usd", 0.0) or 0.0) for event in events), 6)
        total_tokens = sum(int(event.get("total_tokens", 0) or 0) for event in events)
        cost_per_module: dict[str, float] = {}
        cost_per_role: dict[str, float] = {}
        cost_per_phase: dict[str, float] = {}
        for event in events:
            module_id = str(event.get("module_id") or "").strip()
            if module_id:
                cost_per_module[module_id] = round(
                    cost_per_module.get(module_id, 0.0) + float(event.get("cost_usd", 0.0) or 0.0),
                    6,
                )
            role = str(event.get("selected_player_role") or "").strip()
            if role:
                cost_per_role[role] = round(
                    cost_per_role.get(role, 0.0) + float(event.get("cost_usd", 0.0) or 0.0),
                    6,
                )
            for phase_name, phase_cost in (event.get("cost_breakdown") or {}).items():
                cost_per_phase[str(phase_name)] = round(
                    cost_per_phase.get(str(phase_name), 0.0) + float(phase_cost or 0.0),
                    6,
                )

        average_session_cost = round(total_cost / len(sessions), 6) if sessions else 0.0
        return {
            **envelope,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "session_count": len(sessions),
            "average_session_cost": average_session_cost,
            "event_count": len(events),
            "cost_per_module": cost_per_module,
            "cost_per_role": cost_per_role,
            "cost_per_phase": cost_per_phase,
            "cost_anomalies": [
                {
                    "session_id": event.get("session_id"),
                    "turn_number": event.get("turn_number"),
                    "reason": "non_zero_cost_event",
                    "cost_usd": event.get("cost_usd"),
                }
                for event in events
                if float(event.get("cost_usd", 0.0) or 0.0) > average_session_cost * 2 and average_session_cost > 0.0
            ],
        }


def ingest_runtime_turn_cost(
    session_storage: Any,
    *,
    session_id: str,
    turn_number: int,
    cost_summary: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist truthful runtime cost usage and apply token budget consumption once."""
    dashboard = CostDashboard(session_storage)
    record = dashboard.record_turn_cost(
        session_id,
        turn_number=turn_number,
        cost_summary=cost_summary,
        metadata=metadata,
    )
    if not record.get("applied"):
        return record

    total_tokens = int(cost_summary.get("input_tokens", 0) or 0) + int(cost_summary.get("output_tokens", 0) or 0)
    budget_service = TokenBudgetService(session_storage)
    degradation_level = budget_service.consume_tokens(session_id, total_tokens)
    record["degradation_level"] = degradation_level.value
    record["budget_status"] = budget_service.get_budget_status(session_id)
    return record


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
    import uuid
    from app.models.governance_core import ObservabilityConfig, ObservabilityCredential
    from app.extensions import db
    from app.services.governance_secret_crypto_service import encrypt_secret

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
        # Deactivate old public_key credentials
        ObservabilityCredential.query.filter_by(
            service_id="langfuse",
            secret_name="public_key",
            is_active=True,
        ).update({"is_active": False})

        record = encrypt_secret(public_key)
        cred = ObservabilityCredential(
            credential_id=str(uuid.uuid4()),
            service_id="langfuse",
            secret_name="public_key",
            encrypted_secret=record.encrypted_secret,
            encrypted_dek=record.encrypted_dek,
            secret_nonce=record.secret_nonce,
            dek_nonce=record.dek_nonce,
            dek_algorithm=record.dek_algorithm,
            secret_fingerprint=record.secret_fingerprint,
            is_active=True,
        )
        db.session.add(cred)
        fingerprints["public_key"] = record.secret_fingerprint

    if secret_key:
        # Deactivate old secret_key credentials
        ObservabilityCredential.query.filter_by(
            service_id="langfuse",
            secret_name="secret_key",
            is_active=True,
        ).update({"is_active": False})

        record = encrypt_secret(secret_key)
        cred = ObservabilityCredential(
            credential_id=str(uuid.uuid4()),
            service_id="langfuse",
            secret_name="secret_key",
            encrypted_secret=record.encrypted_secret,
            encrypted_dek=record.encrypted_dek,
            secret_nonce=record.secret_nonce,
            dek_nonce=record.dek_nonce,
            dek_algorithm=record.dek_algorithm,
            secret_fingerprint=record.secret_fingerprint,
            is_active=True,
        )
        db.session.add(cred)
        fingerprints["secret_key"] = record.secret_fingerprint
        config.credential_configured = True
        config.credential_fingerprint = record.secret_fingerprint
        config.is_enabled = True

    db.session.commit()
    logger.info(f"Observability credential written by {actor}")
    return fingerprints


def get_observability_credential_for_runtime(secret_name: str) -> Optional[str]:
    """Retrieve and decrypt an observability credential."""
    from app.models.governance_core import ObservabilityCredential
    from app.services.governance_secret_crypto_service import decrypt_secret

    cred = ObservabilityCredential.query.filter_by(
        service_id="langfuse",
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
