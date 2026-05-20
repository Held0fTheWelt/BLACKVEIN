"""W3.5.1 History Panel Presenter.

Transforms session history (SessionHistory, ProgressionSummary) into a bounded,
presenter-ready output for UI rendering.

Presenter Function:
    present_history_panel(session_state: SessionState) -> HistoryPanelOutput

Output Model:
    HistoryPanelOutput
    - history_summary: Compressed session progression (from ProgressionSummary)
    - recent_entries: Last 20 turn records (from SessionHistory)
    - entry_count: Total entries in SessionHistory

Determinism & Graceful Degradation:
    - Pure function: no side effects, no randomness
    - Deterministic filtering/sorting by turn_number and created_at
    - Graceful: returns valid output with empty entries if SessionHistory missing
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.runtime.runtime_models import SessionState


class HistorySummary(BaseModel):
    """Compressed session progression summary derived from ProgressionSummary."""

    session_phase: str  # "early", "middle", "late", "ended"
    total_turns_covered: int
    first_turn_number: int
    last_turn_number: int
    scene_transition_count: int
    recent_scene_ids: list[str] = Field(default_factory=list)  # last 3-5 scenes
    unique_triggers_detected: list[str] = Field(default_factory=list)  # up to 10
    guard_outcome_summary: dict[str, int] = Field(
        default_factory=dict
    )  # counts by outcome
    ending_reached: bool
    ending_id: Optional[str] = None


class RecentHistoryEntry(BaseModel):
    """Single bounded turn history entry derived from SessionHistory.HistoryEntry."""

    turn_number: int
    scene_id: str
    guard_outcome: str  # ACCEPTED, PARTIALLY_ACCEPTED, REJECTED, STRUCTURALLY_INVALID
    detected_triggers: list[str] = Field(default_factory=list)
    scene_changed: bool
    prior_scene_id: Optional[str] = None
    ending_reached: bool
    ending_id: Optional[str] = None
    created_at: datetime


class HistoryPanelOutput(BaseModel):
    """Complete history panel presenter output, ready for template rendering."""

    history_summary: HistorySummary
    recent_entries: list[
        RecentHistoryEntry
    ]  # last 20, chronological (oldest first)
    entry_count: int  # total entries in source SessionHistory


def present_history_panel(session_state: SessionState) -> HistoryPanelOutput:
    """
    Derive bounded history view from session's SessionHistory and ProgressionSummary.

    Args:
        session_state: Current SessionState with context_layers populated

    Returns:
        HistoryPanelOutput with summary + recent 20 entries (chronological, oldest first)

    Determinism:
        - No randomness, no side effects
        - Filtering/sorting deterministic (by turn_number, by created_at)
        - Graceful degradation: returns valid output with empty entries if SessionHistory missing
    """
    # Get history and progression summary from context layers
    history = session_state.context_layers.session_history
    progression = session_state.context_layers.progression_summary

    # If both missing, return minimal valid output
    if not history and not progression:
        return HistoryPanelOutput(
            history_summary=HistorySummary(
                session_phase="early",
                total_turns_covered=0,
                first_turn_number=0,
                last_turn_number=0,
                scene_transition_count=0,
                ending_reached=False,
            ),
            recent_entries=[],
            entry_count=0,
        )

    # Derive or use progression summary
    if progression:
        summary = HistorySummary(
            session_phase=progression.session_phase,
            total_turns_covered=progression.total_turns_in_source,
            first_turn_number=progression.first_turn_covered,
            last_turn_number=progression.last_turn_covered,
            scene_transition_count=progression.scene_transition_count,
            recent_scene_ids=progression.recent_scene_ids[
                -5:
            ],  # last 5 scenes
            unique_triggers_detected=list(
                progression.unique_triggers_in_period
            )[
                :10
            ],  # up to 10
            guard_outcome_summary=dict(progression.guard_outcome_distribution),
            ending_reached=progression.ending_reached,
            ending_id=progression.ending_id,
        )
    else:
        # Fallback: minimal summary if progression not available
        summary = HistorySummary(
            session_phase="early",
            total_turns_covered=history.size if history else 0,
            first_turn_number=(
                history.entries[0].turn_number if history and history.entries else 0
            ),
            last_turn_number=(
                history.entries[-1].turn_number if history and history.entries else 0
            ),
            scene_transition_count=0,
            ending_reached=False,
        )

    # Extract recent entries (last 20, chronological oldest first)
    recent_entries = []
    if history and history.entries:
        # Get last 20 entries, keep chronological order (oldest first)
        entries_to_use = (
            history.entries[-20:] if len(history.entries) > 20 else history.entries
        )
        recent_entries = [
            RecentHistoryEntry(
                turn_number=entry.turn_number,
                scene_id=entry.scene_id,
                guard_outcome=entry.guard_outcome,
                detected_triggers=entry.detected_triggers or [],
                scene_changed=entry.scene_changed,
                prior_scene_id=entry.prior_scene_id,
                ending_reached=entry.ending_reached,
                ending_id=entry.ending_id,
                created_at=entry.created_at,
            )
            for entry in entries_to_use
        ]

    return HistoryPanelOutput(
        history_summary=summary,
        recent_entries=recent_entries,
        entry_count=history.size if history else 0,
    )
