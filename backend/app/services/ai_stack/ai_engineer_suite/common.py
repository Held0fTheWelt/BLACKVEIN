"""Shared AI Engineer Suite service definitions."""

from __future__ import annotations

import os
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import current_app
from ai_stack import (
    LANGGRAPH_RUNTIME_EXPORT_AVAILABLE,
    RetrievalDomain,
    RetrievalRequest,
    build_runtime_retriever,
)
from ai_stack.rag.semantic_embedding import embedding_backend_probe
from app.governance.errors import governance_error
from app.services.game.game_service import GameServiceError, get_story_diagnostics, list_story_sessions
from app.services.governance.governance_runtime_service import (
    delete_scope_setting,
    evaluate_runtime_readiness,
    get_runtime_modes,
    list_audit_events,
    read_scope_settings,
    update_runtime_modes,
    update_scope_settings,
)
from app.services.story_runtime.runtime_status_semantics import STATUS_SEMANTICS
from app.services.story_runtime.world_engine_control_center_service import build_world_engine_control_center_snapshot

_RAG_STACK_LOCK = threading.Lock()
_RAG_STACK_CACHE: tuple[Path, Any, Any, Any] | None = None

_RUNTIME_CORPUS_REL = Path(".wos") / "rag" / "runtime_corpus.json"
_EMBED_NPZ_REL = Path(".wos") / "rag" / "runtime_embeddings.npz"
_EMBED_META_REL = Path(".wos") / "rag" / "runtime_embeddings.meta.json"

_RAG_ALLOWED_SETTINGS = {
    "retrieval_execution_mode",
    "embeddings_enabled",
    "retrieval_top_k",
    "retrieval_min_score",
    "retrieval_profile",
}
_ORCH_ALLOWED_SETTINGS = {
    "runtime_profile",
    "enable_corrective_feedback",
    "runtime_diagnostics_verbosity",
    "max_retry_attempts",
}
_RUNTIME_PROFILE_ALLOWED = {"safe_local", "balanced", "cost_aware", "quality_first", "custom"}
_RETRIEVAL_MODE_ALLOWED = {"disabled", "sparse_only", "hybrid_dense_sparse"}
_VERBOSITY_ALLOWED = {"operator", "detailed", "debug"}
_GENERATION_MODE_ALLOWED = {"mock_only", "hybrid_routed_with_mock_fallback", "routed_llm_slm", "ai_only"}
_VALIDATION_MODE_ALLOWED = {"schema_only", "schema_plus_semantic"}
_PROVIDER_SELECTION_ALLOWED = {"local_only", "restricted_by_route", "remote_preferred", "remote_allowed"}
_SUITE_SCOPE = "ai_engineer_suite"
_SUITE_DEFAULT_PRESET_ID = "safe_local"
_ADVANCED_SETTINGS_ALLOWED = {
    "generation_execution_mode",
    "validation_execution_mode",
    "provider_selection_mode",
    "runtime_profile",
    "retrieval_execution_mode",
    "retrieval_top_k",
    "retrieval_min_score",
    "embeddings_enabled",
    "retrieval_profile",
    "enable_corrective_feedback",
    "runtime_diagnostics_verbosity",
    "max_retry_attempts",
}
_ADVANCED_SETTINGS_SPEC = {
    "ai_runtime": {
        "generation_execution_mode": {
            "type": "enum",
            "allowed": sorted(_GENERATION_MODE_ALLOWED),
            "hot_reloadable": True,
            "support_level": "recommended",
        },
        "validation_execution_mode": {
            "type": "enum",
            "allowed": sorted(_VALIDATION_MODE_ALLOWED),
            "hot_reloadable": True,
            "support_level": "recommended",
        },
        "provider_selection_mode": {
            "type": "enum",
            "allowed": sorted(_PROVIDER_SELECTION_ALLOWED),
            "hot_reloadable": True,
            "support_level": "recommended",
        },
        "runtime_profile": {
            "type": "enum",
            "allowed": sorted(_RUNTIME_PROFILE_ALLOWED),
            "hot_reloadable": True,
            "support_level": "recommended",
        },
    },
    "retrieval": {
        "retrieval_execution_mode": {
            "type": "enum",
            "allowed": sorted(_RETRIEVAL_MODE_ALLOWED),
            "hot_reloadable": True,
            "support_level": "recommended",
        },
        "retrieval_top_k": {
            "type": "int",
            "min": 1,
            "max": 12,
            "hot_reloadable": True,
            "support_level": "recommended",
        },
        "retrieval_min_score": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "nullable": True,
            "hot_reloadable": True,
            "support_level": "recommended",
        },
        "embeddings_enabled": {
            "type": "bool",
            "hot_reloadable": True,
            "support_level": "recommended",
        },
        "retrieval_profile": {
            "type": "string",
            "min_len": 1,
            "hot_reloadable": True,
            "support_level": "safe",
        },
    },
    "orchestration": {
        "enable_corrective_feedback": {
            "type": "bool",
            "hot_reloadable": True,
            "support_level": "recommended",
        },
        "runtime_diagnostics_verbosity": {
            "type": "enum",
            "allowed": sorted(_VERBOSITY_ALLOWED),
            "hot_reloadable": True,
            "support_level": "debug",
        },
        "max_retry_attempts": {
            "type": "int",
            "min": 0,
            "max": 5,
            "hot_reloadable": True,
            "support_level": "recommended",
        },
    },
}
_RUNTIME_PRESETS = [
    {
        "preset_id": "safe_local",
        "display_name": "Safe Local Baseline",
        "category": "runtime_stack",
        "description": "Conservative local-safe preset with minimal external dependency posture.",
        "stability": "recommended",
        "is_local_only": False,
        "impact_summary": [
            "Forces mock-only generation posture.",
            "Uses disabled retrieval mode unless manually enabled.",
            "Keeps retries and diagnostics conservative.",
        ],
        "compatibility_notes": ["Best starting point after uncertainty or incident response."],
        "controlled_values": {
            "generation_execution_mode": "mock_only",
            "validation_execution_mode": "schema_only",
            "provider_selection_mode": "local_only",
            "runtime_profile": "safe_local",
            "retrieval_execution_mode": "disabled",
            "retrieval_top_k": 4,
            "retrieval_min_score": None,
            "embeddings_enabled": False,
            "retrieval_profile": "runtime_turn_support",
            "enable_corrective_feedback": True,
            "runtime_diagnostics_verbosity": "operator",
            "max_retry_attempts": 1,
        },
    },
    {
        "preset_id": "balanced",
        "display_name": "Balanced Runtime",
        "category": "runtime_stack",
        "description": "Balanced profile for mixed local/cloud posture with governed fallback.",
        "stability": "recommended",
        "is_local_only": False,
        "impact_summary": [
            "Enables hybrid retrieval.",
            "Keeps runtime profile balanced with moderate retries.",
            "Maintains corrective feedback and operator diagnostics.",
        ],
        "compatibility_notes": ["Requires provider/model/route readiness for non-mock gains."],
        "controlled_values": {
            "generation_execution_mode": "hybrid_routed_with_mock_fallback",
            "validation_execution_mode": "schema_plus_semantic",
            "provider_selection_mode": "restricted_by_route",
            "runtime_profile": "balanced",
            "retrieval_execution_mode": "hybrid_dense_sparse",
            "retrieval_top_k": 5,
            "retrieval_min_score": 0.2,
            "embeddings_enabled": True,
            "retrieval_profile": "runtime_turn_support",
            "enable_corrective_feedback": True,
            "runtime_diagnostics_verbosity": "operator",
            "max_retry_attempts": 2,
        },
    },
    {
        "preset_id": "quality_first",
        "display_name": "Quality First",
        "category": "runtime_stack",
        "description": "High-quality runtime posture with richer validation and retrieval behavior.",
        "stability": "safe",
        "is_local_only": False,
        "impact_summary": [
            "Shifts generation to routed AI mode.",
            "Keeps hybrid retrieval with stricter minimum score.",
            "Raises retries and diagnostic detail for issue triage.",
        ],
        "compatibility_notes": ["Best used only when readiness is green for non-mock routes."],
        "controlled_values": {
            "generation_execution_mode": "routed_llm_slm",
            "validation_execution_mode": "schema_plus_semantic",
            "provider_selection_mode": "remote_preferred",
            "runtime_profile": "quality_first",
            "retrieval_execution_mode": "hybrid_dense_sparse",
            "retrieval_top_k": 6,
            "retrieval_min_score": 0.3,
            "embeddings_enabled": True,
            "retrieval_profile": "runtime_turn_support",
            "enable_corrective_feedback": True,
            "runtime_diagnostics_verbosity": "detailed",
            "max_retry_attempts": 3,
        },
    },
    {
        "preset_id": "debug_trace_local",
        "display_name": "Debug Trace Local",
        "category": "runtime_stack",
        "description": "Debug-oriented preset for local troubleshooting with high diagnostics.",
        "stability": "debug",
        "is_local_only": True,
        "impact_summary": [
            "Enables verbose diagnostics and higher retries.",
            "Keeps fallback-first generation behavior.",
            "Uses hybrid retrieval while surfacing more diagnostics.",
        ],
        "compatibility_notes": [
            "Intended for troubleshooting and short-lived use.",
            "Do not treat as production-safe baseline.",
        ],
        "controlled_values": {
            "generation_execution_mode": "hybrid_routed_with_mock_fallback",
            "validation_execution_mode": "schema_plus_semantic",
            "provider_selection_mode": "local_only",
            "runtime_profile": "custom",
            "retrieval_execution_mode": "hybrid_dense_sparse",
            "retrieval_top_k": 8,
            "retrieval_min_score": 0.1,
            "embeddings_enabled": True,
            "retrieval_profile": "runtime_turn_support",
            "enable_corrective_feedback": True,
            "runtime_diagnostics_verbosity": "debug",
            "max_retry_attempts": 5,
        },
    },
]



__all__ = [name for name in globals() if not name.startswith("__")]
