"""Persistence models for operational settings and runtime governance MVP."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.extensions import db
from app.utils.time_utils import utc_now as _utc_now


class BootstrapConfig(db.Model):
    """Singleton bootstrap and trust-anchor status row."""

    __tablename__ = "bootstrap_configs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bootstrap_state = db.Column(db.String(64), nullable=False, index=True)
    bootstrap_locked = db.Column(db.Boolean, nullable=False, default=False)
    selected_preset = db.Column(db.String(64), nullable=True)
    secret_storage_mode = db.Column(db.String(64), nullable=False)
    runtime_profile = db.Column(db.String(64), nullable=False)
    generation_execution_mode = db.Column(db.String(64), nullable=False)
    retrieval_execution_mode = db.Column(db.String(64), nullable=False)
    validation_execution_mode = db.Column(db.String(64), nullable=False)
    provider_selection_mode = db.Column(db.String(64), nullable=False)
    trust_anchor_fingerprint = db.Column(db.String(256), nullable=True)
    trust_anchor_metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    reopen_requires_elevated_auth = db.Column(db.Boolean, nullable=False, default=True)
    bootstrap_completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    bootstrap_completed_by = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)


class BootstrapPreset(db.Model):
    """Bootstrap preset templates shown during initial setup."""

    __tablename__ = "bootstrap_presets"

    preset_id = db.Column(db.String(64), primary_key=True)
    display_name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text(), nullable=False)
    generation_execution_mode = db.Column(db.String(64), nullable=False)
    retrieval_execution_mode = db.Column(db.String(64), nullable=False)
    validation_execution_mode = db.Column(db.String(64), nullable=False)
    provider_selection_mode = db.Column(db.String(64), nullable=False)
    default_runtime_profile = db.Column(db.String(64), nullable=False)
    default_provider_templates_json = db.Column(db.JSON, nullable=False, default=list)
    default_budget_policy_json = db.Column(db.JSON, nullable=False, default=dict)
    is_builtin = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)


class AIProviderConfig(db.Model):
    """Governed provider metadata and availability flags."""

    __tablename__ = "ai_provider_configs"

    provider_id = db.Column(db.String(128), primary_key=True)
    provider_type = db.Column(db.String(64), nullable=False, index=True)
    display_name = db.Column(db.String(128), nullable=False)
    base_url = db.Column(db.String(512), nullable=True)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True, index=True)
    is_local = db.Column(db.Boolean, nullable=False, default=False)
    supports_structured_output = db.Column(db.Boolean, nullable=False, default=False)
    health_status = db.Column(db.String(32), nullable=False, default="unknown")
    credential_configured = db.Column(db.Boolean, nullable=False, default=False)
    credential_fingerprint = db.Column(db.String(256), nullable=True)
    last_tested_at = db.Column(db.DateTime(timezone=True), nullable=True)
    allow_live_runtime = db.Column(db.Boolean, nullable=False, default=True)
    allow_preview_runtime = db.Column(db.Boolean, nullable=False, default=True)
    allow_writers_room = db.Column(db.Boolean, nullable=False, default=True)
    allow_research_suite = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)


class AIProviderCredential(db.Model):
    """Encrypted write-only secret records per provider."""

    __tablename__ = "ai_provider_credentials"

    credential_id = db.Column(db.String(128), primary_key=True)
    provider_id = db.Column(db.String(128), db.ForeignKey("ai_provider_configs.provider_id"), nullable=False, index=True)
    secret_name = db.Column(db.String(128), nullable=False)
    encrypted_secret = db.Column(db.LargeBinary(), nullable=False)
    encrypted_dek = db.Column(db.LargeBinary(), nullable=False)
    secret_nonce = db.Column(db.LargeBinary(), nullable=False)
    dek_nonce = db.Column(db.LargeBinary(), nullable=False)
    dek_algorithm = db.Column(db.String(64), nullable=False, default="AES-256-GCM")
    kek_key_id = db.Column(db.String(128), nullable=True)
    secret_fingerprint = db.Column(db.String(256), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)
    rotated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    rotation_in_progress = db.Column(db.Boolean, nullable=False, default=False)


class AIModelConfig(db.Model):
    """Governed model catalog under a provider."""

    __tablename__ = "ai_model_configs"

    model_id = db.Column(db.String(128), primary_key=True)
    provider_id = db.Column(db.String(128), db.ForeignKey("ai_provider_configs.provider_id"), nullable=False, index=True)
    model_name = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(256), nullable=False)
    model_role = db.Column(db.String(32), nullable=False, index=True)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True, index=True)
    structured_output_capable = db.Column(db.Boolean, nullable=False, default=False)
    timeout_seconds = db.Column(db.Integer, nullable=False, default=30)
    max_context_tokens = db.Column(db.Integer, nullable=True)
    cost_method = db.Column(db.String(64), nullable=False, default="none")
    input_price_per_1k = db.Column(db.Numeric(18, 6), nullable=True)
    output_price_per_1k = db.Column(db.Numeric(18, 6), nullable=True)
    flat_request_price = db.Column(db.Numeric(18, 6), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)


class AITaskRoute(db.Model):
    """Route definitions binding task_kind/workflow_scope to model choices."""

    __tablename__ = "ai_task_routes"

    route_id = db.Column(db.String(128), primary_key=True)
    task_kind = db.Column(db.String(128), nullable=False, index=True)
    workflow_scope = db.Column(db.String(128), nullable=False, index=True)
    preferred_model_id = db.Column(db.String(128), db.ForeignKey("ai_model_configs.model_id"), nullable=True)
    fallback_model_id = db.Column(db.String(128), db.ForeignKey("ai_model_configs.model_id"), nullable=True)
    mock_model_id = db.Column(db.String(128), db.ForeignKey("ai_model_configs.model_id"), nullable=True)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True, index=True)
    use_mock_when_provider_unavailable = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)


class SystemSettingRecord(db.Model):
    """Scope/key/value record for operationally editable settings."""

    __tablename__ = "system_setting_records"

    setting_id = db.Column(db.String(128), primary_key=True)
    scope = db.Column(db.String(64), nullable=False, index=True)
    setting_key = db.Column(db.String(128), nullable=False, index=True)
    setting_value_json = db.Column(db.JSON, nullable=False, default=dict)
    is_secret_backed = db.Column(db.Boolean, nullable=False, default=False)
    is_user_visible = db.Column(db.Boolean, nullable=False, default=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)
    updated_by = db.Column(db.String(128), nullable=True)


class ResolvedRuntimeConfigSnapshot(db.Model):
    """Optional cached resolved runtime config snapshot."""

    __tablename__ = "resolved_runtime_config_snapshots"

    snapshot_id = db.Column(db.String(128), primary_key=True)
    config_version = db.Column(db.String(128), nullable=False, unique=True, index=True)
    generated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, index=True)
    generation_execution_mode = db.Column(db.String(64), nullable=False)
    retrieval_execution_mode = db.Column(db.String(64), nullable=False)
    validation_execution_mode = db.Column(db.String(64), nullable=False)
    runtime_profile = db.Column(db.String(64), nullable=False)
    provider_selection_mode = db.Column(db.String(64), nullable=False)
    resolved_config_json = db.Column(db.JSON, nullable=False, default=dict)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)


class ProviderHealthCheck(db.Model):
    """Health test history for governed providers."""

    __tablename__ = "provider_health_checks"

    health_check_id = db.Column(db.String(128), primary_key=True)
    provider_id = db.Column(db.String(128), db.ForeignKey("ai_provider_configs.provider_id"), nullable=False, index=True)
    health_status = db.Column(db.String(32), nullable=False, index=True)
    latency_ms = db.Column(db.Integer, nullable=True)
    error_code = db.Column(db.String(128), nullable=True)
    error_message = db.Column(db.String(512), nullable=True)
    tested_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, index=True)


class AIUsageEvent(db.Model):
    """Per-request usage/cost event for auditable billing metrics."""

    __tablename__ = "ai_usage_events"

    usage_event_id = db.Column(db.String(128), primary_key=True)
    provider_id = db.Column(db.String(128), db.ForeignKey("ai_provider_configs.provider_id"), nullable=True, index=True)
    model_id = db.Column(db.String(128), db.ForeignKey("ai_model_configs.model_id"), nullable=True, index=True)
    task_kind = db.Column(db.String(128), nullable=False, index=True)
    workflow_scope = db.Column(db.String(128), nullable=False, index=True)
    request_id = db.Column(db.String(128), nullable=False, index=True)
    success = db.Column(db.Boolean, nullable=False, default=True)
    latency_ms = db.Column(db.Integer, nullable=True)
    input_tokens = db.Column(db.Integer, nullable=True)
    output_tokens = db.Column(db.Integer, nullable=True)
    provider_reported_cost = db.Column(db.Numeric(18, 6), nullable=True)
    estimated_cost = db.Column(db.Numeric(18, 6), nullable=True)
    cost_method_used = db.Column(db.String(64), nullable=False, default="none")
    degraded_mode_used = db.Column(db.Boolean, nullable=False, default=False)
    retry_used = db.Column(db.Boolean, nullable=False, default=False)
    fallback_used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, index=True)


class CostBudgetPolicy(db.Model):
    """Configured spending boundaries across global/provider/workflow scopes."""

    __tablename__ = "cost_budget_policies"

    budget_policy_id = db.Column(db.String(128), primary_key=True)
    scope_kind = db.Column(db.String(64), nullable=False, index=True)
    scope_ref = db.Column(db.String(128), nullable=True, index=True)
    daily_limit = db.Column(db.Numeric(18, 6), nullable=True)
    monthly_limit = db.Column(db.Numeric(18, 6), nullable=True)
    warning_threshold_percent = db.Column(db.Integer, nullable=False, default=80)
    hard_stop_enabled = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)


class CostRollup(db.Model):
    """Pre-aggregated daily usage/cost rows."""

    __tablename__ = "cost_rollups"

    rollup_id = db.Column(db.String(128), primary_key=True)
    rollup_date = db.Column(db.Date(), nullable=False, index=True)
    provider_id = db.Column(db.String(128), db.ForeignKey("ai_provider_configs.provider_id"), nullable=True, index=True)
    model_id = db.Column(db.String(128), db.ForeignKey("ai_model_configs.model_id"), nullable=True, index=True)
    workflow_scope = db.Column(db.String(128), nullable=True, index=True)
    request_count = db.Column(db.Integer, nullable=False, default=0)
    estimated_cost_total = db.Column(db.Numeric(18, 6), nullable=False, default=Decimal("0"))
    provider_reported_cost_total = db.Column(db.Numeric(18, 6), nullable=True)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    fallback_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)


class ObservabilityConfig(db.Model):
    """Langfuse observability service configuration."""

    __tablename__ = "observability_configs"

    service_id = db.Column(db.String(64), primary_key=True)  # "langfuse"
    service_type = db.Column(db.String(64), nullable=False)  # "langfuse"
    display_name = db.Column(db.String(128), nullable=False)  # "Langfuse"
    base_url = db.Column(db.String(512), nullable=False, default="https://cloud.langfuse.com")
    is_enabled = db.Column(db.Boolean, nullable=False, default=False)

    environment = db.Column(db.String(64), nullable=False, default="development")
    release = db.Column(db.String(128), nullable=False, default="unknown")
    sample_rate = db.Column(db.Float, nullable=False, default=1.0)

    capture_prompts = db.Column(db.Boolean, nullable=False, default=True)
    capture_outputs = db.Column(db.Boolean, nullable=False, default=True)
    capture_retrieval = db.Column(db.Boolean, nullable=False, default=False)

    redaction_mode = db.Column(db.String(32), nullable=False, default="strict")

    credential_configured = db.Column(db.Boolean, nullable=False, default=False)
    credential_fingerprint = db.Column(db.String(256), nullable=True)

    health_status = db.Column(db.String(32), nullable=False, default="unknown")
    last_tested_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)


class ObservabilityCredential(db.Model):
    """Encrypted write-only credentials for observability services (Langfuse, etc.)."""

    __tablename__ = "observability_credentials"

    credential_id = db.Column(db.String(128), primary_key=True)
    service_id = db.Column(db.String(64), db.ForeignKey("observability_configs.service_id"), nullable=False, index=True)

    secret_name = db.Column(db.String(128), nullable=False)  # "public_key" or "secret_key"

    encrypted_secret = db.Column(db.LargeBinary(), nullable=False)
    encrypted_dek = db.Column(db.LargeBinary(), nullable=False)
    secret_nonce = db.Column(db.LargeBinary(), nullable=False)
    dek_nonce = db.Column(db.LargeBinary(), nullable=False)
    dek_algorithm = db.Column(db.String(64), nullable=False, default="AES-256-GCM")
    kek_key_id = db.Column(db.String(128), nullable=True)

    secret_fingerprint = db.Column(db.String(256), nullable=False, index=True)

    is_active = db.Column(db.Boolean, nullable=False, default=True)
    rotation_in_progress = db.Column(db.Boolean, nullable=False, default=False)
    rotated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)


class SettingAuditEvent(db.Model):
    """Audit events for governance mutations."""

    __tablename__ = "setting_audit_events"

    audit_event_id = db.Column(db.String(128), primary_key=True)
    event_type = db.Column(db.String(128), nullable=False, index=True)
    scope = db.Column(db.String(64), nullable=False, index=True)
    target_ref = db.Column(db.String(256), nullable=False, index=True)
    changed_by = db.Column(db.String(128), nullable=False)
    changed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, index=True)
    summary = db.Column(db.String(512), nullable=False)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize audit event rows for API readback."""
        return {
            "audit_event_id": self.audit_event_id,
            "event_type": self.event_type,
            "scope": self.scope,
            "target_ref": self.target_ref,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "summary": self.summary,
            "metadata": self.metadata_json or {},
        }


class ReadinessGate(db.Model):
    """Canonical release readiness gate definitions and status."""

    __tablename__ = "readiness_gates"

    gate_id = db.Column(db.String(128), primary_key=True)
    gate_name = db.Column(db.String(256), nullable=False, index=True)
    owner_service = db.Column(db.String(128), nullable=False, index=True)

    status = db.Column(db.String(32), nullable=False, default="open", index=True)  # closed|partial|open
    reason = db.Column(db.Text(), nullable=False, default="")

    expected_evidence = db.Column(db.Text(), nullable=False, default="")
    actual_evidence = db.Column(db.Text(), nullable=True)
    evidence_path = db.Column(db.String(512), nullable=True)

    truth_source = db.Column(db.String(64), nullable=False, default="live_endpoint")  # live_endpoint|static_policy|file_store|database
    remediation = db.Column(db.Text(), nullable=False, default="")
    remediation_steps_json = db.Column(db.JSON, nullable=False, default=list)

    last_checked_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    checked_by = db.Column(db.String(128), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize gate row to canonical response schema."""
        return {
            "gate_id": self.gate_id,
            "gate_name": self.gate_name,
            "owner_service": self.owner_service,
            "status": self.status,
            "reason": self.reason,
            "expected_evidence": self.expected_evidence,
            "actual_evidence": self.actual_evidence,
            "evidence_path": self.evidence_path,
            "truth_source": self.truth_source,
            "remediation": self.remediation,
            "remediation_steps": self.remediation_steps_json or [],
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "checked_by": self.checked_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
