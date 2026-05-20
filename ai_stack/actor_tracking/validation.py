"""W5 Actor Tracking validation helpers (Phase 4A).

The validation layer is read-side only: it inspects a typed ``W5Snapshot`` and
proposed structured output, emits compact diagnostics, and never mutates output
blocks or committed events. See ADR-0063 and
``docs/MVPs/w5_actor_tracking_migration.md``.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from typing import Any

from ai_stack.actor_tracking.models import (
    W5ConflictResolutionStatus,
    W5Dimension,
    W5Fact,
    W5FactStatus,
    W5Snapshot,
    W5TruthLevel,
    W5ValidationFailureCode,
    W5VisibilityScope,
)


W5_VALIDATION_SCHEMA_VERSION = "w5_validation.v1"

_HARD_TRUTH_LEVELS = {
    W5TruthLevel.CANONICAL,
    W5TruthLevel.OBSERVED,
    W5TruthLevel.DECLARED,
    W5TruthLevel.DIRECTOR_ASSIGNED,
}


def w5_ast_validation_enabled() -> bool:
    """Fail-closed Phase 4A flag."""

    raw = (os.environ.get("W5_AST_VALIDATION_ENABLED") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _coerce_snapshot(snapshot: W5Snapshot | Mapping[str, Any] | None) -> W5Snapshot:
    if isinstance(snapshot, W5Snapshot):
        return snapshot
    if isinstance(snapshot, Mapping):
        return W5Snapshot.from_dict(dict(snapshot))
    raise ValueError("missing_w5_latest_snapshot")


def _structured_output(generation: Mapping[str, Any] | None) -> dict[str, Any]:
    gen = generation if isinstance(generation, Mapping) else {}
    meta = gen.get("metadata") if isinstance(gen.get("metadata"), Mapping) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), Mapping) else {}
    return dict(structured)


def _clean_str(value: Any) -> str:
    return str(value or "").strip()


def _iter_claims(structured: Mapping[str, Any]) -> Iterable[dict[str, Any]]:
    for lane, actor_key, kind in (
        ("spoken_lines", "speaker_id", "speech"),
        ("action_lines", "actor_id", "action"),
        ("initiative_events", "actor_id", "initiative"),
    ):
        rows = structured.get(lane)
        if not isinstance(rows, list):
            continue
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                continue
            actor_id = _clean_str(row.get(actor_key))
            if not actor_id:
                continue
            yield {
                "actor_id": actor_id,
                "lane": lane,
                "index": index,
                "kind": kind,
                "block": dict(row),
            }


def _facts_for_actor(snapshot: W5Snapshot, actor_id: str, dimension: W5Dimension) -> tuple[W5Fact, ...]:
    situation = snapshot.actors.get(actor_id)
    if situation is None:
        return ()
    return tuple(getattr(situation, dimension.value))


def _strongest_fact(
    facts: Iterable[W5Fact],
    key: str,
    *,
    active_only: bool = True,
) -> W5Fact | None:
    candidates = [
        fact
        for fact in facts
        if fact.key == key and (not active_only or fact.status is W5FactStatus.ACTIVE)
    ]
    if not candidates:
        return None
    rank = {
        W5TruthLevel.CANONICAL: 5,
        W5TruthLevel.OBSERVED: 4,
        W5TruthLevel.DECLARED: 3,
        W5TruthLevel.DIRECTOR_ASSIGNED: 3,
        W5TruthLevel.INFERRED: 2,
        W5TruthLevel.PROJECTED: 1,
    }
    return sorted(
        candidates,
        key=lambda fact: (
            rank.get(fact.truth_level, 0),
            float(fact.confidence),
            int(fact.last_confirmed_turn),
        ),
        reverse=True,
    )[0]


def _fact_ref(fact: W5Fact) -> dict[str, Any]:
    return {
        "fact_id": fact.fact_id,
        "actor_id": fact.actor_id,
        "dimension": fact.dimension.value,
        "key": fact.key,
        "truth_level": fact.truth_level.value,
        "source": fact.source.value,
        "status": fact.status.value,
        "confidence": float(fact.confidence),
    }


def _issue(
    code: W5ValidationFailureCode,
    *,
    actor_id: str | None = None,
    severity: str = "error",
    lane: str | None = None,
    index: int | None = None,
    fact_refs: list[dict[str, Any]] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "code": code.value,
        "severity": severity,
    }
    if actor_id:
        out["actor_id"] = actor_id
    if lane:
        out["lane"] = lane
    if index is not None:
        out["index"] = index
    if fact_refs:
        out["fact_refs"] = fact_refs
    if details:
        out["details"] = details
    return out


def _allowed_target_locations(
    *,
    player_action_frame: Mapping[str, Any] | None,
    affordance_resolution: Mapping[str, Any] | None,
) -> set[str]:
    allowed: set[str] = set()
    for payload in (player_action_frame, affordance_resolution):
        if not isinstance(payload, Mapping):
            continue
        for key in (
            "target_location",
            "target_location_id",
            "resolved_target_id",
            "destination_location_id",
            "current_room_id",
        ):
            value = _clean_str(payload.get(key))
            if value:
                allowed.add(value)
        transition = payload.get("local_context_transition")
        if isinstance(transition, Mapping):
            for nested_key in ("current_location", "target_location", "current_room"):
                nested = transition.get(nested_key)
                if isinstance(nested, Mapping):
                    value = _clean_str(nested.get("id") or nested.get("location_id"))
                else:
                    value = _clean_str(nested)
                if value:
                    allowed.add(value)
    return allowed


def _block_location(block: Mapping[str, Any]) -> str:
    for key in (
        "scene_location",
        "scene_location_id",
        "location_id",
        "current_location",
        "current_room_id",
    ):
        value = _clean_str(block.get(key))
        if value:
            return value
    return ""


def _has_location_transition_support(block: Mapping[str, Any]) -> bool:
    for key in (
        "committed_movement",
        "movement_committed",
        "substrate_supported_transition",
        "location_transition_supported",
    ):
        if block.get(key) is True:
            return True
    for key in ("target_location", "target_location_id", "movement_transition", "transition"):
        if _clean_str(block.get(key)):
            return True
    return False


def _referenced_fact_ids(block: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    for key in ("referenced_fact_id", "w5_fact_id", "knows_fact_id"):
        value = _clean_str(block.get(key))
        if value and value not in refs:
            refs.append(value)
    raw_many = block.get("referenced_fact_ids") or block.get("knowledge_refs")
    if isinstance(raw_many, list):
        for item in raw_many:
            if isinstance(item, Mapping):
                value = _clean_str(item.get("fact_id") or item.get("w5_fact_id"))
            else:
                value = _clean_str(item)
            if value and value not in refs:
                refs.append(value)
    return refs


def _fact_by_id(snapshot: W5Snapshot) -> dict[str, W5Fact]:
    out: dict[str, W5Fact] = {}
    for situation in snapshot.actors.values():
        for dimension in (situation.where, situation.what, situation.how, situation.why):
            for fact in dimension:
                out[fact.fact_id] = fact
    return out


def _actor_can_access_fact(snapshot: W5Snapshot, actor_id: str, fact: W5Fact) -> bool:
    if fact.visibility is W5VisibilityScope.PUBLIC:
        return True
    if fact.visibility in {W5VisibilityScope.GM_ONLY, W5VisibilityScope.DIRECTOR_ONLY}:
        return False
    if actor_id == fact.actor_id:
        return True
    owner = snapshot.actors.get(fact.actor_id)
    if owner is not None and owner.actor_type.value == "human":
        return False
    return actor_id in set(fact.actor_knowledge_scope)


def _is_hard_fact(fact: W5Fact) -> bool:
    return (
        fact.status is W5FactStatus.ACTIVE
        and fact.truth_level in _HARD_TRUTH_LEVELS
        and float(fact.confidence) >= 0.7
    )


def validate_w5_actor_tracking(
    *,
    snapshot: W5Snapshot | Mapping[str, Any] | None,
    generation: Mapping[str, Any] | None,
    proposed_state_effects: list[dict[str, Any]] | None = None,
    player_action_frame: Mapping[str, Any] | None = None,
    affordance_resolution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate proposed actor-tracking claims against a typed W5 snapshot."""

    typed_snapshot = _coerce_snapshot(snapshot)
    structured = _structured_output(generation)
    claims = list(_iter_claims(structured))
    allowed_locations = _allowed_target_locations(
        player_action_frame=player_action_frame,
        affordance_resolution=affordance_resolution,
    )
    fact_index = _fact_by_id(typed_snapshot)
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for claim in claims:
        actor_id = claim["actor_id"]
        block = claim["block"]
        where_fact = _strongest_fact(
            _facts_for_actor(typed_snapshot, actor_id, W5Dimension.WHERE),
            "scene_location",
            active_only=True,
        )
        if where_fact is None:
            failures.append(
                _issue(
                    W5ValidationFailureCode.W5_ACTOR_NOT_PRESENT,
                    actor_id=actor_id,
                    lane=claim["lane"],
                    index=claim["index"],
                    details={"claim_kind": claim["kind"]},
                )
            )
        else:
            claimed_location = _block_location(block)
            if (
                claimed_location
                and claimed_location != str(where_fact.value)
                and claimed_location not in allowed_locations
                and not _has_location_transition_support(block)
            ):
                failures.append(
                    _issue(
                        W5ValidationFailureCode.W5_LOCATION_CONTINUITY_BREAK,
                        actor_id=actor_id,
                        lane=claim["lane"],
                        index=claim["index"],
                        fact_refs=[_fact_ref(where_fact)],
                        details={
                            "w5_scene_location": str(where_fact.value),
                            "claimed_location": claimed_location,
                        },
                    )
                )

        for fact_id in _referenced_fact_ids(block):
            fact = fact_index.get(fact_id)
            if fact is None:
                continue
            if not _actor_can_access_fact(typed_snapshot, actor_id, fact):
                failures.append(
                    _issue(
                        W5ValidationFailureCode.W5_PERCEPTION_BREAK,
                        actor_id=actor_id,
                        lane=claim["lane"],
                        index=claim["index"],
                        fact_refs=[_fact_ref(fact)],
                        details={"referenced_fact_id": fact_id},
                    )
                )

        next_action_state = _clean_str(block.get("action_state"))
        if next_action_state and not _clean_str(block.get("action_transition")):
            state_fact = _strongest_fact(
                _facts_for_actor(typed_snapshot, actor_id, W5Dimension.WHAT),
                "action_state",
                active_only=False,
            )
            if state_fact is not None and next_action_state != str(state_fact.value):
                issue = _issue(
                    W5ValidationFailureCode.W5_ACTION_CONTINUITY_BREAK,
                    actor_id=actor_id,
                    severity="error" if _is_hard_fact(state_fact) else "warning",
                    lane=claim["lane"],
                    index=claim["index"],
                    fact_refs=[_fact_ref(state_fact)],
                    details={
                        "w5_action_state": str(state_fact.value),
                        "claimed_action_state": next_action_state,
                    },
                )
                if issue["severity"] == "error":
                    failures.append(issue)
                else:
                    warnings.append(issue)

    claimed_actor_ids = {claim["actor_id"] for claim in claims}
    for conflict in typed_snapshot.conflicts:
        if conflict.resolution_status is not W5ConflictResolutionStatus.UNRESOLVED:
            continue
        if claimed_actor_ids and conflict.actor_id not in claimed_actor_ids:
            continue
        refs = [fact_index[fid] for fid in conflict.competing_fact_ids if fid in fact_index]
        hard_refs = [fact for fact in refs if fact.truth_level in {W5TruthLevel.CANONICAL, W5TruthLevel.OBSERVED}]
        inferred_why_only = (
            conflict.dimension is W5Dimension.WHY
            and refs
            and all(fact.truth_level is W5TruthLevel.INFERRED for fact in refs)
        )
        issue = _issue(
            W5ValidationFailureCode.W5_UNRESOLVED_CONFLICT,
            actor_id=conflict.actor_id,
            severity="warning" if inferred_why_only or not hard_refs else "error",
            fact_refs=[_fact_ref(fact) for fact in refs[:4]],
            details={
                "conflict_id": conflict.conflict_id,
                "dimension": conflict.dimension.value,
                "resolution_status": conflict.resolution_status.value,
            },
        )
        if issue["severity"] == "error":
            failures.append(issue)
        else:
            warnings.append(issue)

    failure_codes = []
    for item in failures:
        code = str(item.get("code") or "")
        if code and code not in failure_codes:
            failure_codes.append(code)

    return {
        "schema_version": W5_VALIDATION_SCHEMA_VERSION,
        "status": "failed" if failures else "passed",
        "w5_validation_failed": bool(failures),
        "w5_validation_failure_codes": failure_codes,
        "w5_snapshot_id": typed_snapshot.snapshot_id,
        "w5_validation_source": "w5_snapshot",
        "failures": failures,
        "warnings": warnings,
        "proposed_effect_count": len(proposed_state_effects or []),
    }


def w5_validation_fallback(reason: str) -> dict[str, Any]:
    return {
        "schema_version": W5_VALIDATION_SCHEMA_VERSION,
        "status": "fallback",
        "w5_validation_failed": False,
        "w5_validation_failure_codes": [],
        "w5_snapshot_id": None,
        "w5_validation_source": "structural_fallback",
        "w5_validation_fallback_reason": reason,
        "failures": [],
        "warnings": [],
    }


__all__ = [
    "W5_VALIDATION_SCHEMA_VERSION",
    "validate_w5_actor_tracking",
    "w5_ast_validation_enabled",
    "w5_validation_fallback",
]
