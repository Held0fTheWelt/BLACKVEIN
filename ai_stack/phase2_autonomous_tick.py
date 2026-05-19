"""Phase 2 Stage E — Autonomous Director Tick Coordinator.

Wraps the Phase 2 Director shadow path (``evaluate_director_tick``) and the
WS session loop with an explicit, event-driven autonomous-tick promotion
layer. Stage E is the first stage in which the Director may *emit* a block
for an NPC without an immediately preceding player input — but only when a
real, event-driven trigger fires.

Hard boundaries (ADR-0058 §"Stage E"):

* Fail-closed feature flag ``PHASE2_AUTONOMOUS_TICK_ENABLED``. Off by default.
* Triggers are *event-driven only*. No wall-clock polling, no background
  scheduler, no per-second heartbeat. The coordinator is invoked by the
  WS session loop (or any other call site) at a discrete, observable moment.
* Each tick evaluation may emit *at most one* ``block_stream_event.v1``.
* Silence is a first-class outcome with its own ``silence_reason``.
* Cooldown is content-policy driven (``min_tick_interval_ms`` from
  the module's ``runtime_intelligence.pacing_rhythm`` policy or a caller
  override). Cooldowns block emission, never block diagnostics.
* The coordinator never mutates committed turn state, never advances the
  canonical path, never consumes a mandatory beat, never changes
  ``validation_outcome``.
* When ``gathering_paused`` is true the coordinator may still emit an
  *autonomous off-stage NPC reaction* (one block, no beat consumption),
  but never a mandatory beat. The flag's authority over beat semantics
  remains with ADR-0061.
* No hardcoded actor IDs, room IDs, verb whitelists, or speaker rotations.
* No Pi/Π runtime keys.

Governance:
* ADR-0058 — Director-Driven Pulse and Block-Stream-Bus
* ADR-0059 — Semantic NPC Motivation Score
* ADR-0061 — Director Gathering State (gathering_paused)
* ADR-0039 — No Pi/Π runtime keys; semantic names only
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Final

from ai_stack.director_pulse_contracts import (
    ACTION_SILENCE,
    ACTION_SPEAK,
    BLOCK_TYPE_ACTOR_LINE,
    CUT_IN_UNINTERRUPTED,
    LANE_VISIBLE_SCENE_OUTPUT,
    TRIGGER_COOLDOWN_CHECK,
    TRIGGER_KINDS,
    TRIGGER_MOTIVATION_THRESHOLD_CROSSED,
    TRIGGER_PLAYER_INPUT,
    TRIGGER_STATE_CHANGE,
    build_block_stream_event,
)
from ai_stack.director_pulse_shadow import evaluate_director_tick
from ai_stack.phase2_off_stage_updates import (
    OffStageCommitInputs,
    OffStageUpdateInputs,
    SAFETY_GATE_BLOCKED,
    build_default_off_stage_commit_result,
    build_off_stage_update_candidate,
    commit_off_stage_update_candidates,
)
from ai_stack.phase2_stream_readiness import (
    classify_capability_availability,
    classify_motivation_component_sources,
)

# ── Feature flag ──────────────────────────────────────────────────────────────

PHASE2_AUTONOMOUS_TICK_ENABLED: Final[str] = "PHASE2_AUTONOMOUS_TICK_ENABLED"
PHASE2_AUTONOMOUS_PAUSE_LOOP_ENABLED: Final[str] = (
    "PHASE2_AUTONOMOUS_PAUSE_LOOP_ENABLED"
)

_TRUE_VALUES: Final[frozenset[str]] = frozenset(("1", "true", "yes", "on"))


def is_autonomous_tick_enabled() -> bool:
    """True when Stage E autonomous Director ticks are enabled server-side.

    Fail-closed: any unset / unparseable value is treated as disabled.
    """
    raw = os.environ.get(PHASE2_AUTONOMOUS_TICK_ENABLED, "false")
    return str(raw or "").strip().lower() in _TRUE_VALUES


def is_autonomous_pause_loop_enabled() -> bool:
    """True when Stage H multi-tick pause loops are enabled server-side.

    Fail-closed and separate from the single-tick flag: enabling autonomous
    ticks does not automatically enable repeated pause-loop evaluation.
    """
    raw = os.environ.get(PHASE2_AUTONOMOUS_PAUSE_LOOP_ENABLED, "false")
    return str(raw or "").strip().lower() in _TRUE_VALUES


# ── Suppression reasons (closed enum) ────────────────────────────────────────

SUPPRESS_FLAG_DISABLED: Final[str] = "flag_disabled"
SUPPRESS_NO_NPCS_PRESENT: Final[str] = "no_npcs_present"
SUPPRESS_COOLDOWN_ACTIVE: Final[str] = "cooldown_active"
SUPPRESS_PENDING_PLAYER_INPUT: Final[str] = "pending_player_input"
SUPPRESS_INVALID_TRIGGER: Final[str] = "invalid_trigger"
SUPPRESS_ALREADY_EMITTING: Final[str] = "already_emitting"

SUPPRESSION_REASONS: Final[frozenset[str]] = frozenset({
    SUPPRESS_FLAG_DISABLED,
    SUPPRESS_NO_NPCS_PRESENT,
    SUPPRESS_COOLDOWN_ACTIVE,
    SUPPRESS_PENDING_PLAYER_INPUT,
    SUPPRESS_INVALID_TRIGGER,
    SUPPRESS_ALREADY_EMITTING,
})


# ── Silence reasons (closed enum) ────────────────────────────────────────────

SILENCE_NO_NPC_ABOVE_THRESHOLD: Final[str] = "no_npc_above_motivation_threshold"
SILENCE_GATHERING_PAUSED_OFF_STAGE: Final[str] = "gathering_paused_off_stage_only"
SILENCE_DIRECTOR_CHOSE: Final[str] = "director_chose_silence"

SILENCE_REASONS: Final[frozenset[str]] = frozenset({
    SILENCE_NO_NPC_ABOVE_THRESHOLD,
    SILENCE_GATHERING_PAUSED_OFF_STAGE,
    SILENCE_DIRECTOR_CHOSE,
})


# ── Stage H loop triggers / stop reasons ─────────────────────────────────────

LOOP_TRIGGER_USER_PAUSE: Final[str] = "user_pause"
LOOP_TRIGGER_SILENCE: Final[str] = "silence"
LOOP_TRIGGER_GATHERING_PAUSED: Final[str] = "gathering_paused"

LOOP_TRIGGER_KINDS: Final[frozenset[str]] = frozenset({
    LOOP_TRIGGER_USER_PAUSE,
    LOOP_TRIGGER_SILENCE,
    LOOP_TRIGGER_GATHERING_PAUSED,
})

LOOP_STOP_DISABLED: Final[str] = "loop_disabled"
LOOP_STOP_INVALID_TRIGGER: Final[str] = "invalid_loop_trigger"
LOOP_STOP_MAX_TICKS: Final[str] = "max_ticks_per_pause"
LOOP_STOP_COOLDOWN_ACTIVE: Final[str] = "cooldown_active"
LOOP_STOP_ELAPSED_INPUT_MISSING: Final[str] = "elapsed_input_missing"
LOOP_STOP_PLAYER_CUT_IN: Final[str] = "player_cut_in"
LOOP_STOP_UNSAFE_CANDIDATE: Final[str] = "unsafe_candidate"
LOOP_STOP_NO_MOTIVATION_THRESHOLD: Final[str] = "no_motivation_threshold_crossed"
LOOP_STOP_TICK_SUPPRESSED: Final[str] = "tick_suppressed"


# ── Cooldown ──────────────────────────────────────────────────────────────────

_DEFAULT_MIN_TICK_INTERVAL_MS: Final[float] = 1500.0
_DEFAULT_MAX_TICKS_PER_PAUSE: Final[int] = 1


def resolve_min_tick_interval_ms(
    pacing_rhythm_policy: dict[str, Any] | None,
    explicit_override_ms: float | None,
) -> float:
    """Resolve cooldown interval from policy / explicit override / default."""
    if explicit_override_ms is not None:
        try:
            return max(0.0, float(explicit_override_ms))
        except (TypeError, ValueError):
            pass
    if isinstance(pacing_rhythm_policy, dict):
        raw = pacing_rhythm_policy.get("min_tick_interval_ms")
        if raw is not None:
            try:
                return max(0.0, float(raw))
            except (TypeError, ValueError):
                pass
    return _DEFAULT_MIN_TICK_INTERVAL_MS


def resolve_max_ticks_per_pause(
    pacing_rhythm_policy: dict[str, Any] | None,
    explicit_override: int | None = None,
) -> int:
    """Resolve the Stage H per-pause tick cap from policy / override."""
    raw = explicit_override
    if raw is None and isinstance(pacing_rhythm_policy, dict):
        raw = pacing_rhythm_policy.get("max_ticks_per_pause")
    try:
        parsed = int(raw) if raw is not None else _DEFAULT_MAX_TICKS_PER_PAUSE
    except (TypeError, ValueError):
        parsed = _DEFAULT_MAX_TICKS_PER_PAUSE
    return max(1, min(8, parsed))


def _cooldown_active(
    *,
    since_last_tick_ms: float | None,
    min_tick_interval_ms: float,
) -> bool:
    """Cooldown is active when fewer ms have elapsed than the policy minimum.

    ``since_last_tick_ms is None`` represents "no prior tick recorded",
    which is *not* a cooldown — first tick is always free.
    """
    if since_last_tick_ms is None:
        return False
    try:
        elapsed = float(since_last_tick_ms)
    except (TypeError, ValueError):
        return False
    return elapsed < min_tick_interval_ms


# ── Inputs / outcome ──────────────────────────────────────────────────────────


@dataclass
class AutonomousTickInputs:
    """Pure inputs for one autonomous-tick evaluation.

    Built by the caller (typically the WS session loop) from the freshly
    committed turn state. Pure data — no callbacks, no mutable refs.
    """

    trigger_kind: str = TRIGGER_MOTIVATION_THRESHOLD_CROSSED
    triggering_actor_id: str | None = None
    npc_ids: list[str] = field(default_factory=list)
    scene_energy_output: dict[str, Any] | None = None
    social_pressure_output: dict[str, Any] | None = None
    relationship_state_output: dict[str, Any] | None = None
    narrative_momentum_output: dict[str, Any] | None = None
    actor_pressure_profiles: dict[str, Any] | None = None
    npc_motivation_score_policy: dict[str, Any] | None = None
    pacing_rhythm_policy: dict[str, Any] | None = None
    gathering_paused: bool = False
    since_last_tick_ms: float | None = None
    min_tick_interval_ms_override: float | None = None
    pending_player_input: bool = False
    already_streaming_block: bool = False
    tick_id: str | None = None
    # Stage F — off-stage safety-gate context.
    visible_npc_ids: list[str] = field(default_factory=list)
    known_actor_ids: list[str] = field(default_factory=list)
    known_room_ids: list[str] = field(default_factory=list)
    # Stage G — opt-in off-stage commit policy/targets. Omitted means preview-only.
    off_stage_updates_policy: dict[str, Any] | None = None
    relationship_state_record: dict[str, Any] | None = None
    hierarchical_memory_snapshot: dict[str, Any] | None = None
    hierarchical_memory_policy: dict[str, Any] | None = None
    module_runtime_policy: dict[str, Any] | None = None
    module_id: str | None = None
    runtime_profile_id: str | None = None
    turn_number: int | None = None


@dataclass
class AutonomousTickOutcome:
    """Result of one autonomous-tick evaluation.

    A live (non-shadow) outcome: ``shadow_only`` is always False here. The
    coordinator decides whether to emit, but never *delivers* — that is the
    transport's job.

    Stage F additions:
        - ``capability_outputs_used`` / ``capability_outputs_missing``
        - ``motivation_score_component_sources``
        - ``off_stage_update_candidate`` (full Stage F scaffold result dict)
    """

    tick_id: str
    autonomous_tick_enabled: bool
    tick_trigger_kind: str
    chosen_actor_id: str | None
    chosen_action_kind: str
    block_stream_event: dict[str, Any] | None
    director_tick_decision: dict[str, Any]
    npc_motivation_scores: list[dict[str, Any]]
    motivation_scores: dict[str, float]
    silence_reason: str | None
    cooldown_state: dict[str, Any]
    autonomous_tick_suppressed_reason: str | None
    gathering_paused: bool
    capability_outputs_used: list[str] = field(default_factory=list)
    capability_outputs_missing: list[str] = field(default_factory=list)
    motivation_score_component_sources: dict[str, str] = field(default_factory=dict)
    off_stage_update_candidate: dict[str, Any] = field(default_factory=dict)
    off_stage_commit_result: dict[str, Any] = field(default_factory=dict)
    canonical_path_advanced: bool = False
    mandatory_beat_consumed: bool = False
    shadow_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick_id": self.tick_id,
            "autonomous_tick_enabled": self.autonomous_tick_enabled,
            "tick_trigger_kind": self.tick_trigger_kind,
            "chosen_actor_id": self.chosen_actor_id,
            "chosen_action_kind": self.chosen_action_kind,
            "block_stream_event": self.block_stream_event,
            "director_tick_decision": self.director_tick_decision,
            "npc_motivation_scores": list(self.npc_motivation_scores),
            "motivation_scores": dict(self.motivation_scores),
            "silence_reason": self.silence_reason,
            "cooldown_state": dict(self.cooldown_state),
            "autonomous_tick_suppressed_reason": self.autonomous_tick_suppressed_reason,
            "gathering_paused": self.gathering_paused,
            "capability_outputs_used": list(self.capability_outputs_used),
            "capability_outputs_missing": list(self.capability_outputs_missing),
            "motivation_score_component_sources": dict(self.motivation_score_component_sources),
            "off_stage_update_candidate": dict(self.off_stage_update_candidate),
            "off_stage_commit_result": dict(self.off_stage_commit_result),
            "canonical_path_advanced": self.canonical_path_advanced,
            "mandatory_beat_consumed": self.mandatory_beat_consumed,
            "shadow_only": self.shadow_only,
        }


@dataclass
class AutonomousPauseLoopInputs:
    """Pure Stage H loop inputs for a single explicit pause opportunity."""

    tick_inputs: AutonomousTickInputs
    loop_trigger_kind: str = LOOP_TRIGGER_USER_PAUSE
    max_ticks_per_pause: int | None = None
    elapsed_ms_between_ticks: list[float] = field(default_factory=list)
    player_cut_in_after_tick_index: int | None = None


@dataclass
class AutonomousPauseLoopOutcome:
    """Diagnostic result for one bounded autonomous pause loop."""

    loop_enabled: bool
    loop_trigger_kind: str
    tick_outcomes: list[AutonomousTickOutcome]
    stop_reason: str
    max_ticks_per_pause: int
    min_tick_interval_ms: float
    stopped_on_player_cut_in: bool = False
    stopped_on_unsafe_candidate: bool = False
    canonical_path_advanced: bool = False
    mandatory_beat_consumed: bool = False
    proof_level: str = "local_only"

    def to_dict(self) -> dict[str, Any]:
        return {
            "loop_enabled": self.loop_enabled,
            "loop_trigger_kind": self.loop_trigger_kind,
            "tick_count": len(self.tick_outcomes),
            "max_ticks_per_pause": self.max_ticks_per_pause,
            "min_tick_interval_ms": self.min_tick_interval_ms,
            "stop_reason": self.stop_reason,
            "stopped_on_player_cut_in": self.stopped_on_player_cut_in,
            "stopped_on_unsafe_candidate": self.stopped_on_unsafe_candidate,
            "canonical_path_advanced": self.canonical_path_advanced,
            "mandatory_beat_consumed": self.mandatory_beat_consumed,
            "proof_level": self.proof_level,
            "tick_summaries": [outcome.to_dict() for outcome in self.tick_outcomes],
        }


# ── Block-payload construction for autonomous emission ───────────────────────


def _build_actor_line_payload(
    *,
    chosen_actor_id: str,
    tick_id: str,
) -> dict[str, Any]:
    """Build a minimal ``actor_line`` block payload for an autonomous tick.

    The body text is deliberately empty — the runtime delivery layer fills
    in the actual narration. The coordinator only owns the *fact* of the
    emission, not the line itself.

    No hardcoded actor IDs (the value flows in from motivation scoring).
    No hardcoded verbs or rooms.
    """
    block_id = str(uuid.uuid4())
    return {
        "id": block_id,
        "block_type": BLOCK_TYPE_ACTOR_LINE,
        "actor_id": chosen_actor_id,
        "text": "",
        "originator": "autonomous_tick",
        "autonomous_tick_id": tick_id,
    }


# ── Trigger validation ────────────────────────────────────────────────────────


def _validate_trigger(trigger_kind: str) -> bool:
    return trigger_kind in TRIGGER_KINDS


def _candidate_is_unsafe(outcome: AutonomousTickOutcome) -> bool:
    candidate = (
        outcome.off_stage_update_candidate
        if isinstance(outcome.off_stage_update_candidate, dict)
        else {}
    )
    return candidate.get("off_stage_safety_gate_result") == SAFETY_GATE_BLOCKED


def _commit_artifacts_from_outcome(
    outcome: AutonomousTickOutcome,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    commit = (
        outcome.off_stage_commit_result
        if isinstance(outcome.off_stage_commit_result, dict)
        else {}
    )
    relationship_state: dict[str, Any] | None = None
    memory_snapshot: dict[str, Any] | None = None
    for row in commit.get("target_results") or []:
        if not isinstance(row, dict) or not row.get("committed"):
            continue
        if isinstance(row.get("relationship_state_record"), dict):
            relationship_state = row["relationship_state_record"]
        if isinstance(row.get("hierarchical_memory_snapshot"), dict):
            memory_snapshot = row["hierarchical_memory_snapshot"]
    return relationship_state, memory_snapshot


# ── Public API ────────────────────────────────────────────────────────────────


def should_emit_autonomous_tick(
    *,
    inputs: AutonomousTickInputs,
    enabled: bool | None = None,
) -> tuple[bool, str | None]:
    """Pure pre-check: should this autonomous-tick evaluation even run?

    Returns ``(allowed, suppression_reason)``. When ``allowed`` is True the
    caller should proceed to ``evaluate_autonomous_tick``. When False the
    caller should record ``suppression_reason`` (a closed enum value) and
    skip emission.

    The pre-check is event-driven only. There is no time-based path here.
    """
    if enabled is None:
        enabled = is_autonomous_tick_enabled()
    if not enabled:
        return False, SUPPRESS_FLAG_DISABLED
    if not _validate_trigger(inputs.trigger_kind):
        return False, SUPPRESS_INVALID_TRIGGER
    if inputs.pending_player_input:
        return False, SUPPRESS_PENDING_PLAYER_INPUT
    if inputs.already_streaming_block:
        return False, SUPPRESS_ALREADY_EMITTING
    if not inputs.npc_ids:
        return False, SUPPRESS_NO_NPCS_PRESENT
    min_interval = resolve_min_tick_interval_ms(
        inputs.pacing_rhythm_policy,
        inputs.min_tick_interval_ms_override,
    )
    if _cooldown_active(
        since_last_tick_ms=inputs.since_last_tick_ms,
        min_tick_interval_ms=min_interval,
    ):
        return False, SUPPRESS_COOLDOWN_ACTIVE
    return True, None


def evaluate_autonomous_tick(
    inputs: AutonomousTickInputs,
    *,
    enabled: bool | None = None,
) -> AutonomousTickOutcome:
    """Evaluate one autonomous Director tick and return the outcome.

    Pipeline:
        1. Pre-check (flag, trigger validity, cooldown, no pending input,
           no in-flight block, NPCs present).
        2. If allowed: invoke ``evaluate_director_tick`` (shadow contract)
           to compute per-NPC motivation scores and pick an initiative
           actor.
        3. If an actor crosses threshold: build one ``block_stream_event.v1``
           with ``block_type=actor_line``, ``originator=autonomous_tick``.
        4. Else: record silence with a closed-enum ``silence_reason``.

    Hard guarantees:
        * ``canonical_path_advanced`` and ``mandatory_beat_consumed`` are
          always False — the coordinator never touches either.
        * ``shadow_only`` is always False — this is the live emission path.
        * Cooldown state is always reported so the caller can update its
          tick timestamp.
    """
    if enabled is None:
        enabled = is_autonomous_tick_enabled()
    resolved_tick_id = inputs.tick_id or str(uuid.uuid4())
    min_interval = resolve_min_tick_interval_ms(
        inputs.pacing_rhythm_policy,
        inputs.min_tick_interval_ms_override,
    )
    cooldown_state = {
        "min_tick_interval_ms": min_interval,
        "since_last_tick_ms": inputs.since_last_tick_ms,
        "cooldown_active": _cooldown_active(
            since_last_tick_ms=inputs.since_last_tick_ms,
            min_tick_interval_ms=min_interval,
        ),
    }

    # Stage F — capability availability + per-component source labels are
    # always emitted, even when the tick is suppressed.
    capability_outputs_used, capability_outputs_missing = classify_capability_availability(
        scene_energy_output=inputs.scene_energy_output,
        social_pressure_output=inputs.social_pressure_output,
        relationship_state_output=inputs.relationship_state_output,
        narrative_momentum_output=inputs.narrative_momentum_output,
        actor_pressure_profiles=inputs.actor_pressure_profiles,
        npc_motivation_score_policy=inputs.npc_motivation_score_policy,
        pacing_rhythm_policy=inputs.pacing_rhythm_policy,
    )
    component_sources = classify_motivation_component_sources(
        scene_energy_output=inputs.scene_energy_output,
        social_pressure_output=inputs.social_pressure_output,
        relationship_state_output=inputs.relationship_state_output,
        narrative_momentum_output=inputs.narrative_momentum_output,
        actor_pressure_profiles=inputs.actor_pressure_profiles,
        npc_motivation_score_policy=inputs.npc_motivation_score_policy,
    )

    allowed, suppression = should_emit_autonomous_tick(inputs=inputs, enabled=enabled)

    if not allowed:
        # Build a silence director_tick_decision so the audit trail is
        # complete even when emission is suppressed.
        from ai_stack.director_pulse_contracts import build_director_tick_decision

        composition_inputs: list[str] = []
        silent_decision = build_director_tick_decision(
            trigger_kind=inputs.trigger_kind if _validate_trigger(inputs.trigger_kind) else TRIGGER_STATE_CHANGE,
            triggering_actor_id=inputs.triggering_actor_id,
            chosen_action_kind=ACTION_SILENCE,
            chosen_actor_id=None,
            composition_inputs=composition_inputs,
            since_last_tick_ms=inputs.since_last_tick_ms,
            silence_reason=SILENCE_DIRECTOR_CHOSE,
            tick_id=resolved_tick_id,
        )
        suppressed_off_stage = build_off_stage_update_candidate(
            OffStageUpdateInputs(
                tick_id=resolved_tick_id,
                chosen_actor_id=None,
                chosen_action_kind=ACTION_SILENCE,
                motivation_scores={},
                visible_npc_ids=list(inputs.visible_npc_ids),
                known_actor_ids=list(inputs.known_actor_ids),
                known_room_ids=list(inputs.known_room_ids),
                gathering_paused=inputs.gathering_paused,
            )
        )
        suppressed_commit_result = build_default_off_stage_commit_result(
            suppressed_off_stage,
            reason="no_off_stage_candidate",
        )
        return AutonomousTickOutcome(
            tick_id=resolved_tick_id,
            autonomous_tick_enabled=enabled,
            tick_trigger_kind=inputs.trigger_kind,
            chosen_actor_id=None,
            chosen_action_kind=ACTION_SILENCE,
            block_stream_event=None,
            director_tick_decision=silent_decision,
            npc_motivation_scores=[],
            motivation_scores={},
            silence_reason=SILENCE_DIRECTOR_CHOSE,
            cooldown_state=cooldown_state,
            autonomous_tick_suppressed_reason=suppression,
            gathering_paused=inputs.gathering_paused,
            capability_outputs_used=capability_outputs_used,
            capability_outputs_missing=capability_outputs_missing,
            motivation_score_component_sources=component_sources,
            off_stage_update_candidate=suppressed_off_stage,
            off_stage_commit_result=suppressed_commit_result,
        )

    # Allowed — delegate the actor-selection logic to evaluate_director_tick.
    shadow = evaluate_director_tick(
        trigger_kind=inputs.trigger_kind,
        triggering_actor_id=inputs.triggering_actor_id,
        npc_ids=list(inputs.npc_ids),
        scene_energy_output=inputs.scene_energy_output,
        social_pressure_output=inputs.social_pressure_output,
        relationship_state_output=inputs.relationship_state_output,
        narrative_momentum_output=inputs.narrative_momentum_output,
        actor_pressure_profiles=inputs.actor_pressure_profiles,
        npc_motivation_score_policy=inputs.npc_motivation_score_policy,
        gathering_paused=inputs.gathering_paused,
        since_last_tick_ms=inputs.since_last_tick_ms,
        current_block_id=None,
        current_block_type=None,
        block_payload=None,
        player_input_payload=None,
        tick_id=resolved_tick_id,
    )

    tick_decision: dict[str, Any] = dict(shadow["director_tick_decision"])
    motivation_scores: list[dict[str, Any]] = list(shadow["npc_motivation_scores"])
    score_map: dict[str, float] = {
        str(s.get("npc_id") or ""): float(s.get("score") or 0.0)
        for s in motivation_scores
        if isinstance(s, dict)
    }

    chosen_actor: str | None = tick_decision.get("chosen_actor_id")
    chosen_action: str = str(tick_decision.get("chosen_action_kind") or ACTION_SILENCE)

    block_event: dict[str, Any] | None = None
    silence_reason: str | None = None

    if chosen_action == ACTION_SPEAK and chosen_actor:
        payload = _build_actor_line_payload(
            chosen_actor_id=chosen_actor,
            tick_id=resolved_tick_id,
        )
        block_event = build_block_stream_event(
            tick_id=resolved_tick_id,
            block_type=BLOCK_TYPE_ACTOR_LINE,
            block_payload=payload,
            cut_in_state=CUT_IN_UNINTERRUPTED,
            lane=LANE_VISIBLE_SCENE_OUTPUT,
            source=chosen_actor,
        )
    else:
        # Director chose silence — pick the most specific reason available.
        if inputs.gathering_paused:
            silence_reason = SILENCE_GATHERING_PAUSED_OFF_STAGE
        else:
            silence_reason = SILENCE_NO_NPC_ABOVE_THRESHOLD
        # Make sure the tick_decision reflects the same reason for audit parity.
        tick_decision["silence_reason"] = silence_reason
        tick_decision["chosen_action_kind"] = ACTION_SILENCE
        tick_decision["chosen_actor_id"] = None

    off_stage_result = build_off_stage_update_candidate(
        OffStageUpdateInputs(
            tick_id=resolved_tick_id,
            chosen_actor_id=chosen_actor if block_event else None,
            chosen_action_kind=chosen_action if block_event else ACTION_SILENCE,
            motivation_scores=score_map,
            visible_npc_ids=list(inputs.visible_npc_ids),
            known_actor_ids=list(inputs.known_actor_ids),
            known_room_ids=list(inputs.known_room_ids),
            gathering_paused=inputs.gathering_paused,
        )
    )
    off_stage_commit_result = commit_off_stage_update_candidates(
        OffStageCommitInputs(
            candidate_result=off_stage_result,
            policy=inputs.off_stage_updates_policy,
            known_actor_ids=list(inputs.known_actor_ids),
            known_room_ids=list(inputs.known_room_ids),
            relationship_state_record=inputs.relationship_state_record
            or inputs.relationship_state_output,
            hierarchical_memory_snapshot=inputs.hierarchical_memory_snapshot,
            hierarchical_memory_policy=inputs.hierarchical_memory_policy,
            module_runtime_policy=inputs.module_runtime_policy,
            module_id=inputs.module_id,
            runtime_profile_id=inputs.runtime_profile_id,
            turn_number=inputs.turn_number,
        )
    )

    return AutonomousTickOutcome(
        tick_id=resolved_tick_id,
        autonomous_tick_enabled=enabled,
        tick_trigger_kind=inputs.trigger_kind,
        chosen_actor_id=chosen_actor if block_event else None,
        chosen_action_kind=chosen_action if block_event else ACTION_SILENCE,
        block_stream_event=block_event,
        director_tick_decision=tick_decision,
        npc_motivation_scores=motivation_scores,
        motivation_scores=score_map,
        silence_reason=silence_reason,
        cooldown_state=cooldown_state,
        autonomous_tick_suppressed_reason=None,
        gathering_paused=inputs.gathering_paused,
        capability_outputs_used=capability_outputs_used,
        capability_outputs_missing=capability_outputs_missing,
        motivation_score_component_sources=component_sources,
        off_stage_update_candidate=off_stage_result,
        off_stage_commit_result=off_stage_commit_result,
    )


def evaluate_autonomous_pause_loop(
    inputs: AutonomousPauseLoopInputs,
    *,
    enabled: bool | None = None,
    tick_enabled: bool | None = None,
) -> AutonomousPauseLoopOutcome:
    """Evaluate a bounded Stage H autonomous loop for an explicit pause.

    This pure coordinator never sleeps and never schedules by itself. Callers
    must provide elapsed evidence for ticks after the first one, which keeps
    repeated evaluations tied to an explicit pause opportunity rather than an
    ambient timer.
    """
    loop_enabled = is_autonomous_pause_loop_enabled() if enabled is None else bool(enabled)
    min_interval = resolve_min_tick_interval_ms(
        inputs.tick_inputs.pacing_rhythm_policy,
        inputs.tick_inputs.min_tick_interval_ms_override,
    )
    max_ticks = resolve_max_ticks_per_pause(
        inputs.tick_inputs.pacing_rhythm_policy,
        inputs.max_ticks_per_pause,
    )
    if not loop_enabled:
        return AutonomousPauseLoopOutcome(
            loop_enabled=False,
            loop_trigger_kind=inputs.loop_trigger_kind,
            tick_outcomes=[],
            stop_reason=LOOP_STOP_DISABLED,
            max_ticks_per_pause=max_ticks,
            min_tick_interval_ms=min_interval,
        )
    if inputs.loop_trigger_kind not in LOOP_TRIGGER_KINDS:
        return AutonomousPauseLoopOutcome(
            loop_enabled=True,
            loop_trigger_kind=inputs.loop_trigger_kind,
            tick_outcomes=[],
            stop_reason=LOOP_STOP_INVALID_TRIGGER,
            max_ticks_per_pause=max_ticks,
            min_tick_interval_ms=min_interval,
        )

    outcomes: list[AutonomousTickOutcome] = []
    stop_reason = LOOP_STOP_MAX_TICKS
    stopped_on_player_cut_in = False
    stopped_on_unsafe_candidate = False
    relationship_state = inputs.tick_inputs.relationship_state_record
    memory_snapshot = inputs.tick_inputs.hierarchical_memory_snapshot

    for tick_index in range(max_ticks):
        if tick_index == 0:
            since_last_tick_ms = inputs.tick_inputs.since_last_tick_ms
        else:
            elapsed_index = tick_index - 1
            if elapsed_index >= len(inputs.elapsed_ms_between_ticks):
                stop_reason = LOOP_STOP_ELAPSED_INPUT_MISSING
                break
            since_last_tick_ms = inputs.elapsed_ms_between_ticks[elapsed_index]

        tick_inputs = replace(
            inputs.tick_inputs,
            tick_id=(inputs.tick_inputs.tick_id if tick_index == 0 else str(uuid.uuid4())),
            since_last_tick_ms=since_last_tick_ms,
            relationship_state_record=relationship_state,
            hierarchical_memory_snapshot=memory_snapshot,
            pending_player_input=False,
            already_streaming_block=False,
        )
        outcome = evaluate_autonomous_tick(tick_inputs, enabled=tick_enabled)
        outcomes.append(outcome)

        committed_relationship, committed_memory = _commit_artifacts_from_outcome(outcome)
        if committed_relationship is not None:
            relationship_state = committed_relationship
        if committed_memory is not None:
            memory_snapshot = committed_memory

        if inputs.player_cut_in_after_tick_index == tick_index:
            stop_reason = LOOP_STOP_PLAYER_CUT_IN
            stopped_on_player_cut_in = True
            break
        if outcome.autonomous_tick_suppressed_reason == SUPPRESS_COOLDOWN_ACTIVE:
            stop_reason = LOOP_STOP_COOLDOWN_ACTIVE
            break
        if outcome.autonomous_tick_suppressed_reason:
            stop_reason = LOOP_STOP_TICK_SUPPRESSED
            break
        if _candidate_is_unsafe(outcome):
            stop_reason = LOOP_STOP_UNSAFE_CANDIDATE
            stopped_on_unsafe_candidate = True
            break
        if outcome.block_stream_event is None:
            stop_reason = LOOP_STOP_NO_MOTIVATION_THRESHOLD
            break

    return AutonomousPauseLoopOutcome(
        loop_enabled=True,
        loop_trigger_kind=inputs.loop_trigger_kind,
        tick_outcomes=outcomes,
        stop_reason=stop_reason,
        max_ticks_per_pause=max_ticks,
        min_tick_interval_ms=min_interval,
        stopped_on_player_cut_in=stopped_on_player_cut_in,
        stopped_on_unsafe_candidate=stopped_on_unsafe_candidate,
        canonical_path_advanced=False,
        mandatory_beat_consumed=False,
    )


__all__ = [
    "PHASE2_AUTONOMOUS_TICK_ENABLED",
    "PHASE2_AUTONOMOUS_PAUSE_LOOP_ENABLED",
    "is_autonomous_tick_enabled",
    "is_autonomous_pause_loop_enabled",
    "SUPPRESS_FLAG_DISABLED",
    "SUPPRESS_NO_NPCS_PRESENT",
    "SUPPRESS_COOLDOWN_ACTIVE",
    "SUPPRESS_PENDING_PLAYER_INPUT",
    "SUPPRESS_INVALID_TRIGGER",
    "SUPPRESS_ALREADY_EMITTING",
    "SUPPRESSION_REASONS",
    "SILENCE_NO_NPC_ABOVE_THRESHOLD",
    "SILENCE_GATHERING_PAUSED_OFF_STAGE",
    "SILENCE_DIRECTOR_CHOSE",
    "SILENCE_REASONS",
    "LOOP_TRIGGER_USER_PAUSE",
    "LOOP_TRIGGER_SILENCE",
    "LOOP_TRIGGER_GATHERING_PAUSED",
    "LOOP_TRIGGER_KINDS",
    "LOOP_STOP_DISABLED",
    "LOOP_STOP_INVALID_TRIGGER",
    "LOOP_STOP_MAX_TICKS",
    "LOOP_STOP_COOLDOWN_ACTIVE",
    "LOOP_STOP_ELAPSED_INPUT_MISSING",
    "LOOP_STOP_PLAYER_CUT_IN",
    "LOOP_STOP_UNSAFE_CANDIDATE",
    "LOOP_STOP_NO_MOTIVATION_THRESHOLD",
    "LOOP_STOP_TICK_SUPPRESSED",
    "AutonomousTickInputs",
    "AutonomousTickOutcome",
    "AutonomousPauseLoopInputs",
    "AutonomousPauseLoopOutcome",
    "resolve_min_tick_interval_ms",
    "resolve_max_ticks_per_pause",
    "should_emit_autonomous_tick",
    "evaluate_autonomous_tick",
    "evaluate_autonomous_pause_loop",
]
