"""Commit-Pfad: Narrative-Threads aus NarrativeCommit ableiten (DS-049).

DS-007 Task 2: Updated to accept NarrativeCommitEvent DTO for type-safe
state transfer between turn_executor and narrative layers.

DS-007 Task 4: Added type hints referencing NarrativeCommitEvent and ThreadUpdateResult.
Documented narrative protocol (NarrativeCommitEvent → ThreadUpdateResult contract).

DS-003: Parsing, terminal resolution, and non-terminal mutation live in companion modules
(``narrative_threads_update_from_commit_phases`` + ``narrative_threads_commit_path_utils``).
"""

from __future__ import annotations

from typing import Union

from app.runtime.progression_summary import ProgressionSummary
from app.runtime.relationship_context import RelationshipAxisContext
from app.runtime.runtime_models import NarrativeCommitRecord
from app.runtime.session_history import SessionHistory
from app.runtime.narrative_threads import NarrativeThreadSet
from app.runtime.narrative_state_transfer_dto import NarrativeCommitEvent
from app.runtime.narrative_threads_update_from_commit_phases import (
    apply_non_terminal_thread_updates,
    build_narrative_commit_thread_drive,
    maybe_thread_set_for_terminal_ending,
)


def update_narrative_threads_from_commit_impl(
    prior: NarrativeThreadSet,
    *,
    narrative_commit: Union[NarrativeCommitRecord, NarrativeCommitEvent],
    _history: SessionHistory,
    progression: ProgressionSummary,
    relationship: RelationshipAxisContext,
) -> NarrativeThreadSet:
    """Derive next thread snapshot from authoritative commit and existing layers.

    **Narrative Protocol (DS-007 Task 4)**

    **Input Contract (NarrativeCommitEvent):**
    - commit_id: Unique identifier for this commit
    - turn_id: Turn number triggering the update
    - narrative_id: Session/narrative identifier
    - user_id: Player identifier
    - commit_payload: Dict with keys:
      * canonical_consequences: list[str] describing state changes
      * turn_number: int, current turn
      * committed_scene_id: str, scene after commit
      * is_terminal: bool, whether session ending
      * situation_status: str, one of ["continue", "transitioned", "ending_reached"]
    - timestamp: datetime when commit occurred
    - metadata: Optional dict for extensibility

    **Output Contract (NarrativeThreadSet):**
    - active: list[NarrativeThreadState], currently active narrative threads
    - resolved_recent: list[NarrativeThreadState], recently resolved threads (history)

    Each thread captures:
    - thread_id: Stable identifier (hash-based from context)
    - thread_kind: Type ("interpersonal_tension", "interpersonal_pressure", "avoidance_deadlock")
    - status: One of ["active", "escalating", "de_escalating", "holding", "resolved"]
    - intensity: 0-5 scale of narrative pressure
    - evidence_consequences: Supporting state change tokens
    - related_characters: Character IDs involved in this thread
    - related_paths: State paths impacted by this thread

    **Semantics:**
    1. Extracts canonical_consequences from commit payload
    2. Parses character IDs and state paths from consequences
    3. Detects escalation/de-escalation signals in paths
    4. Creates/updates threads for detected interpersonal dynamics
    5. Manages thread lifecycle (active → resolved) based on signals
    6. Evicts lowest-priority threads if max active threads exceeded
    7. Returns updated thread set for downstream narrative systems

    Args:
        prior: Current narrative thread set to update.
        narrative_commit: Either NarrativeCommitRecord (legacy) or NarrativeCommitEvent (DS-007).
        _history: Session history context.
        progression: Progression summary metrics.
        relationship: Relationship axis context for character tensions.

    Returns:
        Updated NarrativeThreadSet with derived thread state (active and resolved).
    """
    drive = build_narrative_commit_thread_drive(narrative_commit)
    terminal = maybe_thread_set_for_terminal_ending(prior, drive)
    if terminal is not None:
        return terminal
    return apply_non_terminal_thread_updates(prior, drive, progression, relationship)
