"""Runtime preset, advanced settings, and change history service functions."""

from __future__ import annotations

from .common import *
from .settings_validation import *

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


__all__ = (
    '_runtime_preset_map',
    '_read_suite_state',
    '_write_suite_state',
    '_current_advanced_settings',
    '_normalize_advanced_settings_patch',
    '_guardrail_warnings',
    '_support_level_for_key',
    '_apply_advanced_settings',
    '_effective_config_payload',
    'list_runtime_presets',
    'apply_runtime_preset',
    'get_advanced_settings',
    'update_advanced_settings',
    'reset_advanced_overrides',
    'get_effective_runtime_config',
    'list_settings_changes',
)
