"""W2.3.1 — Canonical short-term turn context for AI-driven story execution.

Provides a bounded, deterministic representation of immediately recent turn
information suitable for AI request construction and runtime diagnostics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.runtime.turn_executor import TurnExecutionResult

# Task 1C: bounded narrative fields derived from narrative_commit (JSON-safe).
_MAX_CANONICAL_CONSEQUENCES = 24
_MAX_CONSEQUENCE_STRING_LEN = 256
_MAX_AUTHORITATIVE_REASON_LEN = 500


def _cap_str(value: str | None, max_len: int) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _cap_consequence_list(items: list[str] | None) -> list[str]:
    if not items:
        return []
    out: list[str] = []
    for raw in items[:_MAX_CANONICAL_CONSEQUENCES]:
        token = str(raw).strip()
        if not token:
            continue
        if len(token) > _MAX_CONSEQUENCE_STRING_LEN:
            token = token[: _MAX_CONSEQUENCE_STRING_LEN - 1] + "…"
        out.append(token)
    return out


class ShortTermTurnContext(BaseModel):
    """Bounded short-term context from a single completed turn.

    Captures only the most relevant immediately recent information:
    - current scene state
    - what fired (detected triggers)
    - what changed (accepted delta targets)
    - what was blocked (rejected delta targets)
    - guard outcome classification
    - scene/ending transitions
    - Task 1C: authoritative narrative markers from narrative_commit when present

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
        situation_status: Post-turn situation from narrative_commit when present.
        canonical_consequences: Bounded consequence tokens from narrative_commit.
        authoritative_reason: Bounded commit reason when present.
        is_terminal: True when commit marks a terminal ending.
        active_thread_ids: Task 1D compact thread id list (filled after thread derivation).
        dominant_thread_kind: Kind of the highest-pressure active thread, if any.
        thread_pressure_level: Max intensity among active threads (0–5).
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

    situation_status: str = ""
    canonical_consequences: list[str] = Field(default_factory=list)
    authoritative_reason: str | None = None
    is_terminal: bool = False

    active_thread_ids: list[str] = Field(default_factory=list)
    dominant_thread_kind: str = ""
    thread_pressure_level: int = 0

    # W3 Diagnostic Persistence
    execution_result_full: dict | None = None  # Full execution result for UI diagnostics
    ai_decision_log_full: dict | None = None  # Full AI decision log for LLM pipeline visibility


def build_short_term_context(
    result: TurnExecutionResult,
    prior_scene_id: str | None = None,
    session_state: Any = None,
) -> ShortTermTurnContext:
    """Derive a short-term turn context from a completed turn execution result.

    Selects only immediately relevant information — not a full state dump.
    When ``result.narrative_commit`` is set, post-turn narrative fields prefer that
    authoritative record (Task 1C).

    Args:
        result: The TurnExecutionResult from the completed turn.
        prior_scene_id: The scene ID before this turn began (used to detect transitions).
        session_state: Optional SessionState; when set, latest entry from
            ``metadata["ai_decision_logs"]`` is copied into ``ai_decision_log_full``.

    Returns:
        A bounded ShortTermTurnContext for the next AI/runtime step.
    """
    nc = result.narrative_commit

    conflict_pressure = None
    if result.updated_canonical_state:
        conflict_state = result.updated_canonical_state.get("conflict_state", {})
        if isinstance(conflict_state, dict):
            conflict_pressure = conflict_state.get("pressure")

    ai_decision_log_full = None
    try:
        if (
            session_state is not None
            and hasattr(session_state, "metadata")
            and isinstance(session_state.metadata, dict)
            and "ai_decision_logs" in session_state.metadata
            and session_state.metadata["ai_decision_logs"]
        ):
            latest_log = session_state.metadata["ai_decision_logs"][-1]
            if hasattr(latest_log, "model_dump"):
                ai_decision_log_full = latest_log.model_dump(mode="json")
            else:
                ai_decision_log_full = latest_log
    except Exception:
        ai_decision_log_full = None

    if nc is not None:
        scene_id = nc.committed_scene_id or ""
        scene_changed = bool(
            prior_scene_id and scene_id and scene_id != prior_scene_id
        )
        ending_id = nc.committed_ending_id
        ending_reached = (
            nc.situation_status == "ending_reached"
            or bool(ending_id)
            or nc.is_terminal
        )
        situation_status = nc.situation_status
        canonical_consequences = _cap_consequence_list(list(nc.canonical_consequences or []))
        authoritative_reason = _cap_str(nc.authoritative_reason, _MAX_AUTHORITATIVE_REASON_LEN)
        is_terminal = nc.is_terminal
    else:
        scene_id = result.updated_scene_id or ""
        scene_changed = bool(prior_scene_id and scene_id and scene_id != prior_scene_id)
        ending_reached = bool(result.updated_ending_id)
        ending_id = result.updated_ending_id
        situation_status = ""
        canonical_consequences = []
        authoritative_reason = None
        is_terminal = False

    return ShortTermTurnContext(
        turn_number=result.turn_number,
        scene_id=scene_id,
        detected_triggers=list(result.decision.detected_triggers or []),
        accepted_delta_targets=[d.target_path for d in result.accepted_deltas],
        rejected_delta_targets=[d.target_path for d in result.rejected_deltas],
        guard_outcome=result.guard_outcome.value,
        scene_changed=scene_changed,
        prior_scene_id=prior_scene_id if scene_changed else None,
        ending_reached=ending_reached,
        ending_id=ending_id,
        conflict_pressure=conflict_pressure,
        situation_status=situation_status,
        canonical_consequences=canonical_consequences,
        authoritative_reason=authoritative_reason,
        is_terminal=is_terminal,
        execution_result_full=result.model_dump(mode="json") if hasattr(result, "model_dump") else result,
        ai_decision_log_full=ai_decision_log_full,
    )
