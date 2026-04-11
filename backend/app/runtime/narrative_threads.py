"""Task 1D — bounded persistent narrative consequence threads (derived continuity).

Threads are deterministic runtime state derived from narrative_commit and W2.3 layers.
They are not authoritative truth; narrative_commit remains canonical post-turn outcome.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.runtime.progression_summary import ProgressionSummary
from app.runtime.relationship_context import RelationshipAxisContext
from app.runtime.runtime_models import NarrativeCommitRecord, SessionState
from app.runtime.session_history import SessionHistory

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

ThreadStatus = Literal["active", "holding", "escalating", "de_escalating", "resolved"]


class NarrativeThreadState(BaseModel):
    """Single bounded narrative consequence thread (derived, not authoritative)."""

    thread_id: str
    thread_kind: str
    status: ThreadStatus
    scene_anchor: str | None = None
    related_paths: list[str] = Field(default_factory=list)
    related_characters: list[str] = Field(default_factory=list)
    evidence_consequences: list[str] = Field(default_factory=list)
    intensity: int = Field(default=0, ge=0, le=5)
    persistence_turns: int = Field(default=0, ge=0)
    last_updated_turn: int = 0
    resolution_hint: str | None = None


class NarrativeThreadSet(BaseModel):
    """Bounded set of active threads plus a small resolved-recent window."""

    active: list[NarrativeThreadState] = Field(default_factory=list)
    resolved_recent: list[NarrativeThreadState] = Field(default_factory=list)


def _cap_str(s: str | None, max_len: int) -> str | None:
    if s is None:
        return None
    t = str(s).strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


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
    narrative_commit: NarrativeCommitRecord,
    _history: SessionHistory,
    progression: ProgressionSummary,
    relationship: RelationshipAxisContext,
) -> NarrativeThreadSet:
    """Derive next thread snapshot from authoritative commit and existing layers."""
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
