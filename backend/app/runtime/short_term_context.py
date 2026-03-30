"""W2.3.1 — Canonical short-term turn context for AI-driven story execution.

Provides a bounded, deterministic representation of immediately recent turn
information suitable for AI request construction and runtime diagnostics.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.runtime.turn_executor import TurnExecutionResult


class ShortTermTurnContext(BaseModel):
    """Bounded short-term context from a single completed turn.

    Captures only the most relevant immediately recent information:
    - current scene state
    - what fired (detected triggers)
    - what changed (accepted delta targets)
    - what was blocked (rejected delta targets)
    - guard outcome classification
    - scene/ending transitions

    Intentionally excludes:
    - full canonical_state (too large for context window)
    - full StateDelta objects (only target paths included)
    - narrative_text / rationale (prompt prose, not runtime context)
    - historical turns (single-turn scope only)
    - character/relationship detail (W2.3.2/W2.3.3 concern)

    Attributes:
        turn_number: The turn number this context was derived from.
        scene_id: The current scene ID after the turn completed.
        detected_triggers: Triggers that fired this turn.
        accepted_delta_targets: Dot-paths of deltas that passed validation.
        rejected_delta_targets: Dot-paths of deltas that were blocked.
        guard_outcome: Classification of the turn's guard result.
        scene_changed: Whether a scene transition occurred this turn.
        prior_scene_id: The scene before the transition, if one occurred.
        ending_reached: Whether an ending was triggered this turn.
        ending_id: The ending ID if an ending was reached.
        conflict_pressure: conflict_state.pressure from canonical_state, if present.
        created_at: When this context was derived.
    """

    turn_number: int
    scene_id: str
    detected_triggers: list[str] = Field(default_factory=list)
    accepted_delta_targets: list[str] = Field(default_factory=list)
    rejected_delta_targets: list[str] = Field(default_factory=list)
    guard_outcome: str
    scene_changed: bool = False
    prior_scene_id: str | None = None
    ending_reached: bool = False
    ending_id: str | None = None
    conflict_pressure: int | float | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # W3 Diagnostic Persistence
    execution_result_full: dict | None = None  # Full execution result for UI diagnostics
    ai_decision_log_full: dict | None = None  # Full AI decision log for LLM pipeline visibility


def build_short_term_context(
    result: TurnExecutionResult,
    prior_scene_id: str | None = None,
) -> ShortTermTurnContext:
    """Derive a short-term turn context from a completed turn execution result.

    Selects only immediately relevant information — not a full state dump.

    Args:
        result: The TurnExecutionResult from the completed turn.
        prior_scene_id: The scene ID before this turn began (used to detect transitions).

    Returns:
        A bounded ShortTermTurnContext for the next AI/runtime step.
    """
    scene_id = result.updated_scene_id or ""
    scene_changed = bool(prior_scene_id and scene_id and scene_id != prior_scene_id)

    conflict_pressure = None
    if result.updated_canonical_state:
        conflict_state = result.updated_canonical_state.get("conflict_state", {})
        if isinstance(conflict_state, dict):
            conflict_pressure = conflict_state.get("pressure")

    # W3 Closure: Fetch latest AIDecisionLog from canonical storage
    # The real source is session.metadata["ai_decision_logs"]
    ai_decision_log_full = None
    try:
        if (hasattr(session, 'metadata') and
            isinstance(session.metadata, dict) and
            "ai_decision_logs" in session.metadata and
            session.metadata["ai_decision_logs"]):
            latest_log = session.metadata["ai_decision_logs"][-1]
            # Serialize AIDecisionLog to dict if it's a Pydantic model
            if hasattr(latest_log, 'model_dump'):
                ai_decision_log_full = latest_log.model_dump(mode='json')
            else:
                ai_decision_log_full = latest_log  # Already a dict
    except Exception:
        # Gracefully handle any access issues
        ai_decision_log_full = None

    return ShortTermTurnContext(
        turn_number=result.turn_number,
        scene_id=scene_id,
        detected_triggers=list(result.decision.detected_triggers or []),
        accepted_delta_targets=[d.target_path for d in result.accepted_deltas],
        rejected_delta_targets=[d.target_path for d in result.rejected_deltas],
        guard_outcome=result.guard_outcome.value,
        scene_changed=scene_changed,
        prior_scene_id=prior_scene_id if scene_changed else None,
        ending_reached=bool(result.updated_ending_id),
        ending_id=result.updated_ending_id,
        conflict_pressure=conflict_pressure,
        # W3 Diagnostic Persistence
        execution_result_full=result.model_dump(mode='json') if hasattr(result, 'model_dump') else result,
        ai_decision_log_full=ai_decision_log_full,
    )
