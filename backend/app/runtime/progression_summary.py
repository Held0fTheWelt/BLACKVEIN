"""W2.3.3 — Canonical compressed progression summary for session continuity.

Provides a bounded, deterministic summary of session progression derived from
SessionHistory (W2.3.2). Captures meaningful movement without replaying full
history. Suitable for later context assembly and relationship work.

ProgressionSummary is distinct from:
- raw event logs (no per-turn detail replay)
- short-term turn context (multi-turn aggregated view)
- session history (compressed not exhaustive)
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.runtime.session_history import SessionHistory


class ProgressionSummary(BaseModel):
    """A bounded, semantically meaningful summary of session progression.

    Captures turn span, current state, scene flow, trigger activity, guard
    patterns, and ending state. Derived deterministically from SessionHistory
    through aggregation and compression.

    Attributes:
        first_turn_covered: Oldest turn included in source history.
        last_turn_covered: Newest turn included in source history.
        total_turns_in_source: Number of turns in source SessionHistory.
        current_scene_id: Scene ID of the most recent entry.
        scene_transition_count: Total number of scene changes.
        recent_scene_ids: Last N unique scenes (up to 10, newest last).
        unique_triggers_in_period: All unique triggers that fired (bounded to 50).
        trigger_frequency: Top N triggers by frequency (up to 10).
        guard_outcome_distribution: Count of each outcome type.
        most_recent_guard_outcomes: Last N guard outcomes (up to 5, newest last).
        ending_reached: Whether any ending has been triggered.
        ending_id: The ending ID if one was reached.
        session_phase: Rough phase classification (early/middle/late/ended).
    """

    first_turn_covered: int
    last_turn_covered: int
    total_turns_in_source: int
    current_scene_id: str
    scene_transition_count: int = 0
    recent_scene_ids: list[str] = Field(default_factory=list)
    unique_triggers_in_period: list[str] = Field(default_factory=list)
    trigger_frequency: dict[str, int] = Field(default_factory=dict)
    guard_outcome_distribution: dict[str, int] = Field(default_factory=dict)
    most_recent_guard_outcomes: list[str] = Field(default_factory=list)
    ending_reached: bool = False
    ending_id: Optional[str] = None
    session_phase: str = "early"  # early, middle, late, ended


def derive_progression_summary(history: SessionHistory) -> ProgressionSummary:
    """Derive a compressed progression summary from bounded session history.

    Performs deterministic aggregation and compression:
    - Extracts turn span and scene state from history entries
    - Aggregates unique triggers and their frequencies
    - Counts guard outcomes by type
    - Tracks scene transitions and ending state
    - Classifies session phase based on turn count

    Args:
        history: A SessionHistory to summarize.

    Returns:
        A bounded ProgressionSummary suitable for later context assembly.
    """
    if not history.entries:
        # Empty history: return minimal summary
        return ProgressionSummary(
            first_turn_covered=0,
            last_turn_covered=0,
            total_turns_in_source=0,
            current_scene_id="",
            session_phase="early",
        )

    # Extract turn span
    first_turn = history.entries[0].turn_number
    last_turn = history.entries[-1].turn_number
    total_turns = len(history.entries)
    current_scene = history.entries[-1].scene_id

    # Count scene transitions
    scene_transitions = len(history.get_scene_transitions())

    # Extract recent unique scenes (last 10, maintaining order)
    seen_scenes = set()
    recent_scenes = []
    for entry in reversed(history.entries):
        if entry.scene_id not in seen_scenes:
            recent_scenes.insert(0, entry.scene_id)
            seen_scenes.add(entry.scene_id)
            if len(recent_scenes) >= 10:
                break

    # Aggregate triggers: collect unique and frequency
    trigger_frequency_map: dict[str, int] = {}
    for entry in history.entries:
        for trigger in entry.detected_triggers:
            trigger_frequency_map[trigger] = trigger_frequency_map.get(trigger, 0) + 1

    # Keep top 10 triggers by frequency
    all_unique_triggers = sorted(trigger_frequency_map.keys())[:50]  # Bounded to 50 total
    top_triggers = sorted(
        trigger_frequency_map.items(),
        key=lambda x: (-x[1], x[0]),  # Sort by frequency desc, then alphabetically
    )[:10]
    trigger_frequency_dict = dict(top_triggers)

    # Aggregate guard outcomes
    outcome_distribution: dict[str, int] = {}
    recent_outcomes = []
    for entry in history.entries:
        outcome_distribution[entry.guard_outcome] = outcome_distribution.get(entry.guard_outcome, 0) + 1
        recent_outcomes.append(entry.guard_outcome)

    # Keep only last 5 guard outcomes
    recent_outcomes = recent_outcomes[-5:]

    # Check for ending
    endings = history.get_endings_reached()
    ending_reached = len(endings) > 0
    ending_id = endings[-1].ending_id if endings else None

    # Classify session phase based on turn count
    if ending_reached:
        session_phase = "ended"
    elif total_turns < 15:
        session_phase = "early"
    elif total_turns < 50:
        session_phase = "middle"
    else:
        session_phase = "late"

    return ProgressionSummary(
        first_turn_covered=first_turn,
        last_turn_covered=last_turn,
        total_turns_in_source=total_turns,
        current_scene_id=current_scene,
        scene_transition_count=scene_transitions,
        recent_scene_ids=recent_scenes,
        unique_triggers_in_period=all_unique_triggers,
        trigger_frequency=trigger_frequency_dict,
        guard_outcome_distribution=outcome_distribution,
        most_recent_guard_outcomes=recent_outcomes,
        ending_reached=ending_reached,
        ending_id=ending_id,
        session_phase=session_phase,
    )
