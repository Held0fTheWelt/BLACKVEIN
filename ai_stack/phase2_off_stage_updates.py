"""Phase 2 Stage F — Off-Stage Update Scaffold.

Builds *candidate* relationship- and hierarchical-memory updates from an
autonomous Director tick that targets NPCs *outside* the player's current
visible scene. Stage F implements the safety-gated *preview* path only:

* A candidate is a structured proposal, never a commit.
* The scaffold's role is to surface what an off-stage update *would* look
  like and to enumerate blockers explaining why a commit is not safe yet.
* No I/O. No LLM call. Pure functions.

Hard boundaries (ADR-0058 Stage F):

* Off-stage candidates never advance the canonical path.
* Off-stage candidates never consume a mandatory beat.
* Off-stage candidates never introduce a new person (actor IDs must be in
  the supplied ``known_actor_ids`` set).
* Off-stage candidates never introduce a new room (room IDs must be in
  the supplied ``known_room_ids`` set, when referenced).
* Off-stage candidates never introduce a plot-bearing fact. Structured
  fields only; free-text bodies are rejected.
* Candidates are committed only through existing safe relationship-state
  or hierarchical-memory mechanisms; this module does *not* commit.

Governance:
* ADR-0058 — Director-Driven Pulse and Block-Stream-Bus, Stage F
* ADR-0059 — Semantic NPC Motivation Score
* ADR-0061 — Director Gathering State
* ADR-0039 — No Pi/Π runtime keys; semantic names only
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Final


# ── Closed enums ──────────────────────────────────────────────────────────────

SCHEMA_OFF_STAGE_RELATIONSHIP_UPDATE_CANDIDATE: Final[str] = (
    "off_stage_relationship_update_candidate.v1"
)
SCHEMA_OFF_STAGE_MEMORY_UPDATE_CANDIDATE: Final[str] = (
    "off_stage_memory_update_candidate.v1"
)

# Safety-gate outcomes (closed enum).
SAFETY_GATE_PASS: Final[str] = "pass"
SAFETY_GATE_BLOCKED: Final[str] = "blocked"
SAFETY_GATE_NOT_APPLICABLE: Final[str] = "not_applicable"

SAFETY_GATE_RESULTS: Final[frozenset[str]] = frozenset({
    SAFETY_GATE_PASS,
    SAFETY_GATE_BLOCKED,
    SAFETY_GATE_NOT_APPLICABLE,
})

# Blocker reasons (closed enum). Adding a new reason must be a deliberate
# Stage F update; ad-hoc string blockers are not allowed.
BLOCKER_NEW_PERSON: Final[str] = "new_person"
BLOCKER_NEW_ROOM: Final[str] = "new_room"
BLOCKER_NEW_PLOT_FACT: Final[str] = "new_plot_fact"
BLOCKER_FREE_TEXT_BODY: Final[str] = "free_text_body"
BLOCKER_CANONICAL_PATH_ADVANCE_ATTEMPTED: Final[str] = (
    "canonical_path_advance_attempted"
)
BLOCKER_MANDATORY_BEAT_CONSUME_ATTEMPTED: Final[str] = (
    "mandatory_beat_consume_attempted"
)
BLOCKER_NO_OFF_STAGE_ACTOR: Final[str] = "no_off_stage_actor"
BLOCKER_NO_NPC_CHOSEN: Final[str] = "no_npc_chosen"

BLOCKER_REASONS: Final[frozenset[str]] = frozenset({
    BLOCKER_NEW_PERSON,
    BLOCKER_NEW_ROOM,
    BLOCKER_NEW_PLOT_FACT,
    BLOCKER_FREE_TEXT_BODY,
    BLOCKER_CANONICAL_PATH_ADVANCE_ATTEMPTED,
    BLOCKER_MANDATORY_BEAT_CONSUME_ATTEMPTED,
    BLOCKER_NO_OFF_STAGE_ACTOR,
    BLOCKER_NO_NPC_CHOSEN,
})

# Candidate kinds — what the candidate *would* express.
CANDIDATE_KIND_RELATIONSHIP_TENSION_UPDATE: Final[str] = (
    "relationship_tension_update"
)
CANDIDATE_KIND_OFF_STAGE_MEMORY_NOTE: Final[str] = "off_stage_memory_note"


# ── Inputs ────────────────────────────────────────────────────────────────────


@dataclass
class OffStageUpdateInputs:
    """Pure inputs for one off-stage scaffold evaluation.

    The autonomous tick coordinator builds this from its outcome plus the
    set of known actors/rooms in the current module surface.
    """

    tick_id: str
    chosen_actor_id: str | None
    chosen_action_kind: str
    motivation_scores: dict[str, float] = field(default_factory=dict)
    visible_npc_ids: list[str] = field(default_factory=list)
    known_actor_ids: list[str] = field(default_factory=list)
    known_room_ids: list[str] = field(default_factory=list)
    gathering_paused: bool = False


# ── Helpers ──────────────────────────────────────────────────────────────────


def _is_off_stage(actor_id: str | None, visible_npc_ids: list[str]) -> bool:
    """An actor is off-stage when it is not in the visible NPC set.

    None is treated as on-stage so a "no actor" path does not produce
    an off-stage candidate.
    """
    if not actor_id:
        return False
    return str(actor_id) not in set(visible_npc_ids)


def _safe_relationship_tension_payload(
    *,
    tick_id: str,
    actor_id: str,
    motivation_scores: dict[str, float],
) -> dict[str, Any]:
    """Structured payload — no free text, only enumerable fields.

    Encodes what the autonomous tick *observed* about this NPC's motivation
    pressure into a relationship-update *proposal*. The pair the update
    relates to is left to the safe relationship-state commit mechanism
    that consumes the candidate; the scaffold's job is only to surface
    the proposal.
    """
    score = motivation_scores.get(actor_id)
    score_value: float | None
    try:
        score_value = float(score) if score is not None else None
    except (TypeError, ValueError):
        score_value = None
    return {
        "schema_version": SCHEMA_OFF_STAGE_RELATIONSHIP_UPDATE_CANDIDATE,
        "candidate_id": str(uuid.uuid4()),
        "candidate_kind": CANDIDATE_KIND_RELATIONSHIP_TENSION_UPDATE,
        "originating_tick_id": tick_id,
        "actor_id": actor_id,
        "observed_motivation_score": score_value,
        "pressure_direction": (
            "rising" if score_value is not None and score_value >= 0.5
            else "stable"
        ),
        # No free text. The realisation/commit layer (relationship-state
        # machine) is responsible for projecting into pair-state semantics.
        "structured_only": True,
    }


def _safe_off_stage_memory_payload(
    *,
    tick_id: str,
    actor_id: str,
    motivation_scores: dict[str, float],
) -> dict[str, Any]:
    """Structured memory candidate. No raw prose, no plot facts."""
    score = motivation_scores.get(actor_id)
    try:
        score_value = float(score) if score is not None else None
    except (TypeError, ValueError):
        score_value = None
    return {
        "schema_version": SCHEMA_OFF_STAGE_MEMORY_UPDATE_CANDIDATE,
        "candidate_id": str(uuid.uuid4()),
        "candidate_kind": CANDIDATE_KIND_OFF_STAGE_MEMORY_NOTE,
        "originating_tick_id": tick_id,
        "actor_id": actor_id,
        "memory_tier_target": "actor",
        "evidence_kind": "motivation_pressure_observation",
        "observed_motivation_score": score_value,
        "structured_only": True,
    }


def _validate_actor_id_in_known_set(
    actor_id: str | None,
    known_actor_ids: list[str],
) -> bool:
    if not actor_id:
        return False
    return str(actor_id) in set(known_actor_ids) if known_actor_ids else False


def _payload_has_free_text_body(payload: dict[str, Any] | None) -> bool:
    """Reject candidates that include a free-text body field.

    Stage F candidates must be structured. Any field whose key ends in
    ``_text`` / ``body`` / ``narration`` with non-empty string value, or
    a generic ``text`` field, is treated as free-text and blocked.
    """
    if not isinstance(payload, dict):
        return False
    forbidden_keys = {"text", "body", "narration", "description"}
    for key, value in payload.items():
        key_l = str(key).lower()
        if key_l in forbidden_keys and isinstance(value, str) and value.strip():
            return True
        if key_l.endswith("_text") and isinstance(value, str) and value.strip():
            return True
    return False


def _payload_introduces_new_plot_fact(payload: dict[str, Any] | None) -> bool:
    """Reject candidates containing plot-bearing facts.

    A plot-bearing fact is anything labelled ``plot_fact``, ``revelation``,
    ``secret``, ``hidden_fact``, ``twist``, ``reveal`` — these touch the
    canonical fiction and must not flow through an off-stage autonomous
    update.
    """
    if not isinstance(payload, dict):
        return False
    forbidden_keys = {
        "plot_fact",
        "plot_bearing_fact",
        "revelation",
        "secret",
        "hidden_fact",
        "twist",
        "reveal",
        "new_canonical_fact",
    }
    for key in payload:
        if str(key).lower() in forbidden_keys:
            return True
    return False


# ── Public API ────────────────────────────────────────────────────────────────


def build_off_stage_update_candidate(
    inputs: OffStageUpdateInputs,
) -> dict[str, Any]:
    """Build a Stage F off-stage update candidate result.

    The function always returns a structured result with a ``safety_gate``
    field whose value is one of ``SAFETY_GATE_RESULTS``. Blockers are
    accumulated as a list of closed-enum values from ``BLOCKER_REASONS``.

    Result shape:

        {
            "off_stage_update_candidate": bool,
            "relationship_update_candidate": dict | None,
            "memory_update_candidate": dict | None,
            "off_stage_safety_gate_result": str,   # closed enum
            "blockers": list[str],                  # closed-enum strings
            "canonical_path_advanced": False,       # invariant
            "mandatory_beat_consumed": False,       # invariant
        }

    Pure function. No I/O. No mutation of inputs.
    """
    blockers: list[str] = []
    relationship_candidate: dict[str, Any] | None = None
    memory_candidate: dict[str, Any] | None = None
    applicable = False

    if not inputs.chosen_actor_id:
        blockers.append(BLOCKER_NO_NPC_CHOSEN)
    elif not _is_off_stage(inputs.chosen_actor_id, list(inputs.visible_npc_ids)):
        # The chosen actor is visible — Stage F off-stage path does not apply.
        blockers.append(BLOCKER_NO_OFF_STAGE_ACTOR)
    elif not _validate_actor_id_in_known_set(
        inputs.chosen_actor_id, list(inputs.known_actor_ids)
    ):
        # Off-stage NPC must already exist in the module surface — no
        # new people may be introduced from an autonomous tick.
        blockers.append(BLOCKER_NEW_PERSON)
    else:
        applicable = True
        relationship_candidate = _safe_relationship_tension_payload(
            tick_id=inputs.tick_id,
            actor_id=inputs.chosen_actor_id,
            motivation_scores=dict(inputs.motivation_scores or {}),
        )
        memory_candidate = _safe_off_stage_memory_payload(
            tick_id=inputs.tick_id,
            actor_id=inputs.chosen_actor_id,
            motivation_scores=dict(inputs.motivation_scores or {}),
        )

        # Sanity-check our own payloads — defensive, even though the
        # private builders are structured-only.
        for payload in (relationship_candidate, memory_candidate):
            if _payload_has_free_text_body(payload):
                blockers.append(BLOCKER_FREE_TEXT_BODY)
            if _payload_introduces_new_plot_fact(payload):
                blockers.append(BLOCKER_NEW_PLOT_FACT)

    if blockers and relationship_candidate is None and memory_candidate is None:
        gate = (
            SAFETY_GATE_NOT_APPLICABLE
            if blockers == [BLOCKER_NO_NPC_CHOSEN]
            or blockers == [BLOCKER_NO_OFF_STAGE_ACTOR]
            else SAFETY_GATE_BLOCKED
        )
        applicable = False
    elif blockers:
        gate = SAFETY_GATE_BLOCKED
        # Blockers on a built candidate disqualify it.
        relationship_candidate = None
        memory_candidate = None
        applicable = False
    else:
        gate = SAFETY_GATE_PASS

    return {
        "off_stage_update_candidate": bool(applicable),
        "relationship_update_candidate": relationship_candidate,
        "memory_update_candidate": memory_candidate,
        "off_stage_safety_gate_result": gate,
        "blockers": sorted(set(blockers)),
        # Hard invariants — never violated by this module.
        "canonical_path_advanced": False,
        "mandatory_beat_consumed": False,
    }


def validate_external_candidate(
    candidate: dict[str, Any] | None,
    *,
    known_actor_ids: list[str],
    known_room_ids: list[str],
) -> list[str]:
    """Validate an externally-built candidate against Stage F safety rules.

    Returns a list of closed-enum blocker reasons. An empty list means
    the candidate would pass the Stage F safety gate.

    Used by Stage F tests and by integrators that want to vet a candidate
    before passing it to a relationship-state or memory commit.
    """
    if not isinstance(candidate, dict):
        return [BLOCKER_NEW_PERSON]

    blockers: list[str] = []

    actor_id = candidate.get("actor_id")
    if actor_id and not _validate_actor_id_in_known_set(actor_id, known_actor_ids):
        blockers.append(BLOCKER_NEW_PERSON)

    room_id = candidate.get("room_id") or candidate.get("location_id")
    if room_id and known_room_ids and str(room_id) not in set(known_room_ids):
        blockers.append(BLOCKER_NEW_ROOM)

    if _payload_has_free_text_body(candidate):
        blockers.append(BLOCKER_FREE_TEXT_BODY)

    if _payload_introduces_new_plot_fact(candidate):
        blockers.append(BLOCKER_NEW_PLOT_FACT)

    if candidate.get("canonical_path_advance") or candidate.get("advance_canonical_path"):
        blockers.append(BLOCKER_CANONICAL_PATH_ADVANCE_ATTEMPTED)

    if candidate.get("mandatory_beat_consume") or candidate.get("consume_mandatory_beat"):
        blockers.append(BLOCKER_MANDATORY_BEAT_CONSUME_ATTEMPTED)

    return sorted(set(blockers))


__all__ = [
    "SCHEMA_OFF_STAGE_RELATIONSHIP_UPDATE_CANDIDATE",
    "SCHEMA_OFF_STAGE_MEMORY_UPDATE_CANDIDATE",
    "SAFETY_GATE_PASS",
    "SAFETY_GATE_BLOCKED",
    "SAFETY_GATE_NOT_APPLICABLE",
    "SAFETY_GATE_RESULTS",
    "BLOCKER_NEW_PERSON",
    "BLOCKER_NEW_ROOM",
    "BLOCKER_NEW_PLOT_FACT",
    "BLOCKER_FREE_TEXT_BODY",
    "BLOCKER_CANONICAL_PATH_ADVANCE_ATTEMPTED",
    "BLOCKER_MANDATORY_BEAT_CONSUME_ATTEMPTED",
    "BLOCKER_NO_OFF_STAGE_ACTOR",
    "BLOCKER_NO_NPC_CHOSEN",
    "BLOCKER_REASONS",
    "CANDIDATE_KIND_RELATIONSHIP_TENSION_UPDATE",
    "CANDIDATE_KIND_OFF_STAGE_MEMORY_NOTE",
    "OffStageUpdateInputs",
    "build_off_stage_update_candidate",
    "validate_external_candidate",
]
