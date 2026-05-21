"""Governance runtime source segment: imports_and_defaults.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
"""Operational settings and runtime governance services."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

import httpx
from flask import current_app
from sqlalchemy import and_
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError
from story_runtime_core.adapters import MockModelAdapter, OllamaAdapter, OpenAIChatAdapter, openai_http_error_excerpt

from app.extensions import db
from app.governance.errors import GovernanceError, governance_error
from app.models import (
    AITaskRoute,
    AIModelConfig,
    AIProviderConfig,
    AIProviderCredential,
    AIUsageEvent,
    BootstrapConfig,
    BootstrapPreset,
    CostBudgetPolicy,
    CostRollup,
    ProviderHealthCheck,
    ResolvedRuntimeConfigSnapshot,
    SettingAuditEvent,
    SystemSettingRecord,
)
from app.services.activity.activity_log_service import log_activity
from app.services.governance.governance_secret_crypto_service import decrypt_secret, encrypt_secret
from app.services.story_runtime.runtime_status_semantics import STATUS_SEMANTICS


_REQUIRED_TASK_KINDS: tuple[str, ...] = (
    "narrative_live_generation",
    "narrative_preview_generation",
    "narrative_validation_semantic",
    "research_synthesis",
    "research_revision_drafting",
    "writers_room_revision_assist",
    "retrieval_embedding_generation",
    "retrieval_query_expansion",
)

_DEFAULT_PRESETS: tuple[dict, ...] = (
    {
        "preset_id": "safe_local",
        "display_name": "Local Mock Safe",
        "description": "Deterministic local mock setup with conservative defaults.",
        "generation_execution_mode": "mock_only",
        "retrieval_execution_mode": "disabled",
        "validation_execution_mode": "schema_only",
        "provider_selection_mode": "local_only",
        "default_runtime_profile": "safe_local",
        "default_provider_templates_json": [{"provider_type": "mock", "display_name": "Mock Provider", "enabled_by_default": True, "requires_secret": False}],
        "default_budget_policy_json": {"daily_limit": "0", "monthly_limit": "0", "warning_threshold_percent": 80, "hard_stop_enabled": False},
    },
    {
        "preset_id": "balanced",
        "display_name": "Local Hybrid",
        "description": "Hybrid routed setup with mock fallback and optional cloud provider.",
        "generation_execution_mode": "hybrid_routed_with_mock_fallback",
        "retrieval_execution_mode": "hybrid_dense_sparse",
        "validation_execution_mode": "schema_plus_semantic",
'''
