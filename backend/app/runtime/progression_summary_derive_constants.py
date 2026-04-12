"""Named bounds for progression summary derivation, momentum, and Task 1C caps (DS-003 / C5)."""

from __future__ import annotations

from typing import Final

# --- Task 1C: situation tail, consequence dedupe / frequency caps ---
RECENT_SITUATION_STATUSES_CAP: Final[int] = 8
RECENT_CANONICAL_CONSEQUENCES_CAP: Final[int] = 15
CONSEQUENCE_FREQUENCY_MAX_KEYS: Final[int] = 25

# --- derive_progression_summary: list / map caps ---
RECENT_SCENE_IDS_CAP: Final[int] = 10
UNIQUE_TRIGGERS_LIST_CAP: Final[int] = 50
TOP_TRIGGER_FREQUENCY_CAP: Final[int] = 10
MOST_RECENT_GUARD_OUTCOMES_TAIL: Final[int] = 5

# --- session_phase thresholds (turn counts, exclusive upper bounds) ---
SESSION_PHASE_EARLY_BELOW_TURNS: Final[int] = 15
SESSION_PHASE_MIDDLE_BELOW_TURNS: Final[int] = 50

# --- _progression_momentum thresholds ---
STALLED_TURNS_FOR_STALLED_LABEL: Final[int] = 2
SAME_SCENE_RESOLVING_MIN_PROGRESSION: Final[int] = 3
SAME_SCENE_DEVELOPING_MIN_PROGRESSION: Final[int] = 2
