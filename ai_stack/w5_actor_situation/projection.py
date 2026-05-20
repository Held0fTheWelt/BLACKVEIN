"""W5 Actor Situation Tracker — typed projection builders (Phase 2).

This module is the single legal place where consumers obtain a typed,
prompt-ready ``W5Projection`` derived from a ``W5Snapshot``. Raw persisted
``w5_history`` dicts are coerced through ``W5Snapshot.from_dict`` first; the
projection is never built from a free-form dict in consumer code.

Phase 2 scope (ADR-0063 + ``docs/MVPs/w5_actor_situation_migration.md``):

- The narrator projection consumes only the five W5 dimensions.
- ``how_summary`` is first-class and must not be folded into ``what_summary``.
- ``why_summary`` may include INFERRED / DIRECTOR_ASSIGNED / CANONICAL /
  DECLARED facts, but never OBSERVED (see ``why_truth_level_is_admitted``).
- ``source_attribution`` and ``truth_attribution`` are populated per
  ``summary_path`` so the narrator can be audited and so admin can later
  diff against the legacy ``transition_from_previous`` block.
- Raw ledgers (per-fact dicts) are **not** exposed; only compact summaries.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ai_stack.w5_actor_situation.models import (
    W5_PROJECTION_SCHEMA_VERSION,
    W5ActorSituation,
    W5Dimension,
    W5Fact,
    W5FactStatus,
    W5Projection,
    W5ProjectionConsumer,
    W5Snapshot,
    W5TruthLevel,
    why_truth_level_is_admitted,
)


_WHERE_PROMOTED_KEYS = ("scene_location",)


def _coerce_snapshot(snapshot: W5Snapshot | Mapping[str, Any] | None) -> W5Snapshot | None:
    """Normalize raw persisted dicts into a typed ``W5Snapshot``.

    Consumers may pass either ``W5Snapshot`` (already typed) or a serialized
    payload as found in ``StorySession.w5_latest_snapshot``. We coerce here so
    that downstream code never reads raw dicts directly — the contract for
    consumers is the typed projection, not the persisted dict.
    """

    if snapshot is None:
        return None
    if isinstance(snapshot, W5Snapshot):
        return snapshot
    if isinstance(snapshot, Mapping):
        return W5Snapshot.from_dict(dict(snapshot))
    raise TypeError(
        "build_w5_projection_for_narrator: snapshot must be W5Snapshot, "
        "Mapping, or None; got %r" % type(snapshot).__name__
    )


def _active_facts(facts: tuple[W5Fact, ...]) -> list[W5Fact]:
    return [f for f in facts if f.status is W5FactStatus.ACTIVE]


def _pick_strongest(facts: list[W5Fact], key: str) -> W5Fact | None:
    """Pick the strongest-truth-level active fact for ``(dimension, key)``."""

    truth_rank = {
        W5TruthLevel.CANONICAL: 5,
        W5TruthLevel.OBSERVED: 4,
        W5TruthLevel.DIRECTOR_ASSIGNED: 3,
        W5TruthLevel.DECLARED: 2,
        W5TruthLevel.INFERRED: 1,
        W5TruthLevel.PROJECTED: 0,
    }
    candidates = [f for f in facts if f.key == key]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda f: (
            truth_rank.get(f.truth_level, 0),
            int(f.last_confirmed_turn),
        ),
    )


def _record_attribution(
    *,
    source_attribution: dict[str, str],
    truth_attribution: dict[str, str],
    path: str,
    fact: W5Fact,
) -> None:
    source_attribution[path] = fact.source.value
    truth_attribution[path] = fact.truth_level.value


def _actor_candidates(
    actor_id: str | None,
    actor_id_aliases: Iterable[str] | None,
) -> list[str]:
    candidates: list[str] = []
    for raw in (actor_id, *(actor_id_aliases or ())):
        if not isinstance(raw, str):
            continue
        value = raw.strip()
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def _select_actor_id(
    snapshot: W5Snapshot,
    *,
    actor_id: str | None,
    actor_id_aliases: Iterable[str] | None,
) -> str:
    candidates = _actor_candidates(actor_id, actor_id_aliases)
    for candidate in candidates:
        if candidate in snapshot.actors:
            return candidate

    by_lower = {aid.lower(): aid for aid in snapshot.actors}
    for candidate in candidates:
        found = by_lower.get(candidate.lower())
        if found is not None:
            return found

    return sorted(snapshot.actors.keys())[0]


def _who_summary(
    situation: W5ActorSituation,
    *,
    source_attribution: dict[str, str],
    truth_attribution: dict[str, str],
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "actor_id": situation.actor_id,
        "actor_type": situation.actor_type.value,
        "actor_role_in_scene": situation.actor_role_in_scene,
        "involvement_type": situation.involvement_type,
    }
    # The W5ActorSituation does not currently carry a who tuple in Phase 1;
    # we attribute the situation's structural fields from the canonical
    # CANONICAL_CONTENT lane.
    if situation.actor_role_in_scene is not None:
        source_attribution["who_summary.actor_role_in_scene"] = "canonical_content"
        truth_attribution["who_summary.actor_role_in_scene"] = "canonical"
    if situation.involvement_type is not None:
        source_attribution["who_summary.involvement_type"] = "canonical_content"
        truth_attribution["who_summary.involvement_type"] = "canonical"
    source_attribution["who_summary.actor_type"] = "canonical_content"
    truth_attribution["who_summary.actor_type"] = "canonical"
    return summary


def _where_summary(
    situation: W5ActorSituation,
    *,
    previous_situation: W5ActorSituation | None,
    source_attribution: dict[str, str],
    truth_attribution: dict[str, str],
) -> dict[str, Any]:
    where_active = _active_facts(situation.where)
    summary: dict[str, Any] = {
        "actor_id": situation.actor_id,
        "facts": {},
    }
    current_location: str | None = None
    for key in _WHERE_PROMOTED_KEYS:
        fact = _pick_strongest(where_active, key)
        if fact is None:
            continue
        summary["facts"][key] = fact.value
        if key == "scene_location" and isinstance(fact.value, str):
            current_location = fact.value
            summary["current_location"] = fact.value
        _record_attribution(
            source_attribution=source_attribution,
            truth_attribution=truth_attribution,
            path=f"where_summary.facts.{key}",
            fact=fact,
        )

    previous_location: str | None = None
    if previous_situation is not None:
        prev_fact = _pick_strongest(
            _active_facts(previous_situation.where), "scene_location"
        )
        if prev_fact is not None and isinstance(prev_fact.value, str):
            previous_location = prev_fact.value
    if previous_location is not None:
        summary["previous_location"] = previous_location

    location_changed = (
        current_location is not None
        and previous_location is not None
        and current_location != previous_location
    )
    summary["location_changed"] = bool(location_changed)
    source_attribution["where_summary.location_changed"] = "derived_from_where_facts"
    truth_attribution["where_summary.location_changed"] = "observed"
    return summary


def _what_summary(
    situation: W5ActorSituation,
    *,
    source_attribution: dict[str, str],
    truth_attribution: dict[str, str],
) -> dict[str, Any]:
    summary: dict[str, Any] = {"actor_id": situation.actor_id, "facts": {}}
    active = _active_facts(situation.what)
    # Promote a stable subset of keys; preserve action/interaction/target.
    for key in ("interaction_type", "current_action", "target_actor_id", "target_object_id"):
        fact = _pick_strongest(active, key)
        if fact is None:
            continue
        summary["facts"][key] = fact.value
        _record_attribution(
            source_attribution=source_attribution,
            truth_attribution=truth_attribution,
            path=f"what_summary.facts.{key}",
            fact=fact,
        )
    return summary


def _how_summary(
    situation: W5ActorSituation,
    *,
    source_attribution: dict[str, str],
    truth_attribution: dict[str, str],
) -> dict[str, Any]:
    summary: dict[str, Any] = {"actor_id": situation.actor_id, "facts": {}}
    active = _active_facts(situation.how)
    seen: set[str] = set()
    for fact in active:
        key = fact.key
        if key in seen:
            continue
        chosen = _pick_strongest(active, key)
        if chosen is None:
            continue
        seen.add(key)
        summary["facts"][key] = chosen.value
        _record_attribution(
            source_attribution=source_attribution,
            truth_attribution=truth_attribution,
            path=f"how_summary.facts.{key}",
            fact=chosen,
        )
    return summary


def _why_summary(
    situation: W5ActorSituation,
    *,
    source_attribution: dict[str, str],
    truth_attribution: dict[str, str],
) -> dict[str, Any]:
    summary: dict[str, Any] = {"actor_id": situation.actor_id, "facts": {}}
    active = _active_facts(situation.why)
    seen: set[str] = set()
    for fact in active:
        if not why_truth_level_is_admitted(fact.truth_level):
            # Defensive: model __post_init__ already forbids OBSERVED why.*,
            # but the projection must not leak any non-admitted entries even
            # if a future relaxation lands inconsistently.
            continue
        key = fact.key
        if key in seen:
            continue
        chosen = _pick_strongest(active, key)
        if chosen is None or not why_truth_level_is_admitted(chosen.truth_level):
            continue
        seen.add(key)
        summary["facts"][key] = chosen.value
        _record_attribution(
            source_attribution=source_attribution,
            truth_attribution=truth_attribution,
            path=f"why_summary.facts.{key}",
            fact=chosen,
        )
    return summary


def build_w5_projection_for_narrator(
    snapshot: W5Snapshot | Mapping[str, Any] | None,
    *,
    actor_id: str | None = None,
    actor_id_aliases: Iterable[str] | None = None,
    previous_snapshot: W5Snapshot | Mapping[str, Any] | None = None,
) -> W5Projection:
    """Build the narrator-facing W5 projection.

    - ``snapshot`` may be a ``W5Snapshot`` or a persisted dict; raw dicts are
      coerced through ``W5Snapshot.from_dict``.
    - ``actor_id`` selects which actor the projection centers on; if omitted,
      the first sorted actor_id present in the snapshot is used. Callers in
      Phase 2 typically pass the selected human actor.
    - ``actor_id_aliases`` lets runtime code pass canonical role aliases
      without reading raw persisted W5 dicts. The builder still resolves
      against the typed ``W5Snapshot``.
    - ``previous_snapshot`` is used only to detect ``location_changed`` parity
      against the prior persisted snapshot — same semantics as the legacy
      ``transition_from_previous.location_changed`` flag.

    The returned ``W5Projection`` carries compact, prompt-ready summaries —
    not raw per-fact ledgers — and always records ``source_attribution`` and
    ``truth_attribution`` for narrator audit.
    """

    typed_snapshot = _coerce_snapshot(snapshot)
    typed_previous = _coerce_snapshot(previous_snapshot)

    if typed_snapshot is None or not typed_snapshot.actors:
        return W5Projection(
            schema_version=W5_PROJECTION_SCHEMA_VERSION,
            target_consumer=W5ProjectionConsumer.NARRATOR,
            actor_id=actor_id,
            who_summary={},
            where_summary={"location_changed": False},
            what_summary={},
            how_summary={},
            why_summary={},
            source_attribution={
                "where_summary.location_changed": "derived_from_where_facts",
            },
            truth_attribution={
                "where_summary.location_changed": "observed",
            },
        )

    chosen_actor_id = _select_actor_id(
        typed_snapshot,
        actor_id=actor_id,
        actor_id_aliases=actor_id_aliases,
    )
    situation = typed_snapshot.actors[chosen_actor_id]
    previous_situation = (
        typed_previous.actors.get(chosen_actor_id) if typed_previous is not None else None
    )

    source_attribution: dict[str, str] = {}
    truth_attribution: dict[str, str] = {}

    who_summary = _who_summary(
        situation,
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
    )
    where_summary = _where_summary(
        situation,
        previous_situation=previous_situation,
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
    )
    what_summary = _what_summary(
        situation,
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
    )
    how_summary = _how_summary(
        situation,
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
    )
    why_summary = _why_summary(
        situation,
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
    )

    return W5Projection(
        schema_version=W5_PROJECTION_SCHEMA_VERSION,
        target_consumer=W5ProjectionConsumer.NARRATOR,
        actor_id=chosen_actor_id,
        who_summary=who_summary,
        where_summary=where_summary,
        what_summary=what_summary,
        how_summary=how_summary,
        why_summary=why_summary,
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
    )


__all__ = ["build_w5_projection_for_narrator"]
