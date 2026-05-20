"""Closed-enum contract surface for ``director_gathering_state.v1``.

This module is the PR-C delivery for the NPC Interactivity roadmap. It carries
the per-turn Director-Pause state that gates mandatory-beat consumption when
required actors are not co-present in the gathering.

Authoritative governance:

* :doc:`docs/ADR/adr-0061-director-pause-mode-for-gathering-interruption`
  (defines the contract shape, composition rule, and beat-consumption gate).
* :doc:`docs/ADR/adr-0057-canon-safe-player-freedom-and-affordance-inference`
  (Phase-1 amendment reserves the ``director_gathering_state.v1`` contract).
* :doc:`docs/ADR/adr-0062-director-realization-thin-path` (composition path
  that the Director state rides on).
* :doc:`docs/implementation_logs/pr_c_director_pause_mode_piv` (PR-C PIV
  artifact).

Vocabulary discipline (ADR-0039 + Phase-1 amendment):

* Closed enums for ``reason``. Semantic capability names only.
* No Pi / Pi-numbered runtime keys.
* No verb / room / actor / locale literal whitelists.
* The ``paused`` decision derives from actor topology and resolver evidence;
  never from verb matching, step-mode switching, or room names.
* ``compute_gathering_state`` is a pure function — no I/O, no mutation,
  no LLM call, no content hardcoding.
"""

from __future__ import annotations

from typing import Any, Final


SCHEMA_VERSION: Final[str] = "director_gathering_state.v1"


PAUSE_REASON_ACTOR_NOT_AT_SCENE: Final[str] = "required_actor_not_at_scene_location"
PAUSE_REASON_PARTICIPATION_BROKEN: Final[str] = "participation_relevance_broken"
PAUSE_REASON_VISIBILITY_LOST: Final[str] = "visibility_audibility_lost"

PAUSE_REASONS: Final[frozenset[str]] = frozenset(
    {
        PAUSE_REASON_ACTOR_NOT_AT_SCENE,
        PAUSE_REASON_PARTICIPATION_BROKEN,
        PAUSE_REASON_VISIBILITY_LOST,
    }
)

PAUSE_SOURCE_RESOLVER_EVIDENCE: Final[str] = "free_player_action_resolution.v1"
PAUSE_SOURCE_TOPOLOGY: Final[str] = "actor_topology_derived"

DIAGNOSTIC_BLOCKER_MISSING_ACTOR_LOCATIONS: Final[str] = "missing_actor_locations"
DIAGNOSTIC_BLOCKER_MISSING_NAMED_CHARACTERS: Final[str] = "missing_named_characters"
DIAGNOSTIC_BLOCKER_MISSING_STEP_SCENE_ID: Final[str] = "missing_step_scene_id"
DIAGNOSTIC_BLOCKER_MISSING_PARTICIPATION_EVIDENCE: Final[str] = "missing_participation_evidence"

PAUSE_SOURCES: Final[frozenset[str]] = frozenset(
    {PAUSE_SOURCE_RESOLVER_EVIDENCE, PAUSE_SOURCE_TOPOLOGY}
)


def _coerce_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def compute_gathering_state(
    *,
    actor_locations: dict[str, str | None] | None,
    current_step_named_characters: list[str] | None,
    current_step_scene_id: str | None,
    participation_relevance: str | None = None,
    visibility_audibility: str | None = None,
    subject_actor_id: str | None = None,
    participation_evidence_required: bool = False,
    current_turn_number: int | None = None,
    previous_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute the ``director_gathering_state.v1`` snapshot.

    Pure function. No I/O, no mutation, no LLM call, no content hardcoding.

    The pause decision is a semantic composition over actor topology and
    resolver signals:

    * ``paused == True`` iff at least one actor in
      ``current_step_named_characters`` is either not at
      ``current_step_scene_id``, has lost ``participation_relevance``, or
      has lost ``visibility_audibility`` relative to the gathering.
    * ``missing_actor_ids`` is the subset failing any of those conditions.
    * When ``paused == False``, ``missing_actor_ids`` is empty.

    Args:
        actor_locations: Mapping from actor_id to their current location_id.
            ``None`` means location unknown (treated as not present).
        current_step_named_characters: List of actor_ids required for the
            current canonical step.
        current_step_scene_id: The location_id where the gathering is held.
        participation_relevance: Resolver evidence string. Values like
            ``"broken"`` or ``"not_participating"`` contribute to pause.
        visibility_audibility: Resolver evidence string. Values like
            ``"not_visible"`` or ``"not_audible"`` contribute to pause.
        current_turn_number: Current turn number for ``since_turn`` tracking.
        previous_state: The prior ``director_gathering_state.v1`` dict, used
            to preserve ``since_turn`` on ongoing pauses.

    Returns:
        A dict conforming to ``director_gathering_state.v1``.
    """
    named_characters = (
        [str(c).strip() for c in current_step_named_characters if str(c).strip()]
        if current_step_named_characters
        else []
    )
    scene_id = _coerce_string(current_step_scene_id)
    locations = actor_locations if isinstance(actor_locations, dict) else {}
    prev = previous_state if isinstance(previous_state, dict) else {}
    subject = _coerce_string(subject_actor_id)

    if not named_characters:
        return {
            "schema_version": SCHEMA_VERSION,
            "paused": False,
            "missing_actor_ids": [],
            "presence_required_for_step": named_characters,
            "diagnostic_blocker": True,
            "reason": DIAGNOSTIC_BLOCKER_MISSING_NAMED_CHARACTERS,
        }
    if not scene_id:
        return {
            "schema_version": SCHEMA_VERSION,
            "paused": False,
            "missing_actor_ids": [],
            "presence_required_for_step": named_characters,
            "diagnostic_blocker": True,
            "reason": DIAGNOSTIC_BLOCKER_MISSING_STEP_SCENE_ID,
        }
    if actor_locations is None or not isinstance(actor_locations, dict) or not locations:
        return {
            "schema_version": SCHEMA_VERSION,
            "paused": False,
            "missing_actor_ids": [],
            "presence_required_for_step": named_characters,
            "diagnostic_blocker": True,
            "reason": DIAGNOSTIC_BLOCKER_MISSING_ACTOR_LOCATIONS,
        }

    missing_actor_ids: list[str] = []
    reasons: list[str] = []

    for actor_id in named_characters:
        actor_loc = _coerce_string(locations.get(actor_id))
        if actor_loc is None or actor_loc != scene_id:
            if actor_id not in missing_actor_ids:
                missing_actor_ids.append(actor_id)
            if PAUSE_REASON_ACTOR_NOT_AT_SCENE not in reasons:
                reasons.append(PAUSE_REASON_ACTOR_NOT_AT_SCENE)

    participation_text = _coerce_string(participation_relevance)
    visibility_text = _coerce_string(visibility_audibility)
    if participation_evidence_required and (participation_text is None or visibility_text is None):
        return {
            "schema_version": SCHEMA_VERSION,
            "paused": False,
            "missing_actor_ids": [],
            "presence_required_for_step": named_characters,
            "diagnostic_blocker": True,
            "reason": DIAGNOSTIC_BLOCKER_MISSING_PARTICIPATION_EVIDENCE,
            "evidence_status": {
                "participation_relevance_present": participation_text is not None,
                "visibility_audibility_present": visibility_text is not None,
            },
        }
    if participation_text and participation_text.lower() in (
        "broken",
        "not_participating",
        "disengaged",
        "absent",
    ):
        if subject and subject not in missing_actor_ids:
            if PAUSE_REASON_PARTICIPATION_BROKEN not in reasons:
                reasons.append(PAUSE_REASON_PARTICIPATION_BROKEN)
            missing_actor_ids.append(subject)
        elif not subject:
            # No subject specified: record reason without modifying missing list.
            if PAUSE_REASON_PARTICIPATION_BROKEN not in reasons:
                reasons.append(PAUSE_REASON_PARTICIPATION_BROKEN)

    if visibility_text and visibility_text.lower() in (
        "not_visible",
        "not_audible",
        "hidden",
        "out_of_sight",
        "inaudible",
    ):
        if subject and subject not in missing_actor_ids:
            if PAUSE_REASON_VISIBILITY_LOST not in reasons:
                reasons.append(PAUSE_REASON_VISIBILITY_LOST)
            missing_actor_ids.append(subject)
        elif not subject:
            if PAUSE_REASON_VISIBILITY_LOST not in reasons:
                reasons.append(PAUSE_REASON_VISIBILITY_LOST)

    missing_actor_ids.sort()
    paused = len(missing_actor_ids) > 0 or len(reasons) > 0

    if not paused:
        return {
            "schema_version": SCHEMA_VERSION,
            "paused": False,
            "missing_actor_ids": [],
            "presence_required_for_step": named_characters,
        }

    prev_paused = bool(prev.get("paused"))
    prev_since_turn = prev.get("since_turn") if prev_paused else None
    since_turn: int | None
    if prev_since_turn is not None:
        try:
            since_turn = int(prev_since_turn)
        except (TypeError, ValueError):
            since_turn = current_turn_number
    else:
        since_turn = current_turn_number

    prev_step_id = _coerce_string(prev.get("step_id")) if prev_paused else None
    step_id = prev_step_id or scene_id

    source = (
        PAUSE_SOURCE_RESOLVER_EVIDENCE
        if participation_text or visibility_text
        else PAUSE_SOURCE_TOPOLOGY
    )

    reason = reasons[0] if reasons else PAUSE_REASON_ACTOR_NOT_AT_SCENE

    return {
        "schema_version": SCHEMA_VERSION,
        "paused": True,
        "step_id": step_id,
        "missing_actor_ids": missing_actor_ids,
        "since_turn": since_turn,
        "presence_required_for_step": named_characters,
        "reason": reason,
        "source": source,
    }


def should_suppress_mandatory_beat_consumption(
    director_gathering_state: dict[str, Any] | None,
) -> bool:
    """Return True when mandatory-beat consumption must be suppressed.

    This is the beat-consumption gate described in ADR-0061 §5. When the
    Director-Pause is active, mandatory beats must not be consumed, but the
    player remains free and narrator local consequences are not blocked.
    """
    if not isinstance(director_gathering_state, dict):
        return False
    return bool(director_gathering_state.get("paused"))


def gathering_pause_is_transition(
    *,
    previous_state: dict[str, Any] | None,
    current_state: dict[str, Any] | None,
) -> str | None:
    """Detect a pause transition and return its direction.

    Returns:
        ``"entered"`` for ``paused: false → true``.
        ``"cleared"`` for ``paused: true → false``.
        ``None`` when no transition occurred.
    """
    prev = previous_state if isinstance(previous_state, dict) else {}
    curr = current_state if isinstance(current_state, dict) else {}
    was_paused = bool(prev.get("paused"))
    is_paused = bool(curr.get("paused"))
    if not was_paused and is_paused:
        return "entered"
    if was_paused and not is_paused:
        return "cleared"
    return None


__all__ = [
    "SCHEMA_VERSION",
    "PAUSE_REASON_ACTOR_NOT_AT_SCENE",
    "PAUSE_REASON_PARTICIPATION_BROKEN",
    "PAUSE_REASON_VISIBILITY_LOST",
    "PAUSE_REASONS",
    "PAUSE_SOURCE_RESOLVER_EVIDENCE",
    "PAUSE_SOURCE_TOPOLOGY",
    "PAUSE_SOURCES",
    "DIAGNOSTIC_BLOCKER_MISSING_ACTOR_LOCATIONS",
    "DIAGNOSTIC_BLOCKER_MISSING_NAMED_CHARACTERS",
    "DIAGNOSTIC_BLOCKER_MISSING_STEP_SCENE_ID",
    "DIAGNOSTIC_BLOCKER_MISSING_PARTICIPATION_EVIDENCE",
    "compute_gathering_state",
    "should_suppress_mandatory_beat_consumption",
    "gathering_pause_is_transition",
]
