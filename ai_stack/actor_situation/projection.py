"""W5 Actor Situation Tracker — typed projection builders (Phase 2/3A/3B).

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

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from ai_stack.actor_situation.models import (
    W5_PROJECTION_SCHEMA_VERSION,
    W5ActorSituation,
    W5ActorType,
    W5Dimension,
    W5Fact,
    W5FactStatus,
    W5Projection,
    W5ProjectionConsumer,
    W5Snapshot,
    W5TruthLevel,
    W5VisibilityScope,
    why_truth_level_is_admitted,
)


_WHERE_PROMOTED_KEYS = ("scene_location",)
_DIRECTOR_WHERE_KEYS = ("scene_location", "visibility_audibility")


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


def _record_structural_attribution(
    *,
    source_attribution: dict[str, str],
    truth_attribution: dict[str, str],
    path: str,
    source: str = "w5_snapshot",
    truth: str = "observed",
) -> None:
    source_attribution[path] = source
    truth_attribution[path] = truth


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


def _npc_can_read_fact(
    *,
    fact: W5Fact,
    situation: W5ActorSituation,
    target_actor_id: str,
    is_target_actor: bool,
) -> bool:
    if fact.visibility is W5VisibilityScope.PUBLIC:
        return True
    if fact.visibility in {W5VisibilityScope.GM_ONLY, W5VisibilityScope.DIRECTOR_ONLY}:
        return False
    if is_target_actor:
        return fact.visibility is W5VisibilityScope.PRIVATE_TO_ACTOR
    if situation.actor_type is W5ActorType.HUMAN:
        # Player-private facts never leak into NPC projections.
        return False
    return (
        fact.visibility is W5VisibilityScope.PRIVATE_TO_ACTOR
        and target_actor_id in set(fact.actor_knowledge_scope)
    )


def _npc_dimension_summary(
    *,
    dimension_name: str,
    target_actor_id: str,
    target_situation: W5ActorSituation,
    all_situations: Mapping[str, W5ActorSituation],
    source_attribution: dict[str, str],
    truth_attribution: dict[str, str],
) -> dict[str, Any]:
    own_facts = _active_facts(getattr(target_situation, dimension_name))
    summary: dict[str, Any] = {"actor_id": target_actor_id, "facts": {}}
    seen: set[str] = set()
    for fact in own_facts:
        if fact.key in seen:
            continue
        chosen = _pick_strongest(own_facts, fact.key)
        if chosen is None:
            continue
        if dimension_name == "why" and not why_truth_level_is_admitted(chosen.truth_level):
            continue
        if not _npc_can_read_fact(
            fact=chosen,
            situation=target_situation,
            target_actor_id=target_actor_id,
            is_target_actor=True,
        ):
            continue
        seen.add(chosen.key)
        summary["facts"][chosen.key] = chosen.value
        _record_attribution(
            source_attribution=source_attribution,
            truth_attribution=truth_attribution,
            path=f"{dimension_name}_summary.facts.{chosen.key}",
            fact=chosen,
        )

    known_actors: dict[str, Any] = {}
    for actor_id in sorted(all_situations.keys()):
        if actor_id == target_actor_id:
            continue
        situation = all_situations[actor_id]
        active = _active_facts(getattr(situation, dimension_name))
        facts: dict[str, Any] = {}
        seen_other: set[str] = set()
        for fact in active:
            if fact.key in seen_other:
                continue
            chosen = _pick_strongest(active, fact.key)
            if chosen is None:
                continue
            if dimension_name == "why" and not why_truth_level_is_admitted(chosen.truth_level):
                continue
            if not _npc_can_read_fact(
                fact=chosen,
                situation=situation,
                target_actor_id=target_actor_id,
                is_target_actor=False,
            ):
                continue
            seen_other.add(chosen.key)
            facts[chosen.key] = chosen.value
            _record_attribution(
                source_attribution=source_attribution,
                truth_attribution=truth_attribution,
                path=f"{dimension_name}_summary.known_actors.{actor_id}.facts.{chosen.key}",
                fact=chosen,
            )
        if facts:
            known_actors[actor_id] = {"actor_id": actor_id, "facts": facts}
    if known_actors:
        summary["known_actors"] = known_actors
    return summary


def _prefixed_dimension_summary(
    *,
    prefix: str,
    builder: Callable[..., dict[str, Any]],
    situation: W5ActorSituation,
    source_attribution: dict[str, str],
    truth_attribution: dict[str, str],
) -> dict[str, Any]:
    local_sources: dict[str, str] = {}
    local_truths: dict[str, str] = {}
    summary = builder(
        situation,
        source_attribution=local_sources,
        truth_attribution=local_truths,
    )
    for path, value in local_sources.items():
        source_attribution[f"{prefix}.{path}"] = value
    for path, value in local_truths.items():
        truth_attribution[f"{prefix}.{path}"] = value
    return summary


def _director_where_actor_summary(
    situation: W5ActorSituation,
    *,
    source_attribution: dict[str, str],
    truth_attribution: dict[str, str],
) -> tuple[dict[str, Any], str | None]:
    active = _active_facts(situation.where)
    actor_path = f"where_summary.actors.{situation.actor_id}"
    summary: dict[str, Any] = {
        "actor_id": situation.actor_id,
        "where": {},
        "freshness_status": situation.freshness_status.value,
        "last_confirmed_turn": int(situation.last_confirmed_turn),
        "fact_status": {},
    }
    _record_structural_attribution(
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
        path=f"{actor_path}.freshness_status",
    )
    _record_structural_attribution(
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
        path=f"{actor_path}.last_confirmed_turn",
    )

    scene_location: str | None = None
    for key in _DIRECTOR_WHERE_KEYS:
        fact = _pick_strongest(active, key)
        if fact is None:
            continue
        summary["where"][key] = fact.value
        summary["fact_status"][key] = fact.status.value
        if key == "scene_location" and isinstance(fact.value, str) and fact.value.strip():
            scene_location = fact.value.strip()
        _record_attribution(
            source_attribution=source_attribution,
            truth_attribution=truth_attribution,
            path=f"{actor_path}.where.{key}",
            fact=fact,
        )
        _record_attribution(
            source_attribution=source_attribution,
            truth_attribution=truth_attribution,
            path=f"{actor_path}.fact_status.{key}",
            fact=fact,
        )
    return summary, scene_location


def _empty_projection(target_consumer: W5ProjectionConsumer) -> W5Projection:
    if target_consumer is W5ProjectionConsumer.DIRECTOR:
        return W5Projection(
            schema_version=W5_PROJECTION_SCHEMA_VERSION,
            target_consumer=W5ProjectionConsumer.DIRECTOR,
            actor_id=None,
            who_summary={"actors": {}, "actor_ids": []},
            where_summary={
                "actors": {},
                "derived_actor_locations": {},
                "w5_snapshot_id": None,
            },
            what_summary={"actors": {}},
            how_summary={"actors": {}},
            why_summary={"actors": {}},
            source_attribution={
                "where_summary.derived_actor_locations": "derived_from_where_facts",
            },
            truth_attribution={
                "where_summary.derived_actor_locations": "observed",
            },
        )
    return W5Projection(
        schema_version=W5_PROJECTION_SCHEMA_VERSION,
        target_consumer=W5ProjectionConsumer.NARRATOR,
        actor_id=None,
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
        empty = _empty_projection(W5ProjectionConsumer.NARRATOR)
        return W5Projection(
            schema_version=empty.schema_version,
            target_consumer=empty.target_consumer,
            actor_id=actor_id,
            who_summary=empty.who_summary,
            where_summary=empty.where_summary,
            what_summary=empty.what_summary,
            how_summary=empty.how_summary,
            why_summary=empty.why_summary,
            source_attribution=empty.source_attribution,
            truth_attribution=empty.truth_attribution,
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


def build_w5_projection_for_director(
    snapshot: W5Snapshot | Mapping[str, Any] | None,
) -> W5Projection:
    """Build the Director/Gathering W5 projection.

    Phase 3A keeps ADR-0061 pause semantics anchored in
    ``compute_gathering_state``. This projection only replaces the upstream
    actor-location input source: it exposes a compact per-actor ``where``
    summary and a compatibility ``derived_actor_locations`` map. Raw persisted
    W5 dicts are coerced through ``W5Snapshot.from_dict`` before any field is
    read.
    """

    typed_snapshot = _coerce_snapshot(snapshot)
    if typed_snapshot is None or not typed_snapshot.actors:
        return _empty_projection(W5ProjectionConsumer.DIRECTOR)

    source_attribution: dict[str, str] = {}
    truth_attribution: dict[str, str] = {}
    who_actors: dict[str, Any] = {}
    where_actors: dict[str, Any] = {}
    what_actors: dict[str, Any] = {}
    how_actors: dict[str, Any] = {}
    why_actors: dict[str, Any] = {}
    derived_actor_locations: dict[str, str] = {}

    for actor_id in sorted(typed_snapshot.actors.keys()):
        situation = typed_snapshot.actors[actor_id]
        who_actors[actor_id] = _prefixed_dimension_summary(
            prefix=f"who_summary.actors.{actor_id}",
            builder=_who_summary,
            situation=situation,
            source_attribution=source_attribution,
            truth_attribution=truth_attribution,
        )
        where_summary, scene_location = _director_where_actor_summary(
            situation,
            source_attribution=source_attribution,
            truth_attribution=truth_attribution,
        )
        where_actors[actor_id] = where_summary
        if scene_location is not None:
            derived_actor_locations[actor_id] = scene_location
            _record_structural_attribution(
                source_attribution=source_attribution,
                truth_attribution=truth_attribution,
                path=f"where_summary.derived_actor_locations.{actor_id}",
                source="derived_from_where_facts",
            )
        what_actors[actor_id] = _prefixed_dimension_summary(
            prefix=f"what_summary.actors.{actor_id}",
            builder=_what_summary,
            situation=situation,
            source_attribution=source_attribution,
            truth_attribution=truth_attribution,
        )
        how_actors[actor_id] = _prefixed_dimension_summary(
            prefix=f"how_summary.actors.{actor_id}",
            builder=_how_summary,
            situation=situation,
            source_attribution=source_attribution,
            truth_attribution=truth_attribution,
        )
        why_actors[actor_id] = _prefixed_dimension_summary(
            prefix=f"why_summary.actors.{actor_id}",
            builder=_why_summary,
            situation=situation,
            source_attribution=source_attribution,
            truth_attribution=truth_attribution,
        )

    _record_structural_attribution(
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
        path="where_summary.w5_snapshot_id",
    )

    return W5Projection(
        schema_version=W5_PROJECTION_SCHEMA_VERSION,
        target_consumer=W5ProjectionConsumer.DIRECTOR,
        actor_id=None,
        who_summary={
            "actors": who_actors,
            "actor_ids": sorted(typed_snapshot.actors.keys()),
        },
        where_summary={
            "actors": where_actors,
            "derived_actor_locations": derived_actor_locations,
            "w5_snapshot_id": typed_snapshot.snapshot_id,
        },
        what_summary={"actors": what_actors},
        how_summary={"actors": how_actors},
        why_summary={"actors": why_actors},
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
    )


def build_w5_projection_for_npc(
    snapshot: W5Snapshot | Mapping[str, Any] | None,
    *,
    actor_id: str,
) -> W5Projection:
    """Build an actor-specific NPC-facing W5 projection.

    The target NPC receives its own W5 facts plus only those other-actor facts
    visible to it through public visibility or explicit ``actor_knowledge_scope``.
    Raw persisted dicts are coerced through ``W5Snapshot.from_dict`` before any
    field is read.
    """

    target_actor_id = str(actor_id or "").strip()
    if not target_actor_id:
        raise ValueError("build_w5_projection_for_npc requires a non-empty actor_id")
    typed_snapshot = _coerce_snapshot(snapshot)
    if typed_snapshot is None or target_actor_id not in typed_snapshot.actors:
        raise ValueError(f"npc_actor_not_found_in_w5_snapshot:{target_actor_id}")
    target = typed_snapshot.actors[target_actor_id]
    if target.actor_type is not W5ActorType.NPC:
        raise ValueError(f"w5_npc_projection_target_not_npc:{target_actor_id}")

    source_attribution: dict[str, str] = {}
    truth_attribution: dict[str, str] = {}

    who_summary = _who_summary(
        target,
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
    )
    _record_structural_attribution(
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
        path="where_summary.w5_snapshot_id",
    )
    where_summary = _npc_dimension_summary(
        dimension_name="where",
        target_actor_id=target_actor_id,
        target_situation=target,
        all_situations=typed_snapshot.actors,
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
    )
    where_summary["w5_snapshot_id"] = typed_snapshot.snapshot_id
    what_summary = _npc_dimension_summary(
        dimension_name="what",
        target_actor_id=target_actor_id,
        target_situation=target,
        all_situations=typed_snapshot.actors,
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
    )
    how_summary = _npc_dimension_summary(
        dimension_name="how",
        target_actor_id=target_actor_id,
        target_situation=target,
        all_situations=typed_snapshot.actors,
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
    )
    why_summary = _npc_dimension_summary(
        dimension_name="why",
        target_actor_id=target_actor_id,
        target_situation=target,
        all_situations=typed_snapshot.actors,
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
    )

    return W5Projection(
        schema_version=W5_PROJECTION_SCHEMA_VERSION,
        target_consumer=W5ProjectionConsumer.NPC,
        actor_id=target_actor_id,
        who_summary=who_summary,
        where_summary=where_summary,
        what_summary=what_summary,
        how_summary=how_summary,
        why_summary=why_summary,
        source_attribution=source_attribution,
        truth_attribution=truth_attribution,
    )


__all__ = [
    "build_w5_projection_for_director",
    "build_w5_projection_for_narrator",
    "build_w5_projection_for_npc",
]
