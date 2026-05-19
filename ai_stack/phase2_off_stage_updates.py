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

from ai_stack.hierarchical_memory_contracts import (
    build_off_stage_hierarchical_memory_write,
    merge_hierarchical_memory_snapshot,
)
from ai_stack.relationship_state_contracts import (
    RELATIONSHIP_STATE_SCHEMA_VERSION,
    RelationshipDynamicsTarget,
    RelationshipStateEvidenceRef,
    RelationshipStateRecord,
    RelationshipTransitionEvent,
)


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

RECOGNIZED_CANDIDATE_KINDS: Final[frozenset[str]] = frozenset({
    CANDIDATE_KIND_RELATIONSHIP_TENSION_UPDATE,
    CANDIDATE_KIND_OFF_STAGE_MEMORY_NOTE,
})

# Stage G policy and diagnostics.
OFF_STAGE_UPDATES_POLICY_SCHEMA_VERSION: Final[str] = "off_stage_updates_policy.v1"
OFF_STAGE_COMMIT_RESULT_SCHEMA_VERSION: Final[str] = "off_stage_commit_result.v1"

COMMIT_TARGET_RELATIONSHIP_STATE: Final[str] = "relationship_state"
COMMIT_TARGET_HIERARCHICAL_MEMORY: Final[str] = "hierarchical_memory"

DEFAULT_ALLOWED_CANDIDATE_KINDS: Final[tuple[str, ...]] = (
    CANDIDATE_KIND_RELATIONSHIP_TENSION_UPDATE,
    CANDIDATE_KIND_OFF_STAGE_MEMORY_NOTE,
)


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


@dataclass
class OffStageCommitInputs:
    """Opt-in Stage G commit context for one off-stage candidate result.

    All fields are plain data. The adapter returns updated relationship or
    memory artifacts to the caller; persistence remains owned by the existing
    runtime/session layer.
    """

    candidate_result: dict[str, Any] | None
    policy: dict[str, Any] | None = None
    known_actor_ids: list[str] = field(default_factory=list)
    known_room_ids: list[str] = field(default_factory=list)
    relationship_state_record: dict[str, Any] | None = None
    hierarchical_memory_snapshot: dict[str, Any] | None = None
    hierarchical_memory_policy: dict[str, Any] | None = None
    module_runtime_policy: dict[str, Any] | None = None
    module_id: str | None = None
    runtime_profile_id: str | None = None
    turn_number: int | None = None


# ── Helpers ──────────────────────────────────────────────────────────────────


def _is_off_stage(actor_id: str | None, visible_npc_ids: list[str]) -> bool:
    """An actor is off-stage when it is not in the visible NPC set.

    None is treated as on-stage so a "no actor" path does not produce
    an off-stage candidate.
    """
    if not actor_id:
        return False
    return str(actor_id) not in set(visible_npc_ids)


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _bounded_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def normalize_off_stage_updates_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize Stage G off-stage commit policy.

    The fail-closed default is ``auto_commit_enabled=False``. The allowed-kind
    default describes the only candidate kinds the adapter knows how to route;
    it does not enable commits by itself.
    """
    raw = policy if isinstance(policy, dict) else {}
    if isinstance(raw.get("allowed_candidate_kinds"), list):
        allowed = [
            _clean(kind)
            for kind in raw.get("allowed_candidate_kinds") or []
            if _clean(kind) in RECOGNIZED_CANDIDATE_KINDS
        ]
    else:
        allowed = list(DEFAULT_ALLOWED_CANDIDATE_KINDS)
    return {
        "schema_version": _clean(raw.get("schema_version"))
        or OFF_STAGE_UPDATES_POLICY_SCHEMA_VERSION,
        "auto_commit_enabled": bool(raw.get("auto_commit_enabled", False)),
        "allowed_candidate_kinds": allowed,
        "require_safety_gate_pass": bool(raw.get("require_safety_gate_pass", True)),
        "max_commits_per_tick": _bounded_int(
            raw.get("max_commits_per_tick"),
            1,
            minimum=0,
            maximum=8,
        ),
    }


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
    if room_id and str(room_id) not in set(known_room_ids):
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


def _diagnostic_result(
    *,
    attempted: bool,
    committed: bool = False,
    committed_targets: list[str] | None = None,
    rejected_targets: list[dict[str, Any]] | None = None,
    reason: str,
    safety_gate_result: str | None,
    canonical_path_advanced: bool = False,
    mandatory_beat_consumed: bool = False,
    target_results: list[dict[str, Any]] | None = None,
    audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": OFF_STAGE_COMMIT_RESULT_SCHEMA_VERSION,
        "attempted": bool(attempted),
        "committed": bool(committed),
        "committed_targets": list(committed_targets or []),
        "rejected_targets": list(rejected_targets or []),
        "reason": reason,
        "safety_gate_result": safety_gate_result,
        "canonical_path_advanced": bool(canonical_path_advanced),
        "mandatory_beat_consumed": bool(mandatory_beat_consumed),
        "proof_level": "local_only",
        "target_results": list(target_results or []),
        "audit": dict(audit or {}),
    }


def build_default_off_stage_commit_result(
    candidate_result: dict[str, Any] | None = None,
    *,
    reason: str = "no_off_stage_candidate",
) -> dict[str, Any]:
    """Return a diagnostic no-commit result for callers that only preview."""
    cand = candidate_result if isinstance(candidate_result, dict) else {}
    return _diagnostic_result(
        attempted=False,
        committed=False,
        reason=reason,
        safety_gate_result=cand.get("off_stage_safety_gate_result"),
        canonical_path_advanced=bool(cand.get("canonical_path_advanced", False)),
        mandatory_beat_consumed=bool(cand.get("mandatory_beat_consumed", False)),
    )


def _candidate_targets(candidate_result: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    targets: list[tuple[str, dict[str, Any]]] = []
    relationship_candidate = candidate_result.get("relationship_update_candidate")
    if isinstance(relationship_candidate, dict):
        targets.append((COMMIT_TARGET_RELATIONSHIP_STATE, relationship_candidate))
    memory_candidate = candidate_result.get("memory_update_candidate")
    if isinstance(memory_candidate, dict):
        targets.append((COMMIT_TARGET_HIERARCHICAL_MEMORY, memory_candidate))
    return targets


def _reject_target(
    target: str,
    reason: str,
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cand = candidate if isinstance(candidate, dict) else {}
    return {
        "target": target,
        "candidate_kind": cand.get("candidate_kind"),
        "candidate_id": cand.get("candidate_id"),
        "reason": reason,
    }


def _relationship_pair_for_actor(
    record: RelationshipStateRecord,
    actor_id: str,
) -> tuple[int, Any] | None:
    for idx, pair in enumerate(record.pair_states):
        if actor_id in {str(value) for value in pair.character_ids}:
            return idx, pair
    return None


def _updated_axis_rows(
    *,
    record: RelationshipStateRecord,
    updated_pair_rows: list[dict[str, Any]],
    affected_axis_ids: set[str],
) -> list[dict[str, Any]]:
    axis_rows = [row.model_dump(mode="json") for row in record.axis_states]
    if not affected_axis_ids:
        return axis_rows
    pairs_by_axis: dict[str, list[dict[str, Any]]] = {}
    for pair in updated_pair_rows:
        for axis_id in pair.get("axis_ids") or []:
            if str(axis_id) in affected_axis_ids:
                pairs_by_axis.setdefault(str(axis_id), []).append(pair)
    for axis in axis_rows:
        axis_id = str(axis.get("axis_id") or "")
        if axis_id not in affected_axis_ids:
            continue
        pair_rows = pairs_by_axis.get(axis_id) or []
        if pair_rows:
            axis["tension_score"] = round(
                sum(float(pair.get("tension_score") or 0.0) for pair in pair_rows)
                / len(pair_rows),
                3,
            )
        axis["active"] = bool(axis.get("active", False))
        codes = [
            _clean(code)
            for code in (axis.get("last_transition_codes") or [])
            if _clean(code)
        ]
        if "npc_initiative_pressure" not in codes:
            codes.append("npc_initiative_pressure")
        axis["last_transition_codes"] = codes[-8:]
        axis["trend"] = "rising"
    return axis_rows


def _commit_relationship_candidate(
    *,
    candidate: dict[str, Any],
    prior_record: dict[str, Any] | None,
    turn_number: int | None,
    module_runtime_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    from ai_stack.relationship_state_engine import (
        relationship_state_fingerprint,
        validate_relationship_state_realization,
    )

    if not isinstance(prior_record, dict) or not prior_record:
        return {
            "target": COMMIT_TARGET_RELATIONSHIP_STATE,
            "committed": False,
            "reason": "relationship_state_missing",
        }
    actor_id = _clean(candidate.get("actor_id"))
    if not actor_id:
        return {
            "target": COMMIT_TARGET_RELATIONSHIP_STATE,
            "committed": False,
            "reason": "candidate_actor_missing",
        }
    try:
        record = RelationshipStateRecord.model_validate(prior_record)
    except Exception as exc:  # noqa: BLE001
        return {
            "target": COMMIT_TARGET_RELATIONSHIP_STATE,
            "committed": False,
            "reason": "relationship_state_contract_rejected",
            "detail": str(exc),
        }
    match = _relationship_pair_for_actor(record, actor_id)
    if match is None:
        return {
            "target": COMMIT_TARGET_RELATIONSHIP_STATE,
            "committed": False,
            "reason": "relationship_target_missing",
        }
    pair_index, pair = match
    try:
        turn = max(0, int(turn_number or record.turn_number or 0))
    except (TypeError, ValueError):
        turn = record.turn_number
    prior_fingerprint = relationship_state_fingerprint(record)
    score = candidate.get("observed_motivation_score")
    try:
        score_value = float(score) if score is not None else None
    except (TypeError, ValueError):
        score_value = None
    tension_delta = 0.03 if score_value is not None and score_value >= 0.5 else 0.01
    pair_rows = [row.model_dump(mode="json") for row in record.pair_states]
    pair_row = dict(pair_rows[pair_index])
    pair_row["tension_score"] = min(
        1.0,
        round(float(pair_row.get("tension_score") or 0.0) + tension_delta, 3),
    )
    pair_row["trend"] = "rising"
    pair_row["last_updated_turn"] = turn
    codes = [
        _clean(code)
        for code in (pair_row.get("last_transition_codes") or [])
        if _clean(code)
    ]
    if "npc_initiative_pressure" not in codes:
        codes.append("npc_initiative_pressure")
    pair_row["last_transition_codes"] = codes[-8:]
    pair_rows[pair_index] = pair_row

    evidence = RelationshipStateEvidenceRef(
        source="off_stage_update_candidate",
        field="observed_motivation_score",
        value=score_value,
    )
    transition = RelationshipTransitionEvent(
        transition_id=f"off_stage:{candidate.get('candidate_id') or uuid.uuid4()}",
        turn_number=turn,
        relationship_id=pair.relationship_id,
        axis_ids=list(pair.axis_ids),
        transition_code="npc_initiative_pressure",
        tension_delta=tension_delta,
        source_evidence=[evidence],
    )
    record_data = record.model_dump(mode="json")
    record_data["turn_number"] = turn
    record_data["prior_record_fingerprint"] = prior_fingerprint
    record_data["pair_states"] = pair_rows
    record_data["axis_states"] = _updated_axis_rows(
        record=record,
        updated_pair_rows=pair_rows,
        affected_axis_ids={str(axis_id) for axis_id in pair.axis_ids},
    )
    events = list(record_data.get("transition_events") or [])
    events.append(transition.model_dump(mode="json"))
    record_data["transition_events"] = events[-64:]
    source_evidence = list(record_data.get("source_evidence") or [])
    source_evidence.append(evidence.to_runtime_dict())
    record_data["source_evidence"] = source_evidence[-24:]
    rationale = [
        _clean(code)
        for code in (record_data.get("rationale_codes") or [])
        if _clean(code)
    ]
    if "off_stage_relationship_candidate_committed" not in rationale:
        rationale.append("off_stage_relationship_candidate_committed")
    record_data["rationale_codes"] = rationale[-24:]

    try:
        updated_record = RelationshipStateRecord.model_validate(record_data)
    except Exception as exc:  # noqa: BLE001
        return {
            "target": COMMIT_TARGET_RELATIONSHIP_STATE,
            "committed": False,
            "reason": "relationship_state_contract_rejected",
            "detail": str(exc),
        }
    target = RelationshipDynamicsTarget(
        schema_version=RELATIONSHIP_STATE_SCHEMA_VERSION,
        target_axis_ids=list(pair.axis_ids)[:4],
        target_relationship_ids=[pair.relationship_id],
        required_transition_codes=["npc_initiative_pressure"],
        pressure_band=pair_row.get("stability_band") or "stable",
        requires_visible_relationship_beat=False,
        source_evidence=[evidence],
        rationale_codes=["off_stage_relationship_target"],
    ).to_runtime_dict()
    validation = validate_relationship_state_realization(
        relationship_state_record=updated_record.to_runtime_dict(),
        relationship_dynamics_target=target,
        structured_output={
            "relationship_dynamics_events": [
                {
                    "transition_code": "npc_initiative_pressure",
                    "actor_id": actor_id,
                }
            ]
        },
        actor_lane_context=None,
        module_runtime_policy=module_runtime_policy,
    )
    if validation.get("status") != "approved":
        return {
            "target": COMMIT_TARGET_RELATIONSHIP_STATE,
            "committed": False,
            "reason": "relationship_state_validation_rejected",
            "validation": validation,
        }
    return {
        "target": COMMIT_TARGET_RELATIONSHIP_STATE,
        "committed": True,
        "reason": "committed",
        "relationship_state_record": updated_record.to_runtime_dict(),
        "relationship_state_validation": validation,
        "audit": {
            "prior_fingerprint": prior_fingerprint,
            "new_fingerprint": relationship_state_fingerprint(updated_record),
            "transition_id": transition.transition_id,
            "candidate_id": candidate.get("candidate_id"),
        },
    }


def _commit_memory_candidate(
    *,
    candidate: dict[str, Any],
    prior_snapshot: dict[str, Any] | None,
    memory_policy: dict[str, Any] | None,
    module_id: str | None,
    runtime_profile_id: str | None,
    turn_number: int | None,
) -> dict[str, Any]:
    write_result = build_off_stage_hierarchical_memory_write(
        memory_policy=memory_policy,
        candidate=candidate,
        module_id=module_id,
        runtime_profile_id=runtime_profile_id,
        turn_number=turn_number,
    )
    if not write_result.get("write_allowed") or write_result.get("status") != "passed":
        return {
            "target": COMMIT_TARGET_HIERARCHICAL_MEMORY,
            "committed": False,
            "reason": write_result.get("failure_reason") or "hierarchical_memory_rejected",
            "write_result": write_result,
        }
    snapshot = merge_hierarchical_memory_snapshot(
        prior_snapshot=prior_snapshot,
        write_result=write_result,
        memory_policy=memory_policy,
        module_id=module_id,
        runtime_profile_id=runtime_profile_id,
    )
    return {
        "target": COMMIT_TARGET_HIERARCHICAL_MEMORY,
        "committed": True,
        "reason": "committed",
        "write_result": write_result,
        "hierarchical_memory_snapshot": snapshot,
        "audit": {
            "written_item_ids": [
                item.get("item_id")
                for item in (write_result.get("written_items") or [])
                if isinstance(item, dict)
            ],
            "candidate_id": candidate.get("candidate_id"),
        },
    }


def commit_off_stage_update_candidates(inputs: OffStageCommitInputs) -> dict[str, Any]:
    """Safely commit Stage F candidates when policy and target contracts pass.

    Defaults to diagnostic preview-only behavior. The adapter never advances
    the canonical path, never consumes mandatory beats, and never persists
    state by itself; committed artifacts are returned for the caller's existing
    relationship/memory owner to store.
    """
    candidate_result = (
        inputs.candidate_result if isinstance(inputs.candidate_result, dict) else {}
    )
    policy = normalize_off_stage_updates_policy(inputs.policy)
    safety_gate = candidate_result.get("off_stage_safety_gate_result")
    targets = _candidate_targets(candidate_result)
    attempted = bool(targets)
    base_audit = {
        "policy": policy,
        "candidate_ids": [
            target_candidate.get("candidate_id")
            for _, target_candidate in targets
            if target_candidate.get("candidate_id")
        ],
    }

    if not targets:
        return _diagnostic_result(
            attempted=False,
            committed=False,
            reason="no_off_stage_candidate",
            safety_gate_result=safety_gate,
            canonical_path_advanced=bool(candidate_result.get("canonical_path_advanced", False)),
            mandatory_beat_consumed=bool(candidate_result.get("mandatory_beat_consumed", False)),
            audit=base_audit,
        )
    if not policy.get("auto_commit_enabled"):
        return _diagnostic_result(
            attempted=attempted,
            committed=False,
            rejected_targets=[
                _reject_target(target, "auto_commit_disabled", cand)
                for target, cand in targets
            ],
            reason="auto_commit_disabled",
            safety_gate_result=safety_gate,
            canonical_path_advanced=bool(candidate_result.get("canonical_path_advanced", False)),
            mandatory_beat_consumed=bool(candidate_result.get("mandatory_beat_consumed", False)),
            audit=base_audit,
        )
    if policy.get("require_safety_gate_pass") and safety_gate != SAFETY_GATE_PASS:
        return _diagnostic_result(
            attempted=attempted,
            committed=False,
            rejected_targets=[
                _reject_target(target, "safety_gate_not_pass", cand)
                for target, cand in targets
            ],
            reason="safety_gate_not_pass",
            safety_gate_result=safety_gate,
            canonical_path_advanced=bool(candidate_result.get("canonical_path_advanced", False)),
            mandatory_beat_consumed=bool(candidate_result.get("mandatory_beat_consumed", False)),
            audit=base_audit,
        )
    blockers = [
        _clean(blocker)
        for blocker in (candidate_result.get("blockers") or [])
        if _clean(blocker)
    ]
    if blockers:
        return _diagnostic_result(
            attempted=attempted,
            committed=False,
            rejected_targets=[
                _reject_target(target, "candidate_blocked", cand)
                for target, cand in targets
            ],
            reason="candidate_blocked",
            safety_gate_result=safety_gate,
            canonical_path_advanced=bool(candidate_result.get("canonical_path_advanced", False)),
            mandatory_beat_consumed=bool(candidate_result.get("mandatory_beat_consumed", False)),
            audit={**base_audit, "blockers": sorted(set(blockers))},
        )
    if bool(candidate_result.get("canonical_path_advanced")):
        return _diagnostic_result(
            attempted=attempted,
            committed=False,
            rejected_targets=[
                _reject_target(target, BLOCKER_CANONICAL_PATH_ADVANCE_ATTEMPTED, cand)
                for target, cand in targets
            ],
            reason=BLOCKER_CANONICAL_PATH_ADVANCE_ATTEMPTED,
            safety_gate_result=safety_gate,
            canonical_path_advanced=True,
            mandatory_beat_consumed=bool(candidate_result.get("mandatory_beat_consumed", False)),
            audit=base_audit,
        )
    if bool(candidate_result.get("mandatory_beat_consumed")):
        return _diagnostic_result(
            attempted=attempted,
            committed=False,
            rejected_targets=[
                _reject_target(target, BLOCKER_MANDATORY_BEAT_CONSUME_ATTEMPTED, cand)
                for target, cand in targets
            ],
            reason=BLOCKER_MANDATORY_BEAT_CONSUME_ATTEMPTED,
            safety_gate_result=safety_gate,
            canonical_path_advanced=False,
            mandatory_beat_consumed=True,
            audit=base_audit,
        )

    committed_targets: list[str] = []
    rejected_targets: list[dict[str, Any]] = []
    target_results: list[dict[str, Any]] = []
    audit: dict[str, Any] = dict(base_audit)
    max_commits = int(policy.get("max_commits_per_tick") or 0)
    allowed_kinds = set(policy.get("allowed_candidate_kinds") or [])

    for target, candidate in targets:
        if len(committed_targets) >= max_commits:
            rejected_targets.append(
                _reject_target(target, "max_commits_per_tick_exceeded", candidate)
            )
            continue
        kind = _clean(candidate.get("candidate_kind"))
        if kind not in RECOGNIZED_CANDIDATE_KINDS:
            rejected_targets.append(
                _reject_target(target, "candidate_kind_unrecognized", candidate)
            )
            continue
        if kind not in allowed_kinds:
            rejected_targets.append(
                _reject_target(target, "candidate_kind_not_allowed", candidate)
            )
            continue
        if (
            target == COMMIT_TARGET_RELATIONSHIP_STATE
            and kind != CANDIDATE_KIND_RELATIONSHIP_TENSION_UPDATE
        ) or (
            target == COMMIT_TARGET_HIERARCHICAL_MEMORY
            and kind != CANDIDATE_KIND_OFF_STAGE_MEMORY_NOTE
        ):
            rejected_targets.append(
                _reject_target(target, "candidate_target_mismatch", candidate)
            )
            continue
        candidate_blockers = validate_external_candidate(
            candidate,
            known_actor_ids=list(inputs.known_actor_ids),
            known_room_ids=list(inputs.known_room_ids),
        )
        if candidate_blockers:
            rejected_targets.append(
                _reject_target(target, ",".join(candidate_blockers), candidate)
            )
            continue

        if target == COMMIT_TARGET_RELATIONSHIP_STATE:
            target_result = _commit_relationship_candidate(
                candidate=candidate,
                prior_record=inputs.relationship_state_record,
                turn_number=inputs.turn_number,
                module_runtime_policy=inputs.module_runtime_policy,
            )
        else:
            target_result = _commit_memory_candidate(
                candidate=candidate,
                prior_snapshot=inputs.hierarchical_memory_snapshot,
                memory_policy=inputs.hierarchical_memory_policy,
                module_id=inputs.module_id,
                runtime_profile_id=inputs.runtime_profile_id,
                turn_number=inputs.turn_number,
            )
        target_results.append(target_result)
        if target_result.get("committed"):
            committed_targets.append(target)
            if isinstance(target_result.get("audit"), dict):
                audit[target] = target_result["audit"]
        else:
            rejected_targets.append(
                _reject_target(
                    target,
                    str(target_result.get("reason") or "target_rejected"),
                    candidate,
                )
            )

    committed = bool(committed_targets)
    reason = "committed" if committed else (
        rejected_targets[0]["reason"] if rejected_targets else "no_targets_committed"
    )
    return _diagnostic_result(
        attempted=attempted,
        committed=committed,
        committed_targets=committed_targets,
        rejected_targets=rejected_targets,
        reason=reason,
        safety_gate_result=safety_gate,
        canonical_path_advanced=False,
        mandatory_beat_consumed=False,
        target_results=target_results,
        audit=audit,
    )


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
    "RECOGNIZED_CANDIDATE_KINDS",
    "OFF_STAGE_UPDATES_POLICY_SCHEMA_VERSION",
    "OFF_STAGE_COMMIT_RESULT_SCHEMA_VERSION",
    "COMMIT_TARGET_RELATIONSHIP_STATE",
    "COMMIT_TARGET_HIERARCHICAL_MEMORY",
    "DEFAULT_ALLOWED_CANDIDATE_KINDS",
    "OffStageUpdateInputs",
    "OffStageCommitInputs",
    "normalize_off_stage_updates_policy",
    "build_off_stage_update_candidate",
    "validate_external_candidate",
    "build_default_off_stage_commit_result",
    "commit_off_stage_update_candidates",
]
