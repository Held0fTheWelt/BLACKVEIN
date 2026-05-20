"""W5 Actor Tracking — pure extractor.

The single legal producer of W5 facts. Pure, deterministic, no I/O, no LLM
calls, no mutation of inputs. Phase 1: shadow-only. See ADR-0063 and
``docs/MVPs/w5_actor_tracking_migration.md``.

Truth/source rules enforced here:

- ``committed_action`` / ``participant_state_move`` may produce OBSERVED
  ``where`` / ``what`` only when there is a committed event with a valid
  ``canonical_turn_id`` (the caller must only invoke this after commit).
- ``free_player_action_resolution`` produces DECLARED facts until committed.
- ``character_mind_record`` / ``npc_agency_simulation`` produce INFERRED
  ``how`` / ``why`` facts.
- ``souffleuse`` / ``narrator_composition`` are projection-lane only here
  and **must not** produce OBSERVED facts. Phase 1 does not consume them.
- ``admin_override`` is audited and **must never** produce OBSERVED.
- The extractor does not advance canonical path, consume mandatory beats,
  or authorize actor-lane behavior.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from ai_stack.actor_tracking.models import (
    W5_FACT_SCHEMA_VERSION,
    W5_SNAPSHOT_SCHEMA_VERSION,
    W5ActorSituation,
    W5ActorType,
    W5Conflict,
    W5ConflictResolutionStatus,
    W5Dimension,
    W5Fact,
    W5FactStatus,
    W5FreshnessStatus,
    W5Snapshot,
    W5Source,
    W5TruthLevel,
    W5VisibilityScope,
)


_DEFAULT_CONFIDENCE = {
    W5TruthLevel.CANONICAL: 1.0,
    W5TruthLevel.OBSERVED: 1.0,
    W5TruthLevel.DIRECTOR_ASSIGNED: 0.9,
    W5TruthLevel.DECLARED: 0.6,
    W5TruthLevel.INFERRED: 0.4,
}


_HOW_KEYS = ("tone", "manner", "intensity", "pace", "physicality", "method", "style")
_WHY_KEYS = ("motive", "trigger", "goal", "pressure", "dramatic_function", "reaction_to")


def _stable_hash(*parts: Any) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _fact_id(
    *,
    snapshot_seed: str,
    actor_id: str,
    dimension: W5Dimension,
    key: str,
    source: W5Source,
) -> str:
    return "w5f_" + _stable_hash(
        snapshot_seed, actor_id, dimension.value, key, source.value
    )


def _snapshot_id(*, story_session_id: str, turn_number: int, derived_from: Iterable[str]) -> str:
    return "w5s_" + _stable_hash(story_session_id, int(turn_number), tuple(sorted(derived_from)))


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _confidence_for(truth: W5TruthLevel) -> float:
    return _DEFAULT_CONFIDENCE.get(truth, 1.0)


def _committed_event_id(committed_event: dict[str, Any]) -> str | None:
    for key in ("canonical_turn_id", "committed_event_id", "event_id"):
        value = committed_event.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _build_fact(
    *,
    snapshot_seed: str,
    actor_id: str,
    dimension: W5Dimension,
    key: str,
    value: Any,
    source: W5Source,
    truth_level: W5TruthLevel,
    turn_number: int,
    visibility: W5VisibilityScope = W5VisibilityScope.PUBLIC,
    source_event_id: str | None = None,
    confidence: float | None = None,
    status: W5FactStatus = W5FactStatus.ACTIVE,
) -> W5Fact:
    return W5Fact(
        schema_version=W5_FACT_SCHEMA_VERSION,
        fact_id=_fact_id(
            snapshot_seed=snapshot_seed,
            actor_id=actor_id,
            dimension=dimension,
            key=key,
            source=source,
        ),
        actor_id=actor_id,
        dimension=dimension,
        key=key,
        value=value,
        source=source,
        source_event_id=source_event_id,
        truth_level=truth_level,
        confidence=(
            float(_confidence_for(truth_level)) if confidence is None else float(confidence)
        ),
        valid_from_turn=int(turn_number),
        valid_until_turn=None,
        last_confirmed_turn=int(turn_number),
        visibility=visibility,
        actor_knowledge_scope=(),
        status=status,
        superseded_by_fact_id=None,
        contradicted_by_fact_id=None,
    )


def _actor_type_from_lane(lane_entry: dict[str, Any]) -> W5ActorType:
    raw = str(lane_entry.get("actor_type") or lane_entry.get("type") or "").strip().lower()
    if raw == "human":
        return W5ActorType.HUMAN
    if raw == "narrator":
        return W5ActorType.NARRATOR
    return W5ActorType.NPC


def _extract_where_observed(
    *,
    snapshot_seed: str,
    environment_state_after: dict[str, Any],
    committed_event_id: str | None,
    turn_number: int,
) -> dict[str, list[W5Fact]]:
    """OBSERVED ``where`` facts from committed substrate only."""

    out: dict[str, list[W5Fact]] = {}
    actor_locations = (
        environment_state_after.get("actor_locations")
        if isinstance(environment_state_after.get("actor_locations"), dict)
        else {}
    )
    for actor_id in sorted(str(a) for a in actor_locations.keys()):
        location_id = actor_locations[actor_id]
        if not isinstance(location_id, str) or not location_id.strip():
            continue
        fact = _build_fact(
            snapshot_seed=snapshot_seed,
            actor_id=actor_id,
            dimension=W5Dimension.WHERE,
            key="scene_location",
            value=location_id,
            source=W5Source.PARTICIPANT_STATE_MOVE,
            truth_level=W5TruthLevel.OBSERVED,
            turn_number=turn_number,
            source_event_id=committed_event_id,
        )
        out.setdefault(actor_id, []).append(fact)
    return out


def _extract_what_observed_from_event(
    *,
    snapshot_seed: str,
    committed_event: dict[str, Any],
    committed_event_id: str | None,
    turn_number: int,
) -> dict[str, list[W5Fact]]:
    """OBSERVED ``what`` facts from a committed event's narrative_commit shape.

    Only emits when the event is committed and carries a structured action
    summary that names a specific actor. Free-text narrator prose is **not**
    a source of OBSERVED facts.
    """

    out: dict[str, list[W5Fact]] = {}
    if committed_event_id is None:
        return out
    narrative_commit = _as_dict(committed_event.get("narrative_commit"))
    actor_summary = _as_dict(committed_event.get("actor_turn_summary"))
    committed_actor = (
        actor_summary.get("selected_actor_id")
        or narrative_commit.get("selected_actor_id")
        or actor_summary.get("actor_id")
    )
    action_kind = (
        narrative_commit.get("action_kind")
        or actor_summary.get("action_kind")
    )
    action_verb = narrative_commit.get("action_verb") or actor_summary.get("action_verb")
    target_actor_id = narrative_commit.get("target_actor_id") or actor_summary.get("target_actor_id")
    if not isinstance(committed_actor, str) or not committed_actor.strip():
        return out
    if isinstance(action_kind, str) and action_kind.strip():
        out.setdefault(committed_actor, []).append(
            _build_fact(
                snapshot_seed=snapshot_seed,
                actor_id=committed_actor,
                dimension=W5Dimension.WHAT,
                key="interaction_type",
                value=action_kind,
                source=W5Source.COMMITTED_ACTION,
                truth_level=W5TruthLevel.OBSERVED,
                turn_number=turn_number,
                source_event_id=committed_event_id,
            )
        )
    if isinstance(action_verb, str) and action_verb.strip():
        out.setdefault(committed_actor, []).append(
            _build_fact(
                snapshot_seed=snapshot_seed,
                actor_id=committed_actor,
                dimension=W5Dimension.WHAT,
                key="current_action",
                value=action_verb,
                source=W5Source.COMMITTED_ACTION,
                truth_level=W5TruthLevel.OBSERVED,
                turn_number=turn_number,
                source_event_id=committed_event_id,
            )
        )
    if isinstance(target_actor_id, str) and target_actor_id.strip():
        out.setdefault(committed_actor, []).append(
            _build_fact(
                snapshot_seed=snapshot_seed,
                actor_id=committed_actor,
                dimension=W5Dimension.WHAT,
                key="target_actor_id",
                value=target_actor_id,
                source=W5Source.COMMITTED_ACTION,
                truth_level=W5TruthLevel.OBSERVED,
                turn_number=turn_number,
                source_event_id=committed_event_id,
            )
        )
    return out


def _extract_what_declared(
    *,
    snapshot_seed: str,
    free_player_action_resolution: dict[str, Any] | None,
    turn_number: int,
) -> dict[str, list[W5Fact]]:
    """DECLARED ``what`` facts from free-player resolution before commit."""

    out: dict[str, list[W5Fact]] = {}
    if not isinstance(free_player_action_resolution, dict):
        return out
    actor_id = free_player_action_resolution.get("selected_actor_id") or free_player_action_resolution.get("actor_id")
    declared_verb = free_player_action_resolution.get("declared_verb") or free_player_action_resolution.get("verb")
    declared_target = free_player_action_resolution.get("declared_target_id")
    commit_applied = bool(free_player_action_resolution.get("commit_applied"))
    if commit_applied:
        # The committed lane will handle OBSERVED facts.
        return out
    if not isinstance(actor_id, str) or not actor_id.strip():
        return out
    if isinstance(declared_verb, str) and declared_verb.strip():
        out.setdefault(actor_id, []).append(
            _build_fact(
                snapshot_seed=snapshot_seed,
                actor_id=actor_id,
                dimension=W5Dimension.WHAT,
                key="current_action",
                value=declared_verb,
                source=W5Source.FREE_PLAYER_ACTION_RESOLUTION,
                truth_level=W5TruthLevel.DECLARED,
                turn_number=turn_number,
            )
        )
    if isinstance(declared_target, str) and declared_target.strip():
        out.setdefault(actor_id, []).append(
            _build_fact(
                snapshot_seed=snapshot_seed,
                actor_id=actor_id,
                dimension=W5Dimension.WHAT,
                key="target_object_id",
                value=declared_target,
                source=W5Source.FREE_PLAYER_ACTION_RESOLUTION,
                truth_level=W5TruthLevel.DECLARED,
                turn_number=turn_number,
            )
        )
    return out


def _extract_how_first_class(
    *,
    snapshot_seed: str,
    committed_event: dict[str, Any],
    actor_lane_context: dict[str, Any] | None,
    npc_agency_simulation: dict[str, Any] | None,
    turn_number: int,
    committed_event_id: str | None,
) -> dict[str, list[W5Fact]]:
    """HOW facts (tone/manner/intensity/pace/physicality/method/style).

    Sourced from committed event signals (OBSERVED), actor lane manner
    annotations (DIRECTOR_ASSIGNED), or NPC agency simulation (INFERRED).
    Always emitted under ``dimension="how"`` — never collapsed into ``what``.
    """

    out: dict[str, list[W5Fact]] = {}

    # OBSERVED: committed event may carry an explicit how_signals dict.
    how_signals = _as_dict(committed_event.get("how_signals"))
    if how_signals and committed_event_id is not None:
        actor_id = (
            committed_event.get("actor_id")
            or _as_dict(committed_event.get("actor_turn_summary")).get("selected_actor_id")
        )
        if isinstance(actor_id, str) and actor_id.strip():
            for key in _HOW_KEYS:
                value = how_signals.get(key)
                if value is None:
                    continue
                out.setdefault(actor_id, []).append(
                    _build_fact(
                        snapshot_seed=snapshot_seed,
                        actor_id=actor_id,
                        dimension=W5Dimension.HOW,
                        key=key,
                        value=value,
                        source=W5Source.COMMITTED_ACTION,
                        truth_level=W5TruthLevel.OBSERVED,
                        turn_number=turn_number,
                        source_event_id=committed_event_id,
                    )
                )

    # DIRECTOR_ASSIGNED: actor lane context manner annotations.
    if isinstance(actor_lane_context, dict):
        lanes = (
            actor_lane_context.get("actor_lanes")
            if isinstance(actor_lane_context.get("actor_lanes"), dict)
            else {}
        )
        for actor_id in sorted(str(a) for a in lanes.keys()):
            lane = lanes[actor_id]
            if not isinstance(lane, dict):
                continue
            manner = lane.get("manner_directive") or lane.get("manner")
            if isinstance(manner, dict):
                for key in _HOW_KEYS:
                    value = manner.get(key)
                    if value is None:
                        continue
                    out.setdefault(actor_id, []).append(
                        _build_fact(
                            snapshot_seed=snapshot_seed,
                            actor_id=actor_id,
                            dimension=W5Dimension.HOW,
                            key=key,
                            value=value,
                            source=W5Source.DIRECTOR_COMPOSITION,
                            truth_level=W5TruthLevel.DIRECTOR_ASSIGNED,
                            turn_number=turn_number,
                        )
                    )

    # INFERRED: NPC agency simulation may suggest manner/tone.
    if isinstance(npc_agency_simulation, dict):
        plans = (
            npc_agency_simulation.get("plans")
            if isinstance(npc_agency_simulation.get("plans"), dict)
            else {}
        )
        for actor_id in sorted(str(a) for a in plans.keys()):
            plan = plans[actor_id]
            if not isinstance(plan, dict):
                continue
            manner = plan.get("how") or plan.get("manner")
            if isinstance(manner, dict):
                for key in _HOW_KEYS:
                    value = manner.get(key)
                    if value is None:
                        continue
                    out.setdefault(actor_id, []).append(
                        _build_fact(
                            snapshot_seed=snapshot_seed,
                            actor_id=actor_id,
                            dimension=W5Dimension.HOW,
                            key=key,
                            value=value,
                            source=W5Source.NPC_AGENCY_SIMULATION,
                            truth_level=W5TruthLevel.INFERRED,
                            turn_number=turn_number,
                        )
                    )

    return out


def _extract_why_inferred(
    *,
    snapshot_seed: str,
    character_mind_records: dict[str, Any] | None,
    npc_agency_simulation: dict[str, Any] | None,
    director_gathering_state: dict[str, Any] | None,
    turn_number: int,
) -> dict[str, list[W5Fact]]:
    """INFERRED ``why`` facts (motive, goal, pressure, dramatic_function, ...).

    Why is never OBSERVED in Phase 1. Director may set DIRECTOR_ASSIGNED
    dramatic_function. All else is INFERRED.
    """

    out: dict[str, list[W5Fact]] = {}

    if isinstance(character_mind_records, dict):
        records = (
            character_mind_records.get("records")
            if isinstance(character_mind_records.get("records"), dict)
            else character_mind_records
        )
        for actor_id in sorted(str(a) for a in records.keys()):
            record = records[actor_id]
            if not isinstance(record, dict):
                continue
            for key in _WHY_KEYS:
                value = record.get(key)
                if value is None:
                    continue
                out.setdefault(actor_id, []).append(
                    _build_fact(
                        snapshot_seed=snapshot_seed,
                        actor_id=actor_id,
                        dimension=W5Dimension.WHY,
                        key=key,
                        value=value,
                        source=W5Source.CHARACTER_MIND_RECORD,
                        truth_level=W5TruthLevel.INFERRED,
                        turn_number=turn_number,
                        visibility=W5VisibilityScope.PRIVATE_TO_ACTOR,
                    )
                )

    if isinstance(npc_agency_simulation, dict):
        plans = (
            npc_agency_simulation.get("plans")
            if isinstance(npc_agency_simulation.get("plans"), dict)
            else {}
        )
        for actor_id in sorted(str(a) for a in plans.keys()):
            plan = plans[actor_id]
            if not isinstance(plan, dict):
                continue
            why = plan.get("why") if isinstance(plan.get("why"), dict) else {}
            for key in _WHY_KEYS:
                value = why.get(key)
                if value is None:
                    continue
                out.setdefault(actor_id, []).append(
                    _build_fact(
                        snapshot_seed=snapshot_seed,
                        actor_id=actor_id,
                        dimension=W5Dimension.WHY,
                        key=key,
                        value=value,
                        source=W5Source.NPC_AGENCY_SIMULATION,
                        truth_level=W5TruthLevel.INFERRED,
                        turn_number=turn_number,
                        visibility=W5VisibilityScope.PRIVATE_TO_ACTOR,
                    )
                )

    if isinstance(director_gathering_state, dict):
        assignments = (
            director_gathering_state.get("dramatic_function_assignments")
            if isinstance(director_gathering_state.get("dramatic_function_assignments"), dict)
            else {}
        )
        for actor_id in sorted(str(a) for a in assignments.keys()):
            value = assignments[actor_id]
            if value is None:
                continue
            out.setdefault(actor_id, []).append(
                _build_fact(
                    snapshot_seed=snapshot_seed,
                    actor_id=actor_id,
                    dimension=W5Dimension.WHY,
                    key="dramatic_function",
                    value=value,
                    source=W5Source.DIRECTOR_GATHERING_STATE,
                    truth_level=W5TruthLevel.DIRECTOR_ASSIGNED,
                    turn_number=turn_number,
                    visibility=W5VisibilityScope.DIRECTOR_ONLY,
                )
            )

    return out


def _extract_who(
    *,
    snapshot_seed: str,
    actor_lane_context: dict[str, Any] | None,
    turn_number: int,
) -> dict[str, list[W5Fact]]:
    """WHO facts (actor_type, role_in_scene, involvement_type) from canonical lane."""

    out: dict[str, list[W5Fact]] = {}
    if not isinstance(actor_lane_context, dict):
        return out
    lanes = (
        actor_lane_context.get("actor_lanes")
        if isinstance(actor_lane_context.get("actor_lanes"), dict)
        else {}
    )
    for actor_id in sorted(str(a) for a in lanes.keys()):
        lane = lanes[actor_id]
        if not isinstance(lane, dict):
            continue
        actor_type = _actor_type_from_lane(lane)
        out.setdefault(actor_id, []).append(
            _build_fact(
                snapshot_seed=snapshot_seed,
                actor_id=actor_id,
                dimension=W5Dimension.WHO,
                key="actor_type",
                value=actor_type.value,
                source=W5Source.CANONICAL_CONTENT,
                truth_level=W5TruthLevel.CANONICAL,
                turn_number=turn_number,
            )
        )
        role = lane.get("role_in_scene") or lane.get("actor_role_in_scene")
        if isinstance(role, str) and role.strip():
            out.setdefault(actor_id, []).append(
                _build_fact(
                    snapshot_seed=snapshot_seed,
                    actor_id=actor_id,
                    dimension=W5Dimension.WHO,
                    key="actor_role_in_scene",
                    value=role,
                    source=W5Source.CANONICAL_CONTENT,
                    truth_level=W5TruthLevel.CANONICAL,
                    turn_number=turn_number,
                )
            )
        involvement = lane.get("involvement_type")
        if isinstance(involvement, str) and involvement.strip():
            out.setdefault(actor_id, []).append(
                _build_fact(
                    snapshot_seed=snapshot_seed,
                    actor_id=actor_id,
                    dimension=W5Dimension.WHO,
                    key="involvement_type",
                    value=involvement,
                    source=W5Source.CANONICAL_CONTENT,
                    truth_level=W5TruthLevel.CANONICAL,
                    turn_number=turn_number,
                )
            )
    return out


def _resolve_actor_type(
    *,
    who_facts: list[W5Fact],
    actor_lane_context: dict[str, Any] | None,
    actor_id: str,
) -> W5ActorType:
    for fact in who_facts:
        if fact.key == "actor_type" and isinstance(fact.value, str):
            try:
                return W5ActorType(fact.value)
            except ValueError:
                pass
    if isinstance(actor_lane_context, dict):
        lanes = (
            actor_lane_context.get("actor_lanes")
            if isinstance(actor_lane_context.get("actor_lanes"), dict)
            else {}
        )
        lane = lanes.get(actor_id) if isinstance(lanes.get(actor_id), dict) else None
        if lane is not None:
            return _actor_type_from_lane(lane)
    return W5ActorType.NPC


def _supersede_previous(
    *,
    actor_id: str,
    new_facts: list[W5Fact],
    previous_situations: dict[str, W5ActorSituation],
) -> list[W5Conflict]:
    """Build conflicts and mark supersession when new facts override prior ones.

    Phase 1 rule: DECLARED / INFERRED must never silently overwrite
    OBSERVED / CANONICAL. When new and prior facts share dimension+key but the
    new fact has a weaker truth level than the prior active fact, we emit a
    ``W5Conflict`` entry instead of replacing.
    """

    conflicts: list[W5Conflict] = []
    prior = previous_situations.get(actor_id)
    if prior is None:
        return conflicts
    truth_rank = {
        W5TruthLevel.CANONICAL: 5,
        W5TruthLevel.OBSERVED: 4,
        W5TruthLevel.DIRECTOR_ASSIGNED: 3,
        W5TruthLevel.DECLARED: 2,
        W5TruthLevel.INFERRED: 1,
        W5TruthLevel.PROJECTED: 0,
    }
    prior_index: dict[tuple[str, str], W5Fact] = {}
    for bucket in (prior.where, prior.what, prior.how, prior.why):
        for fact in bucket:
            if fact.status is not W5FactStatus.ACTIVE:
                continue
            prior_index[(fact.dimension.value, fact.key)] = fact
    for new_fact in new_facts:
        prior_fact = prior_index.get((new_fact.dimension.value, new_fact.key))
        if prior_fact is None:
            continue
        if truth_rank[new_fact.truth_level] < truth_rank[prior_fact.truth_level]:
            conflicts.append(
                W5Conflict(
                    conflict_id="w5c_"
                    + _stable_hash(
                        new_fact.fact_id, prior_fact.fact_id, new_fact.dimension.value
                    ),
                    actor_id=actor_id,
                    dimension=new_fact.dimension,
                    competing_fact_ids=(prior_fact.fact_id, new_fact.fact_id),
                    resolution_status=W5ConflictResolutionStatus.UNRESOLVED,
                    resolver_source=None,
                )
            )
    return conflicts


def extract_w5_snapshot_from_committed_event(
    *,
    previous_snapshot: W5Snapshot | None,
    committed_event: dict[str, Any],
    environment_state_after: dict[str, Any] | None,
    director_gathering_state: dict[str, Any] | None,
    free_player_action_resolution: dict[str, Any] | None,
    actor_lane_context: dict[str, Any] | None,
    npc_agency_simulation: dict[str, Any] | None,
    character_mind_records: dict[str, Any] | None,
    active_canonical_step: dict[str, Any] | None,
    story_session_id: str,
    turn_number: int,
) -> W5Snapshot:
    """Pure, deterministic W5 snapshot extractor.

    Contract:

    - No I/O, no LLM, no mutation of inputs.
    - Deterministic for identical inputs.
    - Reads substrate / committed event only for OBSERVED facts.
    - Emits ``how.*`` as first-class facts whenever How signals exist.
    - Emits ``why.*`` only with ``truth_level="inferred"`` (or
      ``director_assigned`` when set by Director gathering state).
    - DECLARED / INFERRED never silently overwrite OBSERVED / CANONICAL;
      conflicts are recorded in the new snapshot.
    """

    if not isinstance(story_session_id, str) or not story_session_id.strip():
        raise ValueError("story_session_id must be a non-empty string")

    env_state = _as_dict(environment_state_after)
    derived_from: list[str] = []
    committed_event_id = _committed_event_id(committed_event)
    if committed_event_id:
        derived_from.append(committed_event_id)
    if isinstance(active_canonical_step, dict):
        step_id = active_canonical_step.get("step_id") or active_canonical_step.get("id")
        if isinstance(step_id, str) and step_id.strip():
            derived_from.append(step_id)

    snapshot_id = _snapshot_id(
        story_session_id=story_session_id,
        turn_number=turn_number,
        derived_from=derived_from,
    )
    snapshot_seed = snapshot_id

    who = _extract_who(
        snapshot_seed=snapshot_seed,
        actor_lane_context=actor_lane_context,
        turn_number=turn_number,
    )
    where = _extract_where_observed(
        snapshot_seed=snapshot_seed,
        environment_state_after=env_state,
        committed_event_id=committed_event_id,
        turn_number=turn_number,
    )
    what_observed = _extract_what_observed_from_event(
        snapshot_seed=snapshot_seed,
        committed_event=committed_event,
        committed_event_id=committed_event_id,
        turn_number=turn_number,
    )
    what_declared = _extract_what_declared(
        snapshot_seed=snapshot_seed,
        free_player_action_resolution=free_player_action_resolution,
        turn_number=turn_number,
    )
    how = _extract_how_first_class(
        snapshot_seed=snapshot_seed,
        committed_event=committed_event,
        actor_lane_context=actor_lane_context,
        npc_agency_simulation=npc_agency_simulation,
        turn_number=turn_number,
        committed_event_id=committed_event_id,
    )
    why = _extract_why_inferred(
        snapshot_seed=snapshot_seed,
        character_mind_records=character_mind_records,
        npc_agency_simulation=npc_agency_simulation,
        director_gathering_state=director_gathering_state,
        turn_number=turn_number,
    )

    # OBSERVED what wins over DECLARED what for the same actor+key.
    what_by_actor: dict[str, list[W5Fact]] = {}
    for actor_id, facts in what_observed.items():
        what_by_actor.setdefault(actor_id, []).extend(facts)
    for actor_id, facts in what_declared.items():
        observed_keys = {f.key for f in what_by_actor.get(actor_id, [])}
        for fact in facts:
            if fact.key in observed_keys:
                continue
            what_by_actor.setdefault(actor_id, []).append(fact)

    all_actor_ids: set[str] = set()
    for bucket in (who, where, what_by_actor, how, why):
        all_actor_ids.update(bucket.keys())

    previous_situations = previous_snapshot.actors if previous_snapshot is not None else {}

    actors: dict[str, W5ActorSituation] = {}
    conflicts: list[W5Conflict] = []
    for actor_id in sorted(all_actor_ids):
        actor_who = list(who.get(actor_id, []))
        actor_where = list(where.get(actor_id, []))
        actor_what = list(what_by_actor.get(actor_id, []))
        actor_how = list(how.get(actor_id, []))
        actor_why = list(why.get(actor_id, []))
        actor_type = _resolve_actor_type(
            who_facts=actor_who,
            actor_lane_context=actor_lane_context,
            actor_id=actor_id,
        )
        # Build conflicts against the prior snapshot, then merge in carry-over
        # OBSERVED/CANONICAL facts the new snapshot did not refresh.
        new_facts = actor_where + actor_what + actor_how + actor_why + actor_who
        conflicts.extend(
            _supersede_previous(
                actor_id=actor_id,
                new_facts=new_facts,
                previous_situations=previous_situations,
            )
        )
        last_confirmed = int(turn_number) if new_facts else (
            previous_situations[actor_id].last_confirmed_turn
            if actor_id in previous_situations
            else int(turn_number)
        )
        actor_role = None
        involvement = None
        for fact in actor_who:
            if fact.key == "actor_role_in_scene" and isinstance(fact.value, str):
                actor_role = fact.value
            if fact.key == "involvement_type" and isinstance(fact.value, str):
                involvement = fact.value
        actors[actor_id] = W5ActorSituation(
            actor_id=actor_id,
            actor_type=actor_type,
            actor_role_in_scene=actor_role,
            involvement_type=involvement,
            where=tuple(actor_where),
            what=tuple(actor_what),
            how=tuple(actor_how),
            why=tuple(actor_why),
            freshness_status=W5FreshnessStatus.FRESH,
            last_confirmed_turn=last_confirmed,
        )

    created_at = "w5:turn:" + str(int(turn_number))

    return W5Snapshot(
        schema_version=W5_SNAPSHOT_SCHEMA_VERSION,
        snapshot_id=snapshot_id,
        story_session_id=story_session_id,
        turn_number=int(turn_number),
        actors=actors,
        conflicts=tuple(conflicts),
        derived_from_event_ids=tuple(derived_from),
        created_at=created_at,
    )
