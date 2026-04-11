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

from app.runtime.session_history import HistoryEntry, SessionHistory

# Task 1C: caps and deterministic ordering (binding precision layer §2).
_RECENT_SITUATION_STATUSES_CAP = 8
_RECENT_CANONICAL_CONSEQUENCES_CAP = 15
_CONSEQUENCE_FREQUENCY_MAX_KEYS = 25

_STATE_CHANGED_PREFIX = "state_changed:"


def _has_meaningful_state_progression(consequences: list[str]) -> bool:
    """True if any committed consequence reflects an applied state path change."""
    for c in consequences:
        if c.startswith(_STATE_CHANGED_PREFIX) and len(c) > len(_STATE_CHANGED_PREFIX):
            return True
    return False


def _narrative_signature_for_stall(consequences: list[str]) -> frozenset[str]:
    """Bounded consequence tokens used to compare consecutive same-scene turns."""
    out: list[str] = []
    for c in consequences:
        if c.startswith(
            (_STATE_CHANGED_PREFIX, "ending_reached:", "scene_transition:", "scene_continue:")
        ):
            out.append(c)
    return frozenset(out)


def _recent_canonical_consequences_ordered(entries: list[HistoryEntry]) -> list[str]:
    """Dedupe with last-seen-wins order: scan newest-first, emit unique tokens newest-first, cap.

    Chronological flatten is oldest→newest per entry order; uniqueness keeps the most
    recent occurrence's intent by scanning reversed(flat).
    """
    flat: list[str] = []
    for e in entries:
        for c in e.canonical_consequences:
            flat.append(c)
    seen: set[str] = set()
    newest_first_unique: list[str] = []
    for c in reversed(flat):
        if c not in seen:
            seen.add(c)
            newest_first_unique.append(c)
    return newest_first_unique[:_RECENT_CANONICAL_CONSEQUENCES_CAP]


def _consequence_frequency_bounded(entries: list[HistoryEntry]) -> dict[str, int]:
    """Count all consequence strings; keep top keys by (-count, key) for stable dict order."""
    counts: dict[str, int] = {}
    for e in entries:
        for c in e.canonical_consequences:
            counts[c] = counts.get(c, 0) + 1
    ordered = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    return dict(ordered[:_CONSEQUENCE_FREQUENCY_MAX_KEYS])


def _same_scene_progression_count(entries: list[HistoryEntry], current_scene: str) -> int:
    """Count meaningful progression turns only in the trailing contiguous current-scene phase.

    Walks newest-to-oldest and stops at the first scene_id mismatch so revisiting the same
    scene_id later does not accumulate counts from an earlier visit.
    """
    n = 0
    for e in reversed(entries):
        if e.scene_id != current_scene:
            break
        if _has_meaningful_state_progression(e.canonical_consequences):
            n += 1
    return n


def _stalled_turn_count(entries: list[HistoryEntry]) -> int:
    """Count trailing consecutive same-scene pairs with identical narrative signatures."""
    if len(entries) < 2:
        return 0
    current_scene = entries[-1].scene_id
    stall = 0
    for i in range(len(entries) - 1, 0, -1):
        cur, prev = entries[i], entries[i - 1]
        if cur.scene_id != current_scene or prev.scene_id != current_scene:
            break
        if _narrative_signature_for_stall(cur.canonical_consequences) == _narrative_signature_for_stall(
            prev.canonical_consequences
        ):
            stall += 1
        else:
            break
    return stall


def _recent_situation_statuses(entries: list[HistoryEntry]) -> list[str]:
    tail = entries[-_RECENT_SITUATION_STATUSES_CAP:]
    return [e.situation_status for e in tail if e.situation_status]


def _progression_momentum(
    *,
    ending_reached: bool,
    last: HistoryEntry,
    same_scene_progression_count: int,
    stalled_turn_count: int,
) -> str:
    """Deterministic coarse momentum label (Task 1C)."""
    if ending_reached or last.is_terminal:
        return "ended"
    if last.scene_changed or last.situation_status == "transitioned":
        return "relocating"
    if stalled_turn_count >= 2:
        return "stalled"
    if same_scene_progression_count >= 3 and stalled_turn_count == 0:
        return "resolving"
    if same_scene_progression_count >= 2:
        return "developing"
    return "holding"


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
        recent_situation_statuses: Recent situation_status strings (Task 1C).
        same_scene_progression_count: Turns with state_changed commits in the trailing contiguous
            stretch of current_scene_id only (Task 1C-R); not all-time for that scene id.
        consequence_frequency: Bounded frequency map over canonical_consequences (Task 1C).
        recent_canonical_consequences: Recent unique consequences, newest-first (Task 1C).
        progression_momentum: Coarse narrative momentum label (Task 1C).
        stalled_turn_count: Trailing stalled same-scene pairs (Task 1C).
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

    recent_situation_statuses: list[str] = Field(default_factory=list)
    same_scene_progression_count: int = 0
    consequence_frequency: dict[str, int] = Field(default_factory=dict)
    recent_canonical_consequences: list[str] = Field(default_factory=list)
    progression_momentum: str = "holding"
    stalled_turn_count: int = 0


def derive_progression_summary(history: SessionHistory) -> ProgressionSummary:
    """Derive a compressed progression summary from bounded session history.

    Performs deterministic aggregation and compression:
    - Extracts turn span and scene state from history entries
    - Aggregates unique triggers and their frequencies
    - Counts guard outcomes by type
    - Tracks scene transitions and ending state
    - Classifies session phase based on turn count
    - Task 1C: narrative continuity signals from canonical_consequences / situation_status
    - Task 1C-R: same_scene_progression_count uses trailing contiguous current scene only

    Args:
        history: A SessionHistory to summarize.

    Returns:
        A bounded ProgressionSummary suitable for later context assembly.
    """
    if not history.entries:
        return ProgressionSummary(
            first_turn_covered=0,
            last_turn_covered=0,
            total_turns_in_source=0,
            current_scene_id="",
            session_phase="early",
            recent_situation_statuses=[],
            same_scene_progression_count=0,
            consequence_frequency={},
            recent_canonical_consequences=[],
            progression_momentum="holding",
            stalled_turn_count=0,
        )

    entries = history.entries
    first_turn = entries[0].turn_number
    last_turn = entries[-1].turn_number
    total_turns = len(entries)
    current_scene = entries[-1].scene_id

    scene_transitions = len(history.get_scene_transitions())

    seen_scenes = set()
    recent_scenes = []
    for entry in reversed(entries):
        if entry.scene_id not in seen_scenes:
            recent_scenes.insert(0, entry.scene_id)
            seen_scenes.add(entry.scene_id)
            if len(recent_scenes) >= 10:
                break

    trigger_frequency_map: dict[str, int] = {}
    for entry in entries:
        for trigger in entry.detected_triggers:
            trigger_frequency_map[trigger] = trigger_frequency_map.get(trigger, 0) + 1

    all_unique_triggers = sorted(trigger_frequency_map.keys())[:50]
    top_triggers = sorted(
        trigger_frequency_map.items(),
        key=lambda x: (-x[1], x[0]),
    )[:10]
    trigger_frequency_dict = dict(top_triggers)

    outcome_distribution: dict[str, int] = {}
    recent_outcomes = []
    for entry in entries:
        outcome_distribution[entry.guard_outcome] = outcome_distribution.get(entry.guard_outcome, 0) + 1
        recent_outcomes.append(entry.guard_outcome)

    recent_outcomes = recent_outcomes[-5:]

    endings = history.get_endings_reached()
    ending_reached = len(endings) > 0
    ending_id = endings[-1].ending_id if endings else None

    if ending_reached:
        session_phase = "ended"
    elif total_turns < 15:
        session_phase = "early"
    elif total_turns < 50:
        session_phase = "middle"
    else:
        session_phase = "late"

    same_scene_prog = _same_scene_progression_count(entries, current_scene)
    stalled = _stalled_turn_count(entries)
    recent_situations = _recent_situation_statuses(entries)
    recent_consequences = _recent_canonical_consequences_ordered(entries)
    cons_freq = _consequence_frequency_bounded(entries)
    momentum = _progression_momentum(
        ending_reached=ending_reached,
        last=entries[-1],
        same_scene_progression_count=same_scene_prog,
        stalled_turn_count=stalled,
    )

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
        recent_situation_statuses=recent_situations,
        same_scene_progression_count=same_scene_prog,
        consequence_frequency=cons_freq,
        recent_canonical_consequences=recent_consequences,
        progression_momentum=momentum,
        stalled_turn_count=stalled,
    )
