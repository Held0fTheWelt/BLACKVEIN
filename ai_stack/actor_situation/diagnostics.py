"""Compact W5 Actor Situation diagnostics (Phase 4B).

Admin and observability consumers must inspect typed W5 snapshots/projections
without reading raw persisted ``w5_history`` dicts or exposing full ledgers by
default. These helpers coerce persisted snapshots through ``W5Snapshot`` and
emit bounded, read-only views.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from ai_stack.actor_situation.models import (
    W5ConflictResolutionStatus,
    W5Dimension,
    W5Fact,
    W5FactStatus,
    W5Projection,
    W5Snapshot,
    W5TruthLevel,
)
from ai_stack.actor_situation.projection import (
    build_w5_projection_for_narrator,
    build_w5_projection_for_npc,
)
from ai_stack.actor_situation.validation import w5_ast_validation_enabled


W5_ADMIN_DIAGNOSTIC_SCHEMA_VERSION = "w5_admin_diagnostics.v1"
W5_RUNTIME_METADATA_SCHEMA_VERSION = "w5_runtime_metadata.v1"


def _flag_enabled(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def w5_projection_flag_states() -> dict[str, bool]:
    """Return current W5 feature-flag posture without mutating runtime config."""

    return {
        "narrator": _flag_enabled("W5_AST_NARRATOR_PROJECTION_ENABLED"),
        "director": _flag_enabled("W5_AST_DIRECTOR_PROJECTION_ENABLED"),
        "npc": _flag_enabled("W5_AST_NPC_PROJECTION_ENABLED"),
        "validation": w5_ast_validation_enabled(),
    }


def coerce_w5_snapshot(
    snapshot: W5Snapshot | Mapping[str, Any] | None,
) -> W5Snapshot:
    if isinstance(snapshot, W5Snapshot):
        return snapshot
    if isinstance(snapshot, Mapping):
        return W5Snapshot.from_dict(dict(snapshot))
    raise ValueError("missing_w5_latest_snapshot")


def _active_facts(facts: tuple[W5Fact, ...]) -> list[W5Fact]:
    return [fact for fact in facts if fact.status is W5FactStatus.ACTIVE]


def _strongest_fact(facts: tuple[W5Fact, ...], key: str) -> W5Fact | None:
    rank = {
        W5TruthLevel.CANONICAL: 5,
        W5TruthLevel.OBSERVED: 4,
        W5TruthLevel.DIRECTOR_ASSIGNED: 3,
        W5TruthLevel.DECLARED: 2,
        W5TruthLevel.INFERRED: 1,
        W5TruthLevel.PROJECTED: 0,
    }
    candidates = [fact for fact in _active_facts(facts) if fact.key == key]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda fact: (
            rank.get(fact.truth_level, 0),
            float(fact.confidence),
            int(fact.last_confirmed_turn),
        ),
        reverse=True,
    )[0]


def _compact_fact(fact: W5Fact, *, include_value: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {
        "fact_id": fact.fact_id,
        "actor_id": fact.actor_id,
        "dimension": fact.dimension.value,
        "key": fact.key,
        "source": fact.source.value,
        "truth_level": fact.truth_level.value,
        "truth_label": "soft_inferred" if fact.truth_level is W5TruthLevel.INFERRED else fact.truth_level.value,
        "visibility": fact.visibility.value,
        "status": fact.status.value,
        "confidence": float(fact.confidence),
        "last_confirmed_turn": int(fact.last_confirmed_turn),
    }
    if include_value:
        out["value"] = fact.value
    if fact.source_event_id:
        out["source_event_id"] = fact.source_event_id
    if fact.actor_knowledge_scope:
        out["actor_knowledge_scope"] = list(fact.actor_knowledge_scope)
    if fact.contradicted_by_fact_id:
        out["contradicted_by_fact_id"] = fact.contradicted_by_fact_id
    return out


def _dimension_view(facts: tuple[W5Fact, ...]) -> dict[str, Any]:
    active = _active_facts(facts)
    return {
        "facts": [_compact_fact(fact) for fact in active[:12]],
        "active_count": len(active),
        "stale_count": sum(1 for fact in facts if fact.status is W5FactStatus.STALE),
        "contradicted_count": sum(
            1
            for fact in facts
            if fact.status is W5FactStatus.CONTRADICTED or bool(fact.contradicted_by_fact_id)
        ),
        "truth_levels": sorted({fact.truth_level.value for fact in active}),
        "sources": sorted({fact.source.value for fact in active}),
    }


def _snapshot_stats(snapshot: W5Snapshot) -> dict[str, Any]:
    active_facts: list[W5Fact] = []
    stale_facts = 0
    contradicted_facts = 0
    for situation in snapshot.actors.values():
        for facts in (situation.where, situation.what, situation.how, situation.why):
            for fact in facts:
                if fact.status is W5FactStatus.ACTIVE:
                    active_facts.append(fact)
                if fact.status is W5FactStatus.STALE:
                    stale_facts += 1
                if fact.status is W5FactStatus.CONTRADICTED or fact.contradicted_by_fact_id:
                    contradicted_facts += 1
    return {
        "actor_count": len(snapshot.actors),
        "active_fact_count": len(active_facts),
        "stale_fact_count": stale_facts,
        "contradicted_fact_count": contradicted_facts,
        "conflict_count": len(snapshot.conflicts),
        "unresolved_conflict_count": sum(
            1
            for conflict in snapshot.conflicts
            if conflict.resolution_status is W5ConflictResolutionStatus.UNRESOLVED
        ),
        "has_how": any(fact.dimension is W5Dimension.HOW for fact in active_facts),
        "has_inferred_why": any(
            fact.dimension is W5Dimension.WHY
            and fact.truth_level is W5TruthLevel.INFERRED
            for fact in active_facts
        ),
    }


def _validation_payload(latest_validation_outcome: Mapping[str, Any] | None) -> dict[str, Any]:
    outcome = latest_validation_outcome if isinstance(latest_validation_outcome, Mapping) else {}
    w5 = outcome.get("w5_validation") if isinstance(outcome.get("w5_validation"), Mapping) else {}
    return {
        "w5_validation_enabled": w5_ast_validation_enabled(),
        "w5_validation_ran": bool(w5.get("w5_validation_ran")),
        "w5_validation_failed": bool(w5.get("w5_validation_failed")),
        "w5_validation_failure_codes": list(w5.get("w5_validation_failure_codes") or []),
        "w5_snapshot_id": w5.get("w5_snapshot_id"),
        "w5_validation_source": w5.get("w5_validation_source"),
        "w5_validation_fallback_reason": w5.get("w5_validation_fallback_reason"),
        "w5_validation_warnings": list(w5.get("w5_validation_warnings") or []),
        "failures": list(w5.get("failures") or []),
    }


def build_w5_runtime_metadata(
    snapshot: W5Snapshot | Mapping[str, Any] | None,
    *,
    latest_validation_outcome: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compact W5 fields safe for committed turn diagnostics."""

    try:
        typed = coerce_w5_snapshot(snapshot)
    except Exception as exc:
        return {
            "schema_version": W5_RUNTIME_METADATA_SCHEMA_VERSION,
            "w5_snapshot_id": None,
            "w5_actor_count": 0,
            "w5_conflict_count": 0,
            "w5_has_how": False,
            "w5_has_inferred_why": False,
            "w5_validation_enabled": w5_ast_validation_enabled(),
            "w5_validation_ran": False,
            "w5_validation_failure_codes": [],
            "w5_projection_flags_used": w5_projection_flag_states(),
            "w5_metadata_fallback_reason": str(exc) or type(exc).__name__,
        }
    stats = _snapshot_stats(typed)
    validation = _validation_payload(latest_validation_outcome)
    return {
        "schema_version": W5_RUNTIME_METADATA_SCHEMA_VERSION,
        "w5_snapshot_id": typed.snapshot_id,
        "w5_actor_count": stats["actor_count"],
        "w5_conflict_count": stats["conflict_count"],
        "w5_has_how": bool(stats["has_how"]),
        "w5_has_inferred_why": bool(stats["has_inferred_why"]),
        "w5_validation_enabled": validation["w5_validation_enabled"],
        "w5_validation_ran": validation["w5_validation_ran"],
        "w5_validation_failure_codes": validation["w5_validation_failure_codes"],
        "w5_projection_flags_used": w5_projection_flag_states(),
    }


def build_w5_langfuse_metadata(
    snapshot: W5Snapshot | Mapping[str, Any] | None,
    *,
    latest_validation_outcome: Mapping[str, Any] | None = None,
    location_changed_this_turn: bool | None = None,
) -> dict[str, Any]:
    """Dot-key W5 attributes for existing trace/span metadata."""

    runtime = build_w5_runtime_metadata(
        snapshot,
        latest_validation_outcome=latest_validation_outcome,
    )
    return {
        "w5.snapshot_id": runtime.get("w5_snapshot_id"),
        "w5.actor_count": runtime.get("w5_actor_count"),
        "w5.unresolved_conflict_count": (
            _snapshot_stats(coerce_w5_snapshot(snapshot))["unresolved_conflict_count"]
            if snapshot is not None and runtime.get("w5_snapshot_id")
            else 0
        ),
        "w5.location_changed_this_turn": bool(location_changed_this_turn),
        "w5.has_how": bool(runtime.get("w5_has_how")),
        "w5.has_inferred_why": bool(runtime.get("w5_has_inferred_why")),
        "w5.validation_enabled": bool(runtime.get("w5_validation_enabled")),
        "w5.validation_failed": bool(
            (latest_validation_outcome or {})
            .get("w5_validation", {})
            .get("w5_validation_failed")
        )
        if isinstance(latest_validation_outcome, Mapping)
        else False,
        "w5.validation_failure_codes": list(runtime.get("w5_validation_failure_codes") or []),
    }


def build_w5_admin_empty_view(reason: str) -> dict[str, Any]:
    return {
        "schema_version": W5_ADMIN_DIAGNOSTIC_SCHEMA_VERSION,
        "status": "unavailable",
        "diagnostic": {
            "reason": str(reason or "missing_w5_latest_snapshot"),
            "safe_empty": True,
        },
        "flags": w5_projection_flag_states(),
        "read_only": True,
    }


def build_w5_admin_snapshot_view(
    snapshot: W5Snapshot | Mapping[str, Any] | None,
) -> dict[str, Any]:
    try:
        typed = coerce_w5_snapshot(snapshot)
    except Exception as exc:
        return build_w5_admin_empty_view(str(exc))
    stats = _snapshot_stats(typed)
    actor_summaries: dict[str, Any] = {}
    for actor_id, situation in sorted(typed.actors.items()):
        where = _strongest_fact(situation.where, "scene_location")
        action = _strongest_fact(situation.what, "current_action")
        how = _strongest_fact(situation.how, "tone") or (_active_facts(situation.how)[0] if _active_facts(situation.how) else None)
        why = _active_facts(situation.why)[0] if _active_facts(situation.why) else None
        actor_summaries[actor_id] = {
            "actor_id": actor_id,
            "actor_type": situation.actor_type.value,
            "freshness_status": situation.freshness_status.value,
            "last_confirmed_turn": int(situation.last_confirmed_turn),
            "where": _compact_fact(where) if where else None,
            "what": _compact_fact(action) if action else None,
            "how": _compact_fact(how) if how else None,
            "why": _compact_fact(why) if why else None,
        }
    return {
        "schema_version": W5_ADMIN_DIAGNOSTIC_SCHEMA_VERSION,
        "status": "ok",
        "snapshot_id": typed.snapshot_id,
        "story_session_id": typed.story_session_id,
        "turn_number": int(typed.turn_number),
        "created_at": typed.created_at,
        "stats": stats,
        "actor_summaries": actor_summaries,
        "flags": w5_projection_flag_states(),
        "read_only": True,
        "raw_w5_history_exposed": False,
    }


def build_w5_admin_actor_view(
    snapshot: W5Snapshot | Mapping[str, Any] | None,
    *,
    actor_id: str,
) -> dict[str, Any]:
    try:
        typed = coerce_w5_snapshot(snapshot)
    except Exception as exc:
        return build_w5_admin_empty_view(str(exc))
    situation = typed.actors.get(actor_id)
    if situation is None:
        return build_w5_admin_empty_view(f"actor_not_found:{actor_id}")
    return {
        "schema_version": W5_ADMIN_DIAGNOSTIC_SCHEMA_VERSION,
        "status": "ok",
        "snapshot_id": typed.snapshot_id,
        "actor_id": actor_id,
        "actor_type": situation.actor_type.value,
        "freshness_status": situation.freshness_status.value,
        "dimensions": {
            "who": {
                "actor_id": actor_id,
                "actor_type": situation.actor_type.value,
                "actor_role_in_scene": situation.actor_role_in_scene,
                "involvement_type": situation.involvement_type,
            },
            "where": _dimension_view(situation.where),
            "what": _dimension_view(situation.what),
            "how": _dimension_view(situation.how),
            "why": _dimension_view(situation.why),
        },
        "source_truth_inspector": {
            "source_count": len(
                {
                    fact.source.value
                    for facts in (situation.where, situation.what, situation.how, situation.why)
                    for fact in facts
                }
            ),
            "truth_levels": sorted(
                {
                    fact.truth_level.value
                    for facts in (situation.where, situation.what, situation.how, situation.why)
                    for fact in facts
                }
            ),
        },
        "visibility_perception_matrix": {
            "private_fact_count": sum(
                1
                for facts in (situation.where, situation.what, situation.how, situation.why)
                for fact in facts
                if fact.visibility.value != "public"
            ),
            "scoped_actor_ids": sorted(
                {
                    scoped
                    for facts in (situation.where, situation.what, situation.how, situation.why)
                    for fact in facts
                    for scoped in fact.actor_knowledge_scope
                }
            ),
        },
        "stale_contradicted_facts": [
            _compact_fact(fact)
            for facts in (situation.where, situation.what, situation.how, situation.why)
            for fact in facts
            if fact.status in {W5FactStatus.STALE, W5FactStatus.CONTRADICTED}
            or fact.contradicted_by_fact_id
        ][:12],
        "flags": w5_projection_flag_states(),
        "read_only": True,
    }


def build_w5_admin_conflicts_view(
    snapshot: W5Snapshot | Mapping[str, Any] | None,
) -> dict[str, Any]:
    try:
        typed = coerce_w5_snapshot(snapshot)
    except Exception as exc:
        return build_w5_admin_empty_view(str(exc))
    fact_index: dict[str, W5Fact] = {}
    for situation in typed.actors.values():
        for facts in (situation.where, situation.what, situation.how, situation.why):
            for fact in facts:
                fact_index[fact.fact_id] = fact
    conflicts = []
    for conflict in typed.conflicts:
        conflicts.append(
            {
                "conflict_id": conflict.conflict_id,
                "actor_id": conflict.actor_id,
                "dimension": conflict.dimension.value,
                "resolution_status": conflict.resolution_status.value,
                "resolver_source": conflict.resolver_source.value if conflict.resolver_source else None,
                "competing_fact_refs": [
                    _compact_fact(fact_index[fid], include_value=False)
                    for fid in conflict.competing_fact_ids
                    if fid in fact_index
                ],
            }
        )
    return {
        "schema_version": W5_ADMIN_DIAGNOSTIC_SCHEMA_VERSION,
        "status": "ok",
        "snapshot_id": typed.snapshot_id,
        "unresolved_count": sum(
            1
            for conflict in typed.conflicts
            if conflict.resolution_status is W5ConflictResolutionStatus.UNRESOLVED
        ),
        "conflicts": conflicts,
        "flags": w5_projection_flag_states(),
        "read_only": True,
    }


def _projection_payload(projection: W5Projection) -> dict[str, Any]:
    payload = projection.to_dict()
    payload["raw_w5_ledger_exposed"] = False
    return payload


def build_w5_admin_narrator_projection_preview(
    snapshot: W5Snapshot | Mapping[str, Any] | None,
    *,
    actor_id: str | None = None,
) -> dict[str, Any]:
    try:
        projection = build_w5_projection_for_narrator(snapshot, actor_id=actor_id)
    except Exception as exc:
        return build_w5_admin_empty_view(str(exc))
    return {
        "schema_version": W5_ADMIN_DIAGNOSTIC_SCHEMA_VERSION,
        "status": "ok",
        "projection": _projection_payload(projection),
        "flags": w5_projection_flag_states(),
        "read_only": True,
    }


def build_w5_admin_npc_projection_preview(
    snapshot: W5Snapshot | Mapping[str, Any] | None,
    *,
    actor_id: str,
) -> dict[str, Any]:
    try:
        projection = build_w5_projection_for_npc(snapshot, actor_id=actor_id)
    except Exception as exc:
        return build_w5_admin_empty_view(str(exc))
    return {
        "schema_version": W5_ADMIN_DIAGNOSTIC_SCHEMA_VERSION,
        "status": "ok",
        "actor_id": actor_id,
        "projection": _projection_payload(projection),
        "flags": w5_projection_flag_states(),
        "read_only": True,
    }


def build_w5_admin_validation_view(
    snapshot: W5Snapshot | Mapping[str, Any] | None,
    *,
    latest_validation_outcome: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot_id = None
    status = "ok"
    try:
        snapshot_id = coerce_w5_snapshot(snapshot).snapshot_id
    except Exception as exc:
        status = "unavailable"
        fallback_reason = str(exc)
    else:
        fallback_reason = None
    payload = _validation_payload(latest_validation_outcome)
    payload["w5_snapshot_id"] = payload.get("w5_snapshot_id") or snapshot_id
    if fallback_reason and not payload.get("w5_validation_fallback_reason"):
        payload["w5_validation_fallback_reason"] = fallback_reason
    return {
        "schema_version": W5_ADMIN_DIAGNOSTIC_SCHEMA_VERSION,
        "status": status,
        "validation": payload,
        "flags": w5_projection_flag_states(),
        "read_only": True,
    }


__all__ = [
    "W5_ADMIN_DIAGNOSTIC_SCHEMA_VERSION",
    "W5_RUNTIME_METADATA_SCHEMA_VERSION",
    "build_w5_admin_actor_view",
    "build_w5_admin_conflicts_view",
    "build_w5_admin_empty_view",
    "build_w5_admin_narrator_projection_preview",
    "build_w5_admin_npc_projection_preview",
    "build_w5_admin_snapshot_view",
    "build_w5_admin_validation_view",
    "build_w5_langfuse_metadata",
    "build_w5_runtime_metadata",
    "coerce_w5_snapshot",
    "w5_projection_flag_states",
]
