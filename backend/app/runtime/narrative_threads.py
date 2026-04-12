"""Task 1D — bounded persistent narrative consequence threads (derived continuity).

Threads are deterministic runtime state derived from narrative_commit and W2.3 layers.
They are not authoritative truth; narrative_commit remains canonical post-turn outcome.
"""

from __future__ import annotations

from typing import Any, Literal, Union

from app.runtime.context_types import NarrativeThreadState, NarrativeThreadSet
from app.runtime.progression_summary import ProgressionSummary
from app.runtime.relationship_context import RelationshipAxisContext
from app.runtime.runtime_models import NarrativeCommitRecord, SessionState
from app.runtime.session_history import SessionHistory
from app.runtime.narrative_state_transfer_dto import NarrativeCommitEvent
from app.runtime._string_utils import _cap_str

# Re-export ThreadStatus type alias for backwards compatibility
ThreadStatus = Literal["active", "holding", "escalating", "de_escalating", "resolved"]

_STATE_CHANGED_PREFIX = "state_changed:"
_MAX_ACTIVE_THREADS = 8
_MAX_RESOLVED_RECENT = 3
_MAX_EVIDENCE = 6
_MAX_RELATED_PATHS = 8
_MAX_RELATED_CHARACTERS = 6
_MAX_ADAPTER_PATHS = 5
_MAX_ADAPTER_CHARS = 5
_MAX_RESOLUTION_HINT_LEN = 120

_ESCALATION_SEGMENTS = frozenset(
    {
        "tension",
        "hostility",
        "conflict",
        "aggression",
        "rage",
        "enemy",
        "betrayal",
        "accusation",
    }
)
_DE_ESCALATION_SEGMENTS = frozenset(
    {
        "trust",
        "reconciliation",
        "peace",
        "alliance",
        "support",
        "calm",
        "forgiveness",
    }
)


def hydrate_narrative_threads_layer(session: SessionState) -> None:
    """Migration-on-read: fill context_layers from metadata or empty set."""
    if session.context_layers.narrative_threads is not None:
        return
    raw = session.metadata.get("narrative_threads")
    if raw:
        try:
            session.context_layers.narrative_threads = NarrativeThreadSet.model_validate(raw)
        except Exception:
            session.context_layers.narrative_threads = NarrativeThreadSet()
    else:
        session.context_layers.narrative_threads = NarrativeThreadSet()


def sync_narrative_thread_set(session: SessionState, thread_set: NarrativeThreadSet) -> None:
    """Dual-write authoritative snapshot to working layer and persistence metadata."""
    session.context_layers.narrative_threads = thread_set
    session.metadata["narrative_threads"] = thread_set.model_dump(mode="json")


def compact_threads_for_adapter(thread_set: NarrativeThreadSet | None) -> list[dict[str, Any]]:
    """JSON-safe compact dicts for AdapterRequest (no evidence lists)."""
    if thread_set is None:
        return []
    out: list[dict[str, Any]] = []
    for t in thread_set.active[:_MAX_ACTIVE_THREADS]:
        out.append(
            {
                "thread_id": t.thread_id,
                "thread_kind": t.thread_kind,
                "status": t.status,
                "intensity": t.intensity,
                "related_characters": list(t.related_characters[:_MAX_ADAPTER_CHARS]),
                "related_paths": list(t.related_paths[:_MAX_ADAPTER_PATHS]),
                "resolution_hint": _cap_str(t.resolution_hint, _MAX_RESOLUTION_HINT_LEN),
            }
        )
    return out


def update_narrative_threads_from_commit(
    prior: NarrativeThreadSet,
    *,
    narrative_commit: Union[NarrativeCommitRecord, NarrativeCommitEvent],
    _history: SessionHistory,
    progression: ProgressionSummary,
    relationship: RelationshipAxisContext,
) -> NarrativeThreadSet:
    """Derive next thread snapshot from authoritative commit and existing layers.

    DS-007 Task 2: Updated signature to accept both legacy NarrativeCommitRecord
    and new NarrativeCommitEvent DTO for type-safe state transfer.

    Args:
        prior: Current narrative thread set to update.
        narrative_commit: Either NarrativeCommitRecord (legacy) or NarrativeCommitEvent (DS-007).
        _history: Session history context.
        progression: Progression summary metrics.
        relationship: Relationship axis context for character tensions.

    Returns:
        Updated NarrativeThreadSet with derived thread state.
    """
    from app.runtime.narrative_threads_update_from_commit import update_narrative_threads_from_commit_impl

    return update_narrative_threads_from_commit_impl(
        prior,
        narrative_commit=narrative_commit,
        _history=_history,
        progression=progression,
        relationship=relationship,
    )


def apply_thread_markers_to_layers(session: SessionState) -> None:
    """Write compact markers onto short_term_context and last history entry."""
    raw = session.context_layers.narrative_threads
    if not isinstance(raw, NarrativeThreadSet):
        return
    active = raw.active
    ids = [t.thread_id for t in active[:10]]
    dominant = active[0].thread_kind if active else ""
    pressure = max((t.intensity for t in active), default=0)

    st = session.context_layers.short_term_context
    if st is not None and hasattr(st, "model_copy"):
        session.context_layers.short_term_context = st.model_copy(
            update={
                "active_thread_ids": ids,
                "dominant_thread_kind": dominant,
                "thread_pressure_level": pressure,
            }
        )

    hist = session.context_layers.session_history
    if hist is None or not getattr(hist, "entries", None):
        return
    last = hist.last_entry
    if last is None:
        return
    hist.entries[-1] = last.model_copy(
        update={
            "active_thread_ids": ids,
            "dominant_thread_kind": dominant,
            "thread_pressure_level": pressure,
        }
    )


def coerce_narrative_thread_set(value: Any) -> NarrativeThreadSet | None:
    """Best-effort parse for context_layers after JSON round-trip."""
    if value is None:
        return None
    if isinstance(value, NarrativeThreadSet):
        return value
    if isinstance(value, dict):
        try:
            return NarrativeThreadSet.model_validate(value)
        except Exception:
            return None
    return None
