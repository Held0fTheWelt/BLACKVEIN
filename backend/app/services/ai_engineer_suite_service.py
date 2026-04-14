"""Phase 2 AI Engineer Suite service layer."""

from __future__ import annotations

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
from ai_stack.semantic_embedding import embedding_backend_probe
from app.governance.errors import governance_error
from app.services.game_service import GameServiceError, get_story_diagnostics, list_story_sessions
from app.services.governance_runtime_service import (
    evaluate_runtime_readiness,
    get_runtime_modes,
    list_audit_events,
    read_scope_settings,
    update_runtime_modes,
    update_scope_settings,
)
from app.services.runtime_status_semantics import STATUS_SEMANTICS
from app.services.world_engine_control_center_service import build_world_engine_control_center_snapshot

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
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _remove_if_exists(path: Path) -> bool:
    if not path.exists():
        return False
    path.unlink()
    return True


def _build_rag_stack(*, force_corpus_rebuild: bool = False, force_dense_rebuild: bool = False, reset_cache: bool = False):
    global _RAG_STACK_CACHE
    root = _repo_root()
    corpus_path = root / _RUNTIME_CORPUS_REL
    npz_path = root / _EMBED_NPZ_REL
    meta_path = root / _EMBED_META_REL
    with _RAG_STACK_LOCK:
        if force_corpus_rebuild:
            _remove_if_exists(corpus_path)
        if force_dense_rebuild:
            _remove_if_exists(npz_path)
            _remove_if_exists(meta_path)
        if reset_cache:
            _RAG_STACK_CACHE = None
        if _RAG_STACK_CACHE is not None:
            cached_root, retriever, assembler, corpus = _RAG_STACK_CACHE
            if cached_root == root and not force_corpus_rebuild and not force_dense_rebuild:
                return retriever, assembler, corpus
        retriever, assembler, corpus = build_runtime_retriever(root)
        _RAG_STACK_CACHE = (root, retriever, assembler, corpus)
        return retriever, assembler, corpus


def _extract_values(payload: Any, key: str) -> list[Any]:
    out: list[Any] = []
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k == key:
                out.append(v)
            out.extend(_extract_values(v, key))
    elif isinstance(payload, list):
        for item in payload:
            out.extend(_extract_values(item, key))
    return out


def _extract_parser_errors(payload: Any) -> list[str]:
    out: list[str] = []
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k == "langchain_parser_error" and isinstance(v, str) and v.strip():
                out.append(v.strip())
            out.extend(_extract_parser_errors(v))
    elif isinstance(payload, list):
        for item in payload:
            out.extend(_extract_parser_errors(item))
    return out


def _validate_rag_settings_patch(payload: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(payload.keys()) - _RAG_ALLOWED_SETTINGS)
    if unknown:
        raise governance_error("setting_key_invalid", "Unsupported RAG setting keys.", 400, {"keys": unknown})
    out: dict[str, Any] = {}
    if "retrieval_execution_mode" in payload:
        mode = str(payload["retrieval_execution_mode"]).strip()
        if mode not in _RETRIEVAL_MODE_ALLOWED:
            raise governance_error("setting_value_invalid", "retrieval_execution_mode is invalid.", 400, {"value": mode})
        out["retrieval_execution_mode"] = mode
    if "embeddings_enabled" in payload:
        out["embeddings_enabled"] = bool(payload["embeddings_enabled"])
    if "retrieval_top_k" in payload:
        top_k = int(payload["retrieval_top_k"])
        if top_k < 1 or top_k > 12:
            raise governance_error("setting_value_invalid", "retrieval_top_k must be between 1 and 12.", 400, {"value": top_k})
        out["retrieval_top_k"] = top_k
    if "retrieval_min_score" in payload:
        min_score = float(payload["retrieval_min_score"])
        if min_score < 0.0 or min_score > 1.0:
            raise governance_error("setting_value_invalid", "retrieval_min_score must be between 0.0 and 1.0.", 400, {"value": min_score})
        out["retrieval_min_score"] = min_score
    if "retrieval_profile" in payload:
        profile = str(payload["retrieval_profile"]).strip()
        if not profile:
            raise governance_error("setting_value_invalid", "retrieval_profile must be non-empty.", 400, {})
        out["retrieval_profile"] = profile
    return out


def _validate_orchestration_settings_patch(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    unknown = sorted(set(payload.keys()) - _ORCH_ALLOWED_SETTINGS)
    if unknown:
        raise governance_error("setting_key_invalid", "Unsupported orchestration setting keys.", 400, {"keys": unknown})
    modes_patch: dict[str, Any] = {}
    world_engine_patch: dict[str, Any] = {}
    if "runtime_profile" in payload:
        profile = str(payload["runtime_profile"]).strip()
        if profile not in _RUNTIME_PROFILE_ALLOWED:
            raise governance_error("setting_value_invalid", "runtime_profile is invalid.", 400, {"value": profile})
        modes_patch["runtime_profile"] = profile
    if "enable_corrective_feedback" in payload:
        world_engine_patch["enable_corrective_feedback"] = bool(payload["enable_corrective_feedback"])
    if "runtime_diagnostics_verbosity" in payload:
        verbosity = str(payload["runtime_diagnostics_verbosity"]).strip()
        if verbosity not in _VERBOSITY_ALLOWED:
            raise governance_error("setting_value_invalid", "runtime_diagnostics_verbosity is invalid.", 400, {"value": verbosity})
        world_engine_patch["runtime_diagnostics_verbosity"] = verbosity
    if "max_retry_attempts" in payload:
        max_retry = int(payload["max_retry_attempts"])
        if max_retry < 0 or max_retry > 5:
            raise governance_error("setting_value_invalid", "max_retry_attempts must be between 0 and 5.", 400, {"value": max_retry})
        world_engine_patch["max_retry_attempts"] = max_retry
    return modes_patch, world_engine_patch


def _runtime_preset_map() -> dict[str, dict[str, Any]]:
    return {row["preset_id"]: row for row in _RUNTIME_PRESETS}


def _read_suite_state() -> tuple[str, dict[str, Any]]:
    state = read_scope_settings(_SUITE_SCOPE)
    preset_id = str(state.get("applied_preset_id") or _SUITE_DEFAULT_PRESET_ID).strip()
    presets = _runtime_preset_map()
    if preset_id not in presets:
        preset_id = _SUITE_DEFAULT_PRESET_ID
    overrides_raw = state.get("manual_overrides")
    overrides = overrides_raw if isinstance(overrides_raw, dict) else {}
    cleaned_overrides = {str(k): v for k, v in overrides.items() if k in _ADVANCED_SETTINGS_ALLOWED}
    return preset_id, cleaned_overrides


def _write_suite_state(*, actor: str, preset_id: str, overrides: dict[str, Any], action: str) -> None:
    update_scope_settings(
        _SUITE_SCOPE,
        {
            "applied_preset_id": preset_id,
            "manual_overrides": overrides,
            "last_action": action,
            "last_action_at": datetime.now(timezone.utc).isoformat(),
        },
        actor,
    )


def _current_advanced_settings() -> dict[str, Any]:
    runtime_modes = get_runtime_modes()
    retrieval_settings = read_scope_settings("retrieval")
    world_engine_settings = read_scope_settings("world_engine")
    return {
        "generation_execution_mode": runtime_modes.get("generation_execution_mode"),
        "validation_execution_mode": runtime_modes.get("validation_execution_mode"),
        "provider_selection_mode": runtime_modes.get("provider_selection_mode"),
        "runtime_profile": runtime_modes.get("runtime_profile"),
        "retrieval_execution_mode": runtime_modes.get("retrieval_execution_mode"),
        "retrieval_top_k": retrieval_settings.get("retrieval_top_k") or 4,
        "retrieval_min_score": retrieval_settings.get("retrieval_min_score"),
        "embeddings_enabled": retrieval_settings.get("embeddings_enabled"),
        "retrieval_profile": retrieval_settings.get("retrieval_profile") or "runtime_turn_support",
        "enable_corrective_feedback": bool(world_engine_settings.get("enable_corrective_feedback", True)),
        "runtime_diagnostics_verbosity": world_engine_settings.get("runtime_diagnostics_verbosity", "operator"),
        "max_retry_attempts": world_engine_settings.get("max_retry_attempts", 1),
    }


def _normalize_advanced_settings_patch(payload: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(payload.keys()) - _ADVANCED_SETTINGS_ALLOWED)
    if unknown:
        raise governance_error(
            "setting_key_invalid",
            "Unsupported advanced setting keys.",
            400,
            {"keys": unknown, "category": "advanced_settings"},
        )
    out: dict[str, Any] = {}
    if "generation_execution_mode" in payload:
        mode = str(payload["generation_execution_mode"]).strip()
        if mode not in _GENERATION_MODE_ALLOWED:
            raise governance_error("setting_value_invalid", "generation_execution_mode is invalid.", 400, {"value": mode})
        out["generation_execution_mode"] = mode
    if "validation_execution_mode" in payload:
        mode = str(payload["validation_execution_mode"]).strip()
        if mode not in _VALIDATION_MODE_ALLOWED:
            raise governance_error("setting_value_invalid", "validation_execution_mode is invalid.", 400, {"value": mode})
        out["validation_execution_mode"] = mode
    if "provider_selection_mode" in payload:
        mode = str(payload["provider_selection_mode"]).strip()
        if mode not in _PROVIDER_SELECTION_ALLOWED:
            raise governance_error("setting_value_invalid", "provider_selection_mode is invalid.", 400, {"value": mode})
        out["provider_selection_mode"] = mode
    if "runtime_profile" in payload:
        profile = str(payload["runtime_profile"]).strip()
        if profile not in _RUNTIME_PROFILE_ALLOWED:
            raise governance_error("setting_value_invalid", "runtime_profile is invalid.", 400, {"value": profile})
        out["runtime_profile"] = profile
    rag_payload = {k: payload[k] for k in _RAG_ALLOWED_SETTINGS if k in payload}
    orch_payload = {k: payload[k] for k in _ORCH_ALLOWED_SETTINGS if k in payload}
    out.update(_validate_rag_settings_patch(rag_payload))
    modes_patch, world_engine_patch = _validate_orchestration_settings_patch(orch_payload)
    out.update(modes_patch)
    out.update(world_engine_patch)
    return out


def _guardrail_warnings(effective: dict[str, Any]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    if (
        effective.get("generation_execution_mode") in {"ai_only", "routed_llm_slm"}
        and effective.get("runtime_profile") == "safe_local"
    ):
        warnings.append(
            {
                "code": "profile_mode_tension",
                "message": "safe_local profile with AI-only/routed generation may conflict with readiness expectations.",
                "severity": "warn",
            }
        )
    if effective.get("retrieval_execution_mode") == "disabled" and bool(effective.get("embeddings_enabled")):
        warnings.append(
            {
                "code": "retrieval_disabled_embeddings_enabled",
                "message": "Embeddings are enabled while retrieval mode is disabled.",
                "severity": "warn",
            }
        )
    if effective.get("runtime_diagnostics_verbosity") == "debug":
        warnings.append(
            {
                "code": "debug_verbosity_active",
                "message": "Debug diagnostics verbosity is active. Use for short-lived troubleshooting only.",
                "severity": "warn",
            }
        )
    if int(effective.get("max_retry_attempts") or 0) == 0 and bool(effective.get("enable_corrective_feedback")):
        warnings.append(
            {
                "code": "corrective_without_retries",
                "message": "Corrective feedback is enabled while max retries is 0.",
                "severity": "info",
            }
        )
    return warnings


def _support_level_for_key(setting_key: str) -> str:
    for section in _ADVANCED_SETTINGS_SPEC.values():
        spec = section.get(setting_key)
        if isinstance(spec, dict):
            return str(spec.get("support_level") or "recommended")
    return "recommended"


def _apply_advanced_settings(cleaned: dict[str, Any], actor: str) -> None:
    runtime_patch = {
        key: cleaned[key]
        for key in (
            "generation_execution_mode",
            "validation_execution_mode",
            "provider_selection_mode",
            "runtime_profile",
            "retrieval_execution_mode",
        )
        if key in cleaned
    }
    retrieval_patch = {
        key: cleaned[key]
        for key in ("retrieval_top_k", "retrieval_min_score", "embeddings_enabled", "retrieval_profile")
        if key in cleaned
    }
    world_engine_patch = {
        key: cleaned[key]
        for key in ("enable_corrective_feedback", "runtime_diagnostics_verbosity", "max_retry_attempts")
        if key in cleaned
    }
    if runtime_patch:
        update_runtime_modes(runtime_patch, actor)
    if retrieval_patch:
        update_scope_settings("retrieval", retrieval_patch, actor)
    if world_engine_patch:
        update_scope_settings("world_engine", world_engine_patch, actor)


def _effective_config_payload() -> dict[str, Any]:
    preset_id, overrides = _read_suite_state()
    presets = _runtime_preset_map()
    preset = presets[preset_id]
    base = dict(preset.get("controlled_values") or {})
    derived = dict(base)
    derived.update(overrides)
    actual = _current_advanced_settings()
    keys = sorted(_ADVANCED_SETTINGS_ALLOWED)
    value_sources: list[dict[str, Any]] = []
    drift: list[str] = []
    comparison_rows: list[dict[str, Any]] = []
    for key in keys:
        source = "override" if key in overrides else "preset"
        support_level = _support_level_for_key(key)
        preset_value = base.get(key)
        override_value = overrides.get(key) if key in overrides else None
        derived_value = derived.get(key)
        active_value = actual.get(key)
        value_sources.append(
            {
                "key": key,
                "source": source,
                "support_level": support_level,
                "preset_value": preset_value,
                "override_value": override_value,
                "derived_effective_value": derived_value,
                "active_value": active_value,
            }
        )
        if source == "override" or derived_value != active_value:
            comparison_rows.append(
                {
                    "key": key,
                    "support_level": support_level,
                    "source": source,
                    "preset_value": preset_value,
                    "override_value": override_value,
                    "effective_value": derived_value,
                    "active_value": active_value,
                    "drift_detected": derived_value != active_value,
                    "comparison_note": (
                        "Active runtime differs from derived effective value."
                        if derived_value != active_value
                        else "Manual override changes preset intent."
                    ),
                }
            )
        if derived_value != active_value:
            drift.append(key)
    boundedness_notes = []
    for key in keys:
        support = _support_level_for_key(key)
        if support in {"debug", "safe"}:
            boundedness_notes.append(
                {
                    "key": key,
                    "support_level": support,
                    "note": (
                        "Use this setting for short-lived troubleshooting only."
                        if support == "debug"
                        else "This setting is bounded and should be changed intentionally."
                    ),
                }
            )
    source_summary = {
        "preset_count": sum(1 for row in value_sources if row["source"] == "preset"),
        "override_count": sum(1 for row in value_sources if row["source"] == "override"),
        "drift_count": len(drift),
    }
    return {
        "active_preset_id": preset_id,
        "active_preset_display_name": preset.get("display_name"),
        "preset_summary": preset.get("description"),
        "preset_stability": preset.get("stability"),
        "overrides": overrides,
        "overrides_exist": bool(overrides),
        "override_count": len(overrides),
        "base_values": base,
        "derived_effective_values": derived,
        "active_values": actual,
        "value_sources": value_sources,
        "source_summary": source_summary,
        "comparison_rows": comparison_rows,
        "drift_keys": drift,
        "requires_refresh": False,
        "guardrail_warnings": _guardrail_warnings(derived),
        "boundedness_notes": boundedness_notes,
        "status_semantics": STATUS_SEMANTICS,
    }


def list_runtime_presets() -> dict[str, Any]:
    preset_id, _ = _read_suite_state()
    rows: list[dict[str, Any]] = []
    for row in _RUNTIME_PRESETS:
        rows.append(
            {
                "preset_id": row["preset_id"],
                "display_name": row["display_name"],
                "category": row["category"],
                "description": row["description"],
                "stability": row["stability"],
                "is_local_only": row["is_local_only"],
                "impact_summary": list(row["impact_summary"]),
                "compatibility_notes": list(row["compatibility_notes"]),
                "controlled_values": dict(row["controlled_values"]),
                "is_active": row["preset_id"] == preset_id,
            }
        )
    return {"active_preset_id": preset_id, "presets": rows}


def apply_runtime_preset(preset_id: str, actor: str, *, keep_overrides: bool = False) -> dict[str, Any]:
    presets = _runtime_preset_map()
    normalized = (preset_id or "").strip()
    preset = presets.get(normalized)
    if preset is None:
        raise governance_error("preset_not_found", "Requested runtime preset does not exist.", 404, {"preset_id": normalized})
    _, existing_overrides = _read_suite_state()
    overrides = dict(existing_overrides) if keep_overrides else {}
    target_values = dict(preset["controlled_values"])
    target_values.update(overrides)
    cleaned = _normalize_advanced_settings_patch(target_values)
    _apply_advanced_settings(cleaned, actor)
    normalized_overrides = {
        key: value for key, value in overrides.items() if preset["controlled_values"].get(key) != value
    }
    _write_suite_state(actor=actor, preset_id=normalized, overrides=normalized_overrides, action="preset_applied")
    return {
        "applied_preset_id": normalized,
        "kept_overrides": bool(keep_overrides),
        "operator_message": f"Preset '{normalized}' applied.",
        "effective_config": _effective_config_payload(),
    }


def get_advanced_settings() -> dict[str, Any]:
    return {
        "settings": _current_advanced_settings(),
        "categories": _ADVANCED_SETTINGS_SPEC,
        "effective_config": _effective_config_payload(),
    }


def update_advanced_settings(payload: dict[str, Any], actor: str) -> dict[str, Any]:
    cleaned = _normalize_advanced_settings_patch(payload)
    if not cleaned:
        return get_advanced_settings()
    preset_id, existing_overrides = _read_suite_state()
    preset = _runtime_preset_map()[preset_id]
    merged_overrides = dict(existing_overrides)
    merged_overrides.update(cleaned)
    _apply_advanced_settings(cleaned, actor)
    normalized_overrides = {
        key: value for key, value in merged_overrides.items() if preset["controlled_values"].get(key) != value
    }
    _write_suite_state(actor=actor, preset_id=preset_id, overrides=normalized_overrides, action="advanced_settings_updated")
    return get_advanced_settings()


def reset_advanced_overrides(actor: str) -> dict[str, Any]:
    preset_id, _ = _read_suite_state()
    preset = _runtime_preset_map()[preset_id]
    cleaned = _normalize_advanced_settings_patch(dict(preset["controlled_values"]))
    _apply_advanced_settings(cleaned, actor)
    _write_suite_state(actor=actor, preset_id=preset_id, overrides={}, action="advanced_settings_reset")
    return {
        "operator_message": f"Overrides cleared and preset '{preset_id}' re-applied.",
        "effective_config": _effective_config_payload(),
    }


def get_effective_runtime_config() -> dict[str, Any]:
    payload = _effective_config_payload()
    payload["advanced_settings_spec"] = _ADVANCED_SETTINGS_SPEC
    return payload


def list_settings_changes(*, limit: int = 25) -> dict[str, Any]:
    rows = list_audit_events(limit=max(limit * 3, 50))
    relevant_scopes = {"ai_runtime", "retrieval", "world_engine", _SUITE_SCOPE}
    filtered: list[dict[str, Any]] = []
    for row in rows:
        scope = str(row.get("scope") or "")
        if scope not in relevant_scopes:
            continue
        filtered.append(
            {
                "changed_at": row.get("changed_at"),
                "changed_by": row.get("changed_by"),
                "scope": scope,
                "target_ref": row.get("target_ref"),
                "event_type": row.get("event_type"),
                "summary": row.get("summary"),
                "metadata": row.get("metadata"),
            }
        )
        if len(filtered) >= limit:
            break
    return {"items": filtered, "total_returned": len(filtered)}


def get_rag_operations_status() -> dict[str, Any]:
    retriever, _, corpus = _build_rag_stack()
    probe = embedding_backend_probe()
    runtime_modes = get_runtime_modes()
    retrieval_settings = read_scope_settings("retrieval")
    class_counts = Counter(chunk.content_class.value for chunk in corpus.chunks)
    source_paths = sorted({chunk.source_path for chunk in corpus.chunks})
    root = _repo_root()
    corpus_path = root / _RUNTIME_CORPUS_REL
    npz_path = root / _EMBED_NPZ_REL
    meta_path = root / _EMBED_META_REL
    degraded_reasons: list[str] = []
    if not probe.available:
        degraded_reasons.extend(list(probe.messages))
    degraded_reasons.extend(list(corpus.rag_dense_load_reason_codes or ()))
    if corpus.rag_dense_rebuild_reason:
        degraded_reasons.append(corpus.rag_dense_rebuild_reason)
    mode_runtime = runtime_modes.get("retrieval_execution_mode")
    operational_state = "healthy"
    if mode_runtime == "disabled":
        operational_state = "configured_disabled"
    elif len(corpus.chunks) == 0:
        operational_state = "blocked"
    elif degraded_reasons:
        operational_state = "degraded"
    guidance: list[dict[str, str]] = []
    if operational_state == "blocked":
        guidance.append(
            {
                "severity": "blocked",
                "message": "RAG corpus has no chunks, so retrieval cannot produce useful context.",
                "consequence": "AI responses lose retrieval-backed grounding.",
                "next_step": "Run 'Refresh corpus' and re-run a retrieval probe.",
                "fix_path": "/manage/rag-operations",
            }
        )
    if mode_runtime == "disabled":
        guidance.append(
            {
                "severity": "info",
                "message": "Retrieval mode is intentionally disabled by configuration.",
                "consequence": "Runtime relies on non-retrieval behavior.",
                "next_step": "Enable retrieval mode in Runtime Settings or RAG settings when needed.",
                "fix_path": "/manage/runtime-settings",
            }
        )
    if not probe.available and mode_runtime != "disabled":
        guidance.append(
            {
                "severity": "degraded",
                "message": "Embedding backend is unavailable while retrieval mode expects dense support.",
                "consequence": "Retrieval can fall back to sparse-only posture with lower recall quality.",
                "next_step": "Inspect embedding diagnostics and rerun probe to validate fallback quality.",
                "fix_path": "/manage/rag-operations",
            }
        )
    return {
        "generated_at": corpus.built_at,
        "operational_state": operational_state,
        "status_semantics": STATUS_SEMANTICS,
        "corpus": {
            "chunk_count": len(corpus.chunks),
            "source_count": corpus.source_count,
            "content_class_counts": dict(class_counts),
            "sample_source_paths": source_paths[:10],
            "corpus_fingerprint": corpus.corpus_fingerprint,
            "index_version": corpus.index_version,
            "storage_path": corpus.storage_path or str(corpus_path),
            "built_at": corpus.built_at,
        },
        "retrieval": {
            "mode_runtime": runtime_modes.get("retrieval_execution_mode"),
            "mode_setting": retrieval_settings.get("retrieval_execution_mode"),
            "retrieval_profile": retrieval_settings.get("retrieval_profile") or "runtime_turn_support",
            "retrieval_top_k": retrieval_settings.get("retrieval_top_k") or 4,
            "retrieval_min_score": retrieval_settings.get("retrieval_min_score"),
            "embeddings_enabled_setting": retrieval_settings.get("embeddings_enabled"),
        },
        "embedding_backend": {
            "available": probe.available,
            "disabled_by_env": probe.disabled_by_env,
            "import_ok": probe.import_ok,
            "encode_ok": probe.encode_ok,
            "model_id": probe.model_id,
            "cache_dir": probe.cache_dir,
            "cache_dir_identity": probe.cache_dir_identity,
            "primary_reason_code": probe.primary_reason_code,
            "messages": list(probe.messages),
        },
        "dense_index": {
            "present_on_retriever": bool(getattr(retriever, "_embedding_index", None) is not None),
            "artifact_validity": corpus.rag_dense_artifact_validity,
            "index_build_action": corpus.rag_dense_index_build_action,
            "rebuild_reason": corpus.rag_dense_rebuild_reason,
            "load_reason_codes": list(corpus.rag_dense_load_reason_codes or ()),
            "embedding_index_version": corpus.rag_embedding_index_version,
            "embedding_cache_dir_identity": corpus.rag_embedding_cache_dir_identity,
            "embedding_backend_primary_code": corpus.rag_embedding_backend_primary_code,
            "npz_path": str(npz_path),
            "npz_exists": npz_path.exists(),
            "meta_path": str(meta_path),
            "meta_exists": meta_path.exists(),
        },
        "degraded_reasons": sorted(set(r for r in degraded_reasons if r)),
        "comparison": {
            "retrieval_mode_runtime": mode_runtime,
            "retrieval_mode_setting": retrieval_settings.get("retrieval_execution_mode"),
            "dense_index_attached": bool(getattr(retriever, "_embedding_index", None) is not None),
            "expected_healthy": {
                "embedding_backend_available": True,
                "dense_index_attached": True,
                "retrieval_mode_not_disabled": True,
            },
        },
        "guidance": guidance,
        "safe_actions": [
            {"action_id": "refresh_corpus", "label": "Refresh corpus from repository sources"},
            {"action_id": "rebuild_dense_index", "label": "Rebuild dense embedding index"},
            {"action_id": "reload_runtime_retriever", "label": "Reload in-process retriever"},
        ],
    }


def run_rag_query_probe(payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    if not query:
        raise governance_error("setting_value_invalid", "query is required.", 400, {})
    retrieval_settings = read_scope_settings("retrieval")
    requested_max = int(payload.get("max_chunks") or retrieval_settings.get("retrieval_top_k") or 4)
    max_chunks = max(1, min(requested_max, 12))
    mode_setting = str(retrieval_settings.get("retrieval_execution_mode") or "").strip().lower()
    use_sparse_only = bool(payload.get("use_sparse_only")) or mode_setting == "sparse_only"
    domain_raw = str(payload.get("domain") or RetrievalDomain.RUNTIME.value).strip().lower()
    try:
        domain = RetrievalDomain(domain_raw)
    except ValueError:
        raise governance_error("setting_value_invalid", "Unsupported probe domain.", 400, {"domain": domain_raw})
    retriever, _, _ = _build_rag_stack()
    request = RetrievalRequest(
        domain=domain,
        profile=str(payload.get("profile") or retrieval_settings.get("retrieval_profile") or "runtime_turn_support"),
        query=query,
        module_id=str(payload.get("module_id") or "").strip() or None,
        scene_id=str(payload.get("scene_id") or "").strip() or None,
        max_chunks=max_chunks,
        use_sparse_only=use_sparse_only,
    )
    result = retriever.retrieve(request)
    hits = []
    for hit in result.hits:
        hits.append(
            {
                "chunk_id": hit.chunk_id,
                "source_path": hit.source_path,
                "source_name": hit.source_name,
                "content_class": hit.content_class,
                "score": hit.score,
                "snippet": hit.snippet,
                "selection_reason": hit.selection_reason,
                "pack_role": hit.pack_role,
                "source_evidence_lane": hit.source_evidence_lane,
                "source_visibility_class": hit.source_visibility_class,
                "policy_note": hit.policy_note,
                "profile_policy_influence": hit.profile_policy_influence,
            }
        )
    return {
        "request": {
            "domain": request.domain.value,
            "profile": request.profile,
            "query": request.query,
            "module_id": request.module_id,
            "scene_id": request.scene_id,
            "max_chunks": request.max_chunks,
            "use_sparse_only": request.use_sparse_only,
        },
        "result": {
            "status": result.status.value,
            "hit_count": len(result.hits),
            "retrieval_route": result.retrieval_route,
            "embedding_model_id": result.embedding_model_id,
            "degradation_mode": result.degradation_mode,
            "dense_index_build_action": result.dense_index_build_action,
            "dense_rebuild_reason": result.dense_rebuild_reason,
            "dense_artifact_validity": result.dense_artifact_validity,
            "ranking_notes": list(result.ranking_notes),
            "embedding_reason_codes": list(result.embedding_reason_codes),
            "index_version": result.index_version,
            "corpus_fingerprint": result.corpus_fingerprint,
            "storage_path": result.storage_path,
            "hits": hits,
        },
    }


def run_rag_safe_action(action_id: str) -> dict[str, Any]:
    normalized = (action_id or "").strip().lower()
    root = _repo_root()
    corpus_path = root / _RUNTIME_CORPUS_REL
    npz_path = root / _EMBED_NPZ_REL
    meta_path = root / _EMBED_META_REL
    if normalized == "refresh_corpus":
        _build_rag_stack(force_corpus_rebuild=True, force_dense_rebuild=True, reset_cache=True)
        return {
            "action_id": normalized,
            "performed": True,
            "operator_message": "Runtime corpus and dense index were rebuilt from repository sources.",
            "paths_touched": [str(corpus_path), str(npz_path), str(meta_path)],
            "status": get_rag_operations_status(),
        }
    if normalized == "rebuild_dense_index":
        _build_rag_stack(force_dense_rebuild=True, reset_cache=True)
        return {
            "action_id": normalized,
            "performed": True,
            "operator_message": "Dense embedding index rebuild was requested and applied.",
            "paths_touched": [str(npz_path), str(meta_path)],
            "status": get_rag_operations_status(),
        }
    if normalized == "reload_runtime_retriever":
        _build_rag_stack(reset_cache=True)
        return {
            "action_id": normalized,
            "performed": True,
            "operator_message": "In-process runtime retriever cache reloaded.",
            "paths_touched": [],
            "status": get_rag_operations_status(),
        }
    raise governance_error("setting_value_invalid", "Unsupported RAG action.", 400, {"action_id": normalized})


def get_rag_settings() -> dict[str, Any]:
    runtime_modes = get_runtime_modes()
    retrieval_settings = read_scope_settings("retrieval")
    return {
        "retrieval_execution_mode": retrieval_settings.get("retrieval_execution_mode")
        or runtime_modes.get("retrieval_execution_mode"),
        "embeddings_enabled": retrieval_settings.get("embeddings_enabled"),
        "retrieval_top_k": retrieval_settings.get("retrieval_top_k") or 4,
        "retrieval_min_score": retrieval_settings.get("retrieval_min_score"),
        "retrieval_profile": retrieval_settings.get("retrieval_profile") or "runtime_turn_support",
    }


def update_rag_settings(payload: dict[str, Any], actor: str) -> dict[str, Any]:
    cleaned = _validate_rag_settings_patch(payload)
    if not cleaned:
        return get_rag_settings()
    runtime_patch: dict[str, Any] = {}
    if "retrieval_execution_mode" in cleaned:
        runtime_patch["retrieval_execution_mode"] = cleaned["retrieval_execution_mode"]
    if runtime_patch:
        update_runtime_modes(runtime_patch, actor)
    persisted = {k: v for k, v in cleaned.items() if k != "retrieval_execution_mode"}
    if persisted:
        update_scope_settings("retrieval", persisted, actor)
    return get_rag_settings()


def get_orchestration_status(*, trace_id: str | None = None) -> dict[str, Any]:
    runtime_modes = get_runtime_modes()
    world_engine_settings = read_scope_settings("world_engine")
    langgraph_dependency_available = bool(LANGGRAPH_RUNTIME_EXPORT_AVAILABLE)
    langgraph_import_error: str | None = None
    if not langgraph_dependency_available:
        try:
            from ai_stack.langgraph_runtime import ensure_langgraph_available

            ensure_langgraph_available()
            langgraph_dependency_available = True
        except Exception as exc:  # pragma: no cover - environment dependent
            langgraph_import_error = str(exc)
    bridge_available = True
    bridge_error: str | None = None
    parser_schema_health = {"runtime_structured_output": True, "writers_room_structured_output": True}
    try:
        from ai_stack.langchain_integration import RuntimeTurnStructuredOutput, WritersRoomStructuredOutput

        RuntimeTurnStructuredOutput.model_validate_json('{"narrative_response":"ok"}')
        WritersRoomStructuredOutput.model_validate_json('{"review_notes":"ok","recommendations":[]}')
    except Exception as exc:  # pragma: no cover - dependency/runtime dependent
        bridge_available = False
        bridge_error = str(exc)
        parser_schema_health = {"runtime_structured_output": False, "writers_room_structured_output": False}

    session_items: list[dict[str, Any]] = []
    diagnostics_errors: list[dict[str, Any]] = []
    graph_error_count = 0
    fallback_marker_count = 0
    parser_error_count = 0
    node_counter: Counter[str] = Counter()
    try:
        sessions_payload = list_story_sessions(trace_id=trace_id)
        for row in list(sessions_payload.get("items") or [])[:3]:
            if not isinstance(row, dict):
                continue
            session_id = str(row.get("session_id") or "").strip()
            if not session_id:
                continue
            try:
                diag = get_story_diagnostics(session_id, trace_id=trace_id)
                session_items.append({"session_id": session_id, "diagnostics": diag})
                for nodes in _extract_values(diag, "nodes_executed"):
                    if isinstance(nodes, list):
                        for node_name in nodes:
                            if isinstance(node_name, str) and node_name:
                                node_counter[node_name] += 1
                for errs in _extract_values(diag, "graph_errors"):
                    if isinstance(errs, list):
                        graph_error_count += len(errs)
                for marks in _extract_values(diag, "fallback_markers"):
                    if isinstance(marks, list):
                        fallback_marker_count += len(marks)
                parser_error_count += len(_extract_parser_errors(diag))
            except GameServiceError as exc:
                diagnostics_errors.append({"session_id": session_id, "message": str(exc), "status_code": exc.status_code})
    except GameServiceError as exc:
        diagnostics_errors.append({"session_id": None, "message": str(exc), "status_code": exc.status_code})
    langgraph_state = "healthy"
    if not langgraph_dependency_available:
        langgraph_state = "blocked"
    elif graph_error_count > 0 or fallback_marker_count > 0 or diagnostics_errors:
        langgraph_state = "degraded"
    langchain_state = "healthy"
    if not bridge_available:
        langchain_state = "blocked"
    elif parser_error_count > 0:
        langchain_state = "degraded"
    overall_state = "healthy"
    if "blocked" in {langgraph_state, langchain_state}:
        overall_state = "blocked"
    elif "degraded" in {langgraph_state, langchain_state}:
        overall_state = "degraded"
    guidance: list[dict[str, str]] = []
    if not langgraph_dependency_available:
        guidance.append(
            {
                "severity": "blocked",
                "message": "LangGraph dependency/runtime export is unavailable.",
                "consequence": "Primary graph execution cannot run as expected.",
                "next_step": "Review orchestration diagnostics and fallback posture before enabling strict runtime paths.",
                "fix_path": "/manage/ai-orchestration",
            }
        )
    if parser_error_count > 0:
        guidance.append(
            {
                "severity": "degraded",
                "message": "Recent parser/schema failures were observed.",
                "consequence": "Structured orchestration output reliability is reduced.",
                "next_step": "Keep corrective feedback enabled and inspect recent diagnostics errors.",
                "fix_path": "/manage/ai-orchestration",
            }
        )
    if str(world_engine_settings.get("runtime_diagnostics_verbosity", "operator")) == "debug":
        guidance.append(
            {
                "severity": "info",
                "message": "Diagnostics verbosity is set to debug (bounded debug-only posture).",
                "consequence": "Operator output can become noisy during normal operation.",
                "next_step": "Return to operator or detailed verbosity when troubleshooting is complete.",
                "fix_path": "/manage/runtime-settings",
            }
        )

    return {
        "overall_state": overall_state,
        "status_semantics": STATUS_SEMANTICS,
        "langgraph": {
            "state": langgraph_state,
            "dependency_available": langgraph_dependency_available,
            "import_error": langgraph_import_error,
            "runtime_profile": runtime_modes.get("runtime_profile"),
            "validation_execution_mode": runtime_modes.get("validation_execution_mode"),
            "max_retry_attempts": world_engine_settings.get("max_retry_attempts", 1),
            "enable_corrective_feedback": bool(world_engine_settings.get("enable_corrective_feedback", True)),
            "runtime_diagnostics_verbosity": world_engine_settings.get("runtime_diagnostics_verbosity", "operator"),
            "fallback_posture": {
                "fallback_marker_count_recent": fallback_marker_count,
                "graph_error_count_recent": graph_error_count,
            },
            "recent_execution_summary": {
                "sessions_sampled": len(session_items),
                "top_nodes_executed": node_counter.most_common(8),
                "diagnostics_errors": diagnostics_errors,
            },
        },
        "langchain": {
            "state": langchain_state,
            "bridge_available": bridge_available,
            "bridge_error": bridge_error,
            "runtime_adapter_bridge_available": bridge_available,
            "retriever_bridge_available": bridge_available,
            "writers_room_bridge_available": bridge_available,
            "tool_bridge_available": bridge_available,
            "parser_schema_health": parser_schema_health,
            "recent_parser_failure_count": parser_error_count,
        },
        "controls": {
            "allowed_runtime_profiles": sorted(_RUNTIME_PROFILE_ALLOWED),
            "allowed_runtime_diagnostics_verbosity": sorted(_VERBOSITY_ALLOWED),
            "max_retry_attempts_range": {"min": 0, "max": 5},
        },
        "comparison": {
            "expected_healthy": {
                "langgraph_dependency_available": True,
                "langchain_bridge_available": True,
                "recent_graph_errors": 0,
                "recent_parser_failures": 0,
            },
            "active": {
                "runtime_profile": runtime_modes.get("runtime_profile"),
                "runtime_diagnostics_verbosity": world_engine_settings.get("runtime_diagnostics_verbosity", "operator"),
                "max_retry_attempts": world_engine_settings.get("max_retry_attempts", 1),
                "recent_graph_errors": graph_error_count,
                "recent_parser_failures": parser_error_count,
            },
        },
        "guidance": guidance,
    }


def get_orchestration_settings() -> dict[str, Any]:
    runtime_modes = get_runtime_modes()
    world_engine_settings = read_scope_settings("world_engine")
    return {
        "runtime_profile": runtime_modes.get("runtime_profile"),
        "enable_corrective_feedback": bool(world_engine_settings.get("enable_corrective_feedback", True)),
        "runtime_diagnostics_verbosity": world_engine_settings.get("runtime_diagnostics_verbosity", "operator"),
        "max_retry_attempts": world_engine_settings.get("max_retry_attempts", 1),
    }


def update_orchestration_settings(payload: dict[str, Any], actor: str) -> dict[str, Any]:
    modes_patch, world_engine_patch = _validate_orchestration_settings_patch(payload)
    if modes_patch:
        update_runtime_modes(modes_patch, actor)
    if world_engine_patch:
        update_scope_settings("world_engine", world_engine_patch, actor)
    return get_orchestration_settings()


def get_runtime_dashboard(*, trace_id: str | None = None) -> dict[str, Any]:
    governance = evaluate_runtime_readiness()
    rag = get_rag_operations_status()
    orchestration = get_orchestration_status(trace_id=trace_id)
    world_engine = build_world_engine_control_center_snapshot(current_app._get_current_object(), trace_id=trace_id)
    blockers: list[dict[str, str]] = []
    if not governance.get("ai_only_valid"):
        blockers.append({"domain": "governance", "message": governance.get("readiness_headline") or "Governance readiness is blocked."})
    if str(rag.get("operational_state")) == "blocked":
        blockers.append({"domain": "rag", "message": "RAG is blocked and cannot provide runtime retrieval context."})
    langgraph = orchestration.get("langgraph") or {}
    if str(orchestration.get("overall_state")) == "blocked" or not langgraph.get("dependency_available"):
        blockers.append({"domain": "orchestration", "message": "LangGraph runtime dependency is unavailable."})
    if (world_engine.get("status") or {}).get("control_plane_ok") is False:
        blockers.append({"domain": "world_engine", "message": "World-engine control plane has blocking posture issues."})
    effective = _effective_config_payload()
    governance_state = str(governance.get("readiness_severity") or "unknown")
    if governance_state not in {"healthy", "degraded", "blocked", "configured_disabled", "unknown"}:
        governance_state = "unknown"
    rag_state = str(rag.get("operational_state") or "unknown")
    orchestration_state = str(orchestration.get("overall_state") or "unknown")
    world_status = world_engine.get("status") or {}
    world_state = "healthy"
    if world_status.get("control_plane_ok") is False:
        world_state = "blocked"
    elif int(world_status.get("warning_count") or 0) > 0:
        world_state = "degraded"
    domain_status = [
        {
            "domain": "governance",
            "state": governance_state,
            "consequence": "Provider/model/route readiness determines AI-only runtime validity.",
            "fix_path": "/manage/ai-runtime-governance",
        },
        {
            "domain": "runtime_settings",
            "state": (
                "degraded"
                if (effective.get("guardrail_warnings") or []) or (effective.get("drift_keys") or [])
                else "healthy"
            ),
            "consequence": "Preset intent can diverge when manual overrides are active.",
            "fix_path": "/manage/runtime-settings",
        },
        {
            "domain": "rag",
            "state": rag_state,
            "consequence": "Retrieval degradation can lower grounding quality.",
            "fix_path": "/manage/rag-operations",
        },
        {
            "domain": "orchestration",
            "state": orchestration_state,
            "consequence": "Orchestration degradation affects runtime traceability and structured output reliability.",
            "fix_path": "/manage/ai-orchestration",
        },
        {
            "domain": "world_engine",
            "state": world_state,
            "consequence": "Control-plane mismatch can block run/session operations.",
            "fix_path": "/manage/world-engine-control-center",
        },
    ]
    degraded_or_warning: list[dict[str, str]] = []
    for row in rag.get("guidance") or []:
        if str(row.get("severity")) in {"degraded", "warn", "info"}:
            degraded_or_warning.append({"domain": "rag", "message": str(row.get("message") or "")})
    for row in orchestration.get("guidance") or []:
        if str(row.get("severity")) in {"degraded", "warn", "info"}:
            degraded_or_warning.append({"domain": "orchestration", "message": str(row.get("message") or "")})
    if int(world_status.get("warning_count") or 0) > 0:
        degraded_or_warning.append(
            {
                "domain": "world_engine",
                "message": "World-engine snapshot includes warnings; inspect control-center warning rows.",
            }
        )
    return {
        "summary": {
            "provider_readiness": governance.get("provider_summary", {}),
            "model_route_readiness": governance.get("route_summary", {}),
            "ai_only_valid": bool(governance.get("ai_only_valid")),
            "rag": {
                "chunk_count": (rag.get("corpus") or {}).get("chunk_count", 0),
                "embedding_backend_available": (rag.get("embedding_backend") or {}).get("available", False),
                "dense_artifact_validity": (rag.get("dense_index") or {}).get("artifact_validity"),
            },
            "orchestration": {
                "langgraph_dependency_available": bool((orchestration.get("langgraph") or {}).get("dependency_available")),
                "langchain_bridge_available": bool((orchestration.get("langchain") or {}).get("bridge_available")),
                "recent_graph_errors": (orchestration.get("langgraph") or {}).get("fallback_posture", {}).get("graph_error_count_recent", 0),
            },
            "world_engine": world_engine.get("status", {}),
            "active_runtime": world_engine.get("active_runtime", {}),
            "settings_layer": {
                "active_preset_id": effective.get("active_preset_id"),
                "override_count": effective.get("override_count", 0),
                "drift_key_count": len(effective.get("drift_keys") or []),
                "guardrail_warning_count": len(effective.get("guardrail_warnings") or []),
            },
        },
        "status_semantics": STATUS_SEMANTICS,
        "domain_status": domain_status,
        "blockers": blockers,
        "degraded_or_warning": degraded_or_warning,
        "next_actions": [
            "Use AI Runtime Governance to clear provider/model/route blockers.",
            "Use RAG Operations query probe to validate retrieval quality and route.",
            "Use AI Orchestration to inspect LangGraph/LangChain runtime posture.",
            "Use World-Engine Control Center for play-service control-plane fixes.",
        ],
        "links": [
            {"label": "AI Runtime Governance", "path": "/manage/ai-runtime-governance"},
            {"label": "World-Engine Control Center", "path": "/manage/world-engine-control-center"},
            {"label": "RAG Operations", "path": "/manage/rag-operations"},
            {"label": "AI Orchestration", "path": "/manage/ai-orchestration"},
            {"label": "Runtime Settings", "path": "/manage/runtime-settings"},
        ],
    }
