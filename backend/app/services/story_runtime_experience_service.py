"""Backend service for the Story Runtime Experience governed settings section.

Persists settings on the ``story_runtime_experience`` scope (same mechanism
used for other governed scopes), exposes them through resolved runtime config,
and provides operator-truth snapshots for the Administration Tool.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ai_stack.story_runtime_experience import (
    canonical_defaults,
    normalize_story_runtime_experience,
    resolve_story_runtime_experience_policy,
    validate_story_runtime_experience,
)

from app.extensions import db
from app.governance.errors import governance_error
from app.models import SettingAuditEvent, SystemSettingRecord


STORY_RUNTIME_EXPERIENCE_SCOPE = "story_runtime_experience"
_SETTING_KEY = "settings_json"
_SETTING_ID = f"{STORY_RUNTIME_EXPERIENCE_SCOPE}_{_SETTING_KEY}"


def _audit(event_type: str, actor: str, summary: str, metadata: dict | None = None) -> None:
    db.session.add(
        SettingAuditEvent(
            audit_event_id=f"sre_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            event_type=event_type,
            scope=STORY_RUNTIME_EXPERIENCE_SCOPE,
            target_ref=_SETTING_ID,
            changed_by=actor,
            summary=summary[:512],
            metadata_json=metadata or {},
        )
    )


def _load_row() -> SystemSettingRecord | None:
    return db.session.get(SystemSettingRecord, _SETTING_ID)


def seed_default_story_runtime_experience(actor: str = "system") -> dict[str, Any]:
    """Idempotently seed the default Story Runtime Experience settings row.

    Called from the governance baseline so fresh ``docker-up.py`` boots arrive
    with a working default configuration and no manual admin step.
    """
    row = _load_row()
    defaults = canonical_defaults()
    if row is None:
        row = SystemSettingRecord(
            setting_id=_SETTING_ID,
            scope=STORY_RUNTIME_EXPERIENCE_SCOPE,
            setting_key=_SETTING_KEY,
            setting_value_json=defaults,
            is_secret_backed=False,
            is_user_visible=True,
            updated_by=actor,
        )
        db.session.add(row)
        _audit(
            "story_runtime_experience_seeded",
            actor,
            "Default Story Runtime Experience settings seeded.",
            {"defaults": defaults},
        )
    return dict(row.setting_value_json or defaults)


def get_story_runtime_experience_settings() -> dict[str, Any]:
    """Return the persisted, normalized settings (seeding defaults if absent)."""
    row = _load_row()
    if row is None:
        # Read-only path: do not write from a GET; return canonical defaults.
        return canonical_defaults()
    return normalize_story_runtime_experience(row.setting_value_json or {})


def update_story_runtime_experience_settings(
    payload: dict[str, Any], actor: str
) -> dict[str, Any]:
    """Validate, normalize, and persist operator-provided settings.

    Raises a governance error when the payload is not a dict. Warnings (e.g.
    misleading combinations) are returned in the response instead of blocking
    the update — the operator may choose to run in a visibly degraded mode.
    """
    if not isinstance(payload, dict):
        raise governance_error(
            "setting_value_invalid",
            "Story runtime experience payload must be a JSON object.",
            400,
            {},
        )
    normalized = normalize_story_runtime_experience(payload)
    warnings = validate_story_runtime_experience(normalized)

    row = _load_row()
    if row is None:
        row = SystemSettingRecord(
            setting_id=_SETTING_ID,
            scope=STORY_RUNTIME_EXPERIENCE_SCOPE,
            setting_key=_SETTING_KEY,
            setting_value_json=normalized,
            is_secret_backed=False,
            is_user_visible=True,
            updated_by=actor,
        )
        db.session.add(row)
    else:
        row.setting_value_json = normalized
        row.updated_by = actor
        row.updated_at = datetime.now(timezone.utc)
    _audit(
        "story_runtime_experience_updated",
        actor,
        "Story Runtime Experience settings updated.",
        {"warnings": warnings, "experience_mode": normalized.get("experience_mode")},
    )
    db.session.commit()
    return {"settings": normalized, "warnings": warnings}


def build_story_runtime_experience_truth_surface() -> dict[str, Any]:
    """Operator-facing truth surface — configured vs effective + degradations.

    The Administration Tool must display this rather than just the configured
    row so the UI cannot claim a mode is fully active when the runtime caps it.
    """
    settings = get_story_runtime_experience_settings()
    policy = resolve_story_runtime_experience_policy(settings)
    warnings = validate_story_runtime_experience(settings)
    return {
        "configured": policy.configured,
        "effective": policy.effective,
        "degradation_markers": [dict(m) for m in policy.degradation_markers],
        "packaging_contract_version": policy.packaging_contract_version,
        "config_version": policy.config_version,
        "validation_warnings": warnings,
        "experience_mode_honored_fully": not policy.degradation_markers,
    }


def serialize_for_resolved_runtime_config() -> dict[str, Any]:
    """Shape that will be embedded in ``build_resolved_runtime_config``.

    Intentionally carries both configured and effective values so the
    world-engine can honor the caps without re-resolving validation rules,
    and so the admin UI can show both sides of the truth.
    """
    return build_story_runtime_experience_truth_surface()


__all__ = [
    "STORY_RUNTIME_EXPERIENCE_SCOPE",
    "seed_default_story_runtime_experience",
    "get_story_runtime_experience_settings",
    "update_story_runtime_experience_settings",
    "build_story_runtime_experience_truth_surface",
    "serialize_for_resolved_runtime_config",
]
