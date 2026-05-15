"""Bounded branch timeline contract helpers.

The branch timeline is durable operator evidence for branch-tree lifecycle
events. It records what happened around simulated trees and selections without
becoming canonical story truth itself.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


BRANCHING_TIMELINE_RECORD_SCHEMA_VERSION = "branch_timeline_record.v1"
BRANCHING_TIMELINE_EVENT_SCHEMA_VERSION = "branch_timeline_event.v1"
BRANCHING_TIMELINE_SNAPSHOT_SCHEMA_VERSION = "branch_timeline_snapshot.v1"
BRANCHING_TIMELINE_RECORD_SOURCE = "world_engine_branch_timeline_store"

BRANCHING_TIMELINE_SCOPE_ACTIVE = "active"
BRANCHING_TIMELINE_SCOPE_PREVIEW = "preview"
BRANCHING_TIMELINE_SCOPES = (
    BRANCHING_TIMELINE_SCOPE_ACTIVE,
    BRANCHING_TIMELINE_SCOPE_PREVIEW,
)

BRANCHING_TIMELINE_STATUS_ACTIVE = "active"
BRANCHING_TIMELINE_STATUS_ARCHIVED = "archived"
BRANCHING_TIMELINE_STATUSES = (
    BRANCHING_TIMELINE_STATUS_ACTIVE,
    BRANCHING_TIMELINE_STATUS_ARCHIVED,
)

BRANCHING_TIMELINE_EVENT_TREE_CREATED = "tree_created"
BRANCHING_TIMELINE_EVENT_TREE_BECAME_STALE = "tree_became_stale"
BRANCHING_TIMELINE_EVENT_TREE_EXPIRED = "tree_expired"
BRANCHING_TIMELINE_EVENT_NODE_SELECTED = "node_selected"
BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_STARTED = "selection_replay_started"
BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED = "selection_replay_committed"
BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_CONFLICT = "selection_replay_conflict"
BRANCHING_TIMELINE_EVENT_TIMELINE_COMPACTED = "timeline_compacted"
BRANCHING_TIMELINE_EVENT_TIMELINE_ARCHIVED = "timeline_archived"
BRANCHING_TIMELINE_EVENT_TYPES = (
    BRANCHING_TIMELINE_EVENT_TREE_CREATED,
    BRANCHING_TIMELINE_EVENT_TREE_BECAME_STALE,
    BRANCHING_TIMELINE_EVENT_TREE_EXPIRED,
    BRANCHING_TIMELINE_EVENT_NODE_SELECTED,
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_STARTED,
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED,
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_CONFLICT,
    BRANCHING_TIMELINE_EVENT_TIMELINE_COMPACTED,
    BRANCHING_TIMELINE_EVENT_TIMELINE_ARCHIVED,
)

BRANCHING_TIMELINE_TREE_STATUS_ACTIVE = "active"
BRANCHING_TIMELINE_TREE_STATUS_STALE = "stale"
BRANCHING_TIMELINE_TREE_STATUS_EXPIRED = "expired"
BRANCHING_TIMELINE_TREE_STATUS_COMMITTED = "committed"

BRANCHING_TIMELINE_DEFAULT_MAX_EVENTS = 200
BRANCHING_TIMELINE_DEFAULT_MAX_ACTIVE_TREES = 5
BRANCHING_TIMELINE_DEFAULT_MAX_TREE_REFERENCES = 20
BRANCHING_TIMELINE_MIN_MAX_EVENTS = 8
BRANCHING_TIMELINE_COMPACTION_PROTECTED_EVENT_TYPES = (
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED,
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_CONFLICT,
    BRANCHING_TIMELINE_EVENT_TIMELINE_ARCHIVED,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, set):
        return sorted(_json_safe(v) for v in value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def default_branch_timeline_bounds() -> dict[str, int]:
    return {
        "max_events": BRANCHING_TIMELINE_DEFAULT_MAX_EVENTS,
        "max_active_trees": BRANCHING_TIMELINE_DEFAULT_MAX_ACTIVE_TREES,
        "max_tree_references": BRANCHING_TIMELINE_DEFAULT_MAX_TREE_REFERENCES,
    }


def normalize_branch_timeline_bounds(bounds: dict[str, Any] | None = None) -> dict[str, int]:
    out = default_branch_timeline_bounds()
    if isinstance(bounds, dict):
        for key in tuple(out):
            if key in bounds:
                try:
                    out[key] = int(bounds[key])
                except (TypeError, ValueError):
                    continue
    out["max_events"] = max(BRANCHING_TIMELINE_MIN_MAX_EVENTS, out["max_events"])
    out["max_active_trees"] = max(1, out["max_active_trees"])
    out["max_tree_references"] = max(out["max_active_trees"], out["max_tree_references"])
    return out


def stable_branch_timeline_id(
    *,
    story_session_id: str,
    scope: str = BRANCHING_TIMELINE_SCOPE_ACTIVE,
    preview: dict[str, Any] | None = None,
) -> str:
    preview_key = ""
    if isinstance(preview, dict):
        for key in ("preview_id", "preview_package_id", "package_version_id", "namespace"):
            value = str(preview.get(key) or "").strip()
            if value:
                preview_key = value
                break
    seed = "|".join([story_session_id, scope, preview_key])
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"branch_timeline_{digest}"


def make_branch_timeline_record(
    *,
    story_session_id: str,
    module_id: str | None = None,
    runtime_profile_id: str | None = None,
    scope: str = BRANCHING_TIMELINE_SCOPE_ACTIVE,
    root_session_fingerprint: dict[str, Any] | None = None,
    preview: dict[str, Any] | None = None,
    bounds: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    normalized_scope = scope if scope in BRANCHING_TIMELINE_SCOPES else BRANCHING_TIMELINE_SCOPE_ACTIVE
    created = created_at or _now_iso()
    timeline = {
        "schema_version": BRANCHING_TIMELINE_RECORD_SCHEMA_VERSION,
        "source": BRANCHING_TIMELINE_RECORD_SOURCE,
        "timeline_id": stable_branch_timeline_id(
            story_session_id=story_session_id,
            scope=normalized_scope,
            preview=preview,
        ),
        "story_session_id": story_session_id,
        "module_id": module_id,
        "runtime_profile_id": runtime_profile_id,
        "scope": normalized_scope,
        "status": BRANCHING_TIMELINE_STATUS_ACTIVE,
        "root_session_fingerprint": _json_safe(root_session_fingerprint or {}),
        "current_session_fingerprint": _json_safe(root_session_fingerprint or {}),
        "preview": _json_safe(preview or {}),
        "bounds": normalize_branch_timeline_bounds(bounds),
        "events": [],
        "compaction": {
            "compacted_event_count": 0,
            "last_compacted_at": None,
        },
        "created_at": created,
        "updated_at": created,
    }
    timeline["snapshot"] = build_branch_timeline_snapshot(timeline)
    return timeline


def make_branch_timeline_event(
    *,
    event_type: str,
    story_session_id: str,
    timeline_id: str,
    scope: str = BRANCHING_TIMELINE_SCOPE_ACTIVE,
    tree_id: str | None = None,
    node_id: str | None = None,
    canonical_turn_id: str | None = None,
    session_fingerprint: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    normalized_event_type = str(event_type or "").strip()
    if normalized_event_type not in BRANCHING_TIMELINE_EVENT_TYPES:
        raise ValueError(f"branch_timeline_unknown_event_type:{normalized_event_type}")
    happened = occurred_at or _now_iso()
    payload = {
        "event_type": normalized_event_type,
        "story_session_id": story_session_id,
        "timeline_id": timeline_id,
        "scope": scope if scope in BRANCHING_TIMELINE_SCOPES else BRANCHING_TIMELINE_SCOPE_ACTIVE,
        "tree_id": tree_id,
        "node_id": node_id,
        "canonical_turn_id": canonical_turn_id,
        "session_fingerprint": _json_safe(session_fingerprint or {}),
        "details": _json_safe(details or {}),
        "occurred_at": happened,
    }
    event_seed = json.dumps(payload, sort_keys=True, default=str)
    payload["schema_version"] = BRANCHING_TIMELINE_EVENT_SCHEMA_VERSION
    payload["event_id"] = "branch_timeline_event_" + hashlib.sha256(event_seed.encode("utf-8")).hexdigest()[:16]
    return payload


def append_branch_timeline_event(timeline: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(timeline, dict):
        raise ValueError("branch_timeline_payload_not_object")
    if not isinstance(event, dict):
        raise ValueError("branch_timeline_event_not_object")
    timeline_id = str(timeline.get("timeline_id") or "")
    if str(event.get("timeline_id") or "") != timeline_id:
        raise ValueError("branch_timeline_event_timeline_mismatch")
    if str(event.get("story_session_id") or "") != str(timeline.get("story_session_id") or ""):
        raise ValueError("branch_timeline_event_session_mismatch")
    event_type = str(event.get("event_type") or "")
    if event_type not in BRANCHING_TIMELINE_EVENT_TYPES:
        raise ValueError(f"branch_timeline_unknown_event_type:{event_type}")

    out = _json_safe(dict(timeline))
    events = list(out.get("events") or [])
    events.append(_json_safe(event))
    out["events"] = events
    out["updated_at"] = str(event.get("occurred_at") or _now_iso())
    if event_type == BRANCHING_TIMELINE_EVENT_TIMELINE_ARCHIVED:
        out["status"] = BRANCHING_TIMELINE_STATUS_ARCHIVED
    out["snapshot"] = build_branch_timeline_snapshot(out)
    return compact_branch_timeline(out)


def compact_branch_timeline(timeline: dict[str, Any], *, max_events: int | None = None) -> dict[str, Any]:
    out = _json_safe(dict(timeline))
    events = list(out.get("events") or [])
    bounds = normalize_branch_timeline_bounds(out.get("bounds") if isinstance(out.get("bounds"), dict) else None)
    out["bounds"] = bounds
    event_limit = int(max_events if max_events is not None else bounds["max_events"])
    event_limit = max(BRANCHING_TIMELINE_MIN_MAX_EVENTS, event_limit)
    if len(events) <= event_limit:
        out["snapshot"] = build_branch_timeline_snapshot(out)
        return out

    available = event_limit - 1
    tail_start = max(0, len(events) - available)
    selected_indexes = set(range(tail_start, len(events)))
    for idx, event in enumerate(events):
        if str(event.get("event_type") or "") in BRANCHING_TIMELINE_COMPACTION_PROTECTED_EVENT_TYPES:
            selected_indexes.add(idx)
    selected = sorted(selected_indexes)[-available:]
    kept_events = [events[idx] for idx in selected]
    removed_count = len(events) - len(kept_events)

    compaction = dict(out.get("compaction") or {})
    compacted_total = int(compaction.get("compacted_event_count") or 0) + removed_count
    compacted_at = _now_iso()
    compaction["compacted_event_count"] = compacted_total
    compaction["last_compacted_at"] = compacted_at
    out["compaction"] = compaction

    marker = make_branch_timeline_event(
        event_type=BRANCHING_TIMELINE_EVENT_TIMELINE_COMPACTED,
        story_session_id=str(out.get("story_session_id") or ""),
        timeline_id=str(out.get("timeline_id") or ""),
        scope=str(out.get("scope") or BRANCHING_TIMELINE_SCOPE_ACTIVE),
        details={
            "removed_event_count": removed_count,
            "compacted_event_count": compacted_total,
            "max_events": event_limit,
        },
        occurred_at=compacted_at,
    )
    out["events"] = [*kept_events, marker]
    out["updated_at"] = compacted_at
    out["snapshot"] = build_branch_timeline_snapshot(out)
    return out


def archive_branch_timeline(timeline: dict[str, Any], *, reason: str = "operator_archived") -> dict[str, Any]:
    out = _json_safe(dict(timeline))
    out["status"] = BRANCHING_TIMELINE_STATUS_ARCHIVED
    event = make_branch_timeline_event(
        event_type=BRANCHING_TIMELINE_EVENT_TIMELINE_ARCHIVED,
        story_session_id=str(out.get("story_session_id") or ""),
        timeline_id=str(out.get("timeline_id") or ""),
        scope=str(out.get("scope") or BRANCHING_TIMELINE_SCOPE_ACTIVE),
        details={"reason": reason},
    )
    return append_branch_timeline_event(out, event)


def build_branch_timeline_snapshot(timeline: dict[str, Any]) -> dict[str, Any]:
    events = timeline.get("events") if isinstance(timeline.get("events"), list) else []
    tree_states: dict[str, str] = {}
    selection_count = 0
    replay_commit_count = 0
    replay_conflict_count = 0
    last_event_type = None
    last_event_at = None

    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type") or "")
        tree_id = str(event.get("tree_id") or "").strip()
        details = event.get("details") if isinstance(event.get("details"), dict) else {}
        if event_type:
            last_event_type = event_type
            last_event_at = event.get("occurred_at")
        if event_type == BRANCHING_TIMELINE_EVENT_TREE_CREATED and tree_id:
            raw_status = str(details.get("tree_status") or BRANCHING_TIMELINE_TREE_STATUS_ACTIVE)
            tree_states[tree_id] = (
                raw_status
                if raw_status
                in {
                    BRANCHING_TIMELINE_TREE_STATUS_STALE,
                    BRANCHING_TIMELINE_TREE_STATUS_EXPIRED,
                    BRANCHING_TIMELINE_TREE_STATUS_COMMITTED,
                }
                else BRANCHING_TIMELINE_TREE_STATUS_ACTIVE
            )
        elif event_type == BRANCHING_TIMELINE_EVENT_TREE_BECAME_STALE and tree_id:
            tree_states[tree_id] = BRANCHING_TIMELINE_TREE_STATUS_STALE
        elif event_type == BRANCHING_TIMELINE_EVENT_TREE_EXPIRED and tree_id:
            tree_states[tree_id] = BRANCHING_TIMELINE_TREE_STATUS_EXPIRED
        elif event_type == BRANCHING_TIMELINE_EVENT_NODE_SELECTED:
            selection_count += 1
        elif event_type == BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED:
            replay_commit_count += 1
            if tree_id:
                tree_states[tree_id] = BRANCHING_TIMELINE_TREE_STATUS_COMMITTED
        elif event_type == BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_CONFLICT:
            replay_conflict_count += 1
            if tree_id:
                tree_states[tree_id] = BRANCHING_TIMELINE_TREE_STATUS_COMMITTED

    active_tree_ids = sorted(
        tree_id for tree_id, status in tree_states.items() if status == BRANCHING_TIMELINE_TREE_STATUS_ACTIVE
    )
    stale_tree_ids = sorted(
        tree_id for tree_id, status in tree_states.items() if status == BRANCHING_TIMELINE_TREE_STATUS_STALE
    )
    expired_tree_ids = sorted(
        tree_id for tree_id, status in tree_states.items() if status == BRANCHING_TIMELINE_TREE_STATUS_EXPIRED
    )
    committed_tree_ids = sorted(
        tree_id for tree_id, status in tree_states.items() if status == BRANCHING_TIMELINE_TREE_STATUS_COMMITTED
    )
    bounds = normalize_branch_timeline_bounds(timeline.get("bounds") if isinstance(timeline.get("bounds"), dict) else None)
    compaction = timeline.get("compaction") if isinstance(timeline.get("compaction"), dict) else {}
    return {
        "schema_version": BRANCHING_TIMELINE_SNAPSHOT_SCHEMA_VERSION,
        "timeline_id": timeline.get("timeline_id"),
        "story_session_id": timeline.get("story_session_id"),
        "scope": timeline.get("scope") if timeline.get("scope") in BRANCHING_TIMELINE_SCOPES else BRANCHING_TIMELINE_SCOPE_ACTIVE,
        "status": timeline.get("status")
        if timeline.get("status") in BRANCHING_TIMELINE_STATUSES
        else BRANCHING_TIMELINE_STATUS_ACTIVE,
        "event_count": len(events),
        "compacted_event_count": int(compaction.get("compacted_event_count") or 0),
        "tree_count": len(tree_states),
        "active_tree_ids": active_tree_ids[: bounds["max_tree_references"]],
        "stale_tree_ids": stale_tree_ids[: bounds["max_tree_references"]],
        "expired_tree_ids": expired_tree_ids[: bounds["max_tree_references"]],
        "committed_tree_ids": committed_tree_ids[: bounds["max_tree_references"]],
        "active_tree_count": len(active_tree_ids),
        "stale_tree_count": len(stale_tree_ids),
        "expired_tree_count": len(expired_tree_ids),
        "committed_tree_count": len(committed_tree_ids),
        "selection_count": selection_count,
        "replay_commit_count": replay_commit_count,
        "replay_conflict_count": replay_conflict_count,
        "last_event_type": last_event_type,
        "last_event_at": last_event_at,
        "bounds": bounds,
        "bounds_exceeded": {
            "events": len(events) > bounds["max_events"],
            "active_trees": len(active_tree_ids) > bounds["max_active_trees"],
            "tree_references": len(tree_states) > bounds["max_tree_references"],
        },
    }
