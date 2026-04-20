"""Task 1D — bounded persistent narrative consequence threads (derived continuity).

Threads are deterministic runtime state derived from narrative_commit and W2.3 layers.
They are not authoritative truth; narrative_commit remains canonical post-turn outcome.
"""

from __future__ import annotations

import hashlib
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


def _paths_from_consequences(consequences: list[str]) -> list[str]:
    out: list[str] = []
    for c in consequences:
        if not c.startswith(_STATE_CHANGED_PREFIX):
            continue
        p = c[len(_STATE_CHANGED_PREFIX) :].strip()
        if p:
            out.append(p)
    return out


def _character_ids_from_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for path in paths:
        lower = path.lower()
        if not lower.startswith("characters."):
            continue
        rest = path[len("characters.") :]
        if not rest:
            continue
        cid = rest.split(".", 1)[0].strip().lower()
        if len(cid) > 1 and cid not in seen:
            seen.add(cid)
            ordered.append(cid)
    return ordered


def _path_signal(path: str) -> str | None:
    lower = path.lower()
    for seg in _ESCALATION_SEGMENTS:
        if seg in lower:
            return "escalation"
    for seg in _DE_ESCALATION_SEGMENTS:
        if seg in lower:
            return "de_escalation"
    return None


def _stable_anchor_id(kind: str, *parts: str) -> str:
    payload = "|".join(sorted(parts))
    h = hashlib.sha256(f"{kind}:{payload}".encode()).hexdigest()[:12]
    return f"{kind}:{h}"


def _interpersonal_thread_id(chars: list[str]) -> str:
    if len(chars) >= 2:
        a, b = sorted(chars)[:2]
        return _stable_anchor_id("interpersonal_tension", a, b)
    if len(chars) == 1:
        return _stable_anchor_id("interpersonal_pressure", chars[0])
    return _stable_anchor_id("interpersonal_pressure", "none")


def _avoidance_thread_id(scene_id: str) -> str:
    return _stable_anchor_id("avoidance_deadlock", scene_id or "unknown")


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


def _merge_evidence(existing: list[str], new_tokens: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for x in list(existing) + new_tokens:
        if x not in seen:
            seen.add(x)
            merged.append(x)
        if len(merged) >= _MAX_EVIDENCE:
            break
    return merged


def _evict_lowest_priority(active: list[NarrativeThreadState]) -> list[NarrativeThreadState]:
    if len(active) <= _MAX_ACTIVE_THREADS:
        return active
    # Remove lowest (intensity, persistence_turns, thread_id); keep highest-pressure threads.
    ranked = sorted(active, key=lambda t: (t.intensity, t.persistence_turns, t.thread_id))
    drop = len(active) - _MAX_ACTIVE_THREADS
    return ranked[drop:]


def update_narrative_threads_from_commit(
    prior: NarrativeThreadSet,
    *,
    narrative_commit: NarrativeCommitRecord,
    _history: SessionHistory,
    progression: ProgressionSummary,
    relationship: RelationshipAxisContext,
) -> NarrativeThreadSet:
    """Derive next thread snapshot from authoritative commit and existing layers."""
    cons = list(narrative_commit.canonical_consequences or [])
    paths = _paths_from_consequences(cons)
    chars = _character_ids_from_paths(paths)
    turn_no = narrative_commit.turn_number
    scene = narrative_commit.committed_scene_id or ""

    # Terminal: resolve all active, trim resolved_recent
    if narrative_commit.is_terminal or narrative_commit.situation_status == "ending_reached":
        resolved_batch = [
            t.model_copy(
                update={
                    "status": "resolved",
                    "resolution_hint": _cap_str("narrative_ending", _MAX_RESOLUTION_HINT_LEN),
                    "last_updated_turn": turn_no,
                }
            )
            for t in prior.active
        ]
        merged_resolved = resolved_batch + prior.resolved_recent
        return NarrativeThreadSet(
            active=[],
            resolved_recent=merged_resolved[:_MAX_RESOLVED_RECENT],
        )

    active = [t.model_copy(deep=True) for t in prior.active]
    by_id: dict[str, NarrativeThreadState] = {t.thread_id: t for t in active}

    path_signals = [(p, _path_signal(p)) for p in paths]
    has_escalation_path = any(s == "escalation" for _, s in path_signals)
    has_de_path = any(s == "de_escalation" for _, s in path_signals)

    evidence_tokens = [c for c in cons if c.startswith(_STATE_CHANGED_PREFIX)][:4]

    def upsert_thread(
        thread_id: str,
        kind: str,
        *,
        default_status: ThreadStatus = "active",
        paths_for_thread: list[str],
        chars_for_thread: list[str],
    ) -> None:
        rel_paths = sorted(set(paths_for_thread))[:_MAX_RELATED_PATHS]
        rel_chars = sorted(set(chars_for_thread))[:_MAX_RELATED_CHARACTERS]
        if thread_id in by_id:
            t = by_id[thread_id]
            t.last_updated_turn = turn_no
            t.persistence_turns = t.persistence_turns + 1
            t.related_paths = sorted(set(t.related_paths) | set(rel_paths))[:_MAX_RELATED_PATHS]
            t.related_characters = sorted(set(t.related_characters) | set(rel_chars))[
                :_MAX_RELATED_CHARACTERS
            ]
            t.evidence_consequences = _merge_evidence(t.evidence_consequences, evidence_tokens)
            t.scene_anchor = scene or t.scene_anchor
            if has_escalation_path:
                t.intensity = min(5, t.intensity + 1)
                t.status = "escalating"
            elif has_de_path:
                t.intensity = max(0, t.intensity - 1)
                t.status = "de_escalating" if t.intensity > 0 else "resolved"
            else:
                if t.status == "escalating" and progression.stalled_turn_count == 0:
                    t.status = "active"
                elif t.status == "de_escalating" and t.intensity > 0:
                    t.status = "active"
        else:
            intensity = 1 if has_escalation_path else (0 if has_de_path else 1)
            status: ThreadStatus
            if has_escalation_path:
                status = "escalating"
            elif has_de_path:
                status = "de_escalating" if intensity > 0 else "resolved"
            else:
                status = default_status
            by_id[thread_id] = NarrativeThreadState(
                thread_id=thread_id,
                thread_kind=kind,
                status=status,
                scene_anchor=scene,
                related_paths=rel_paths,
                related_characters=rel_chars,
                evidence_consequences=_merge_evidence([], evidence_tokens),
                intensity=min(5, max(0, intensity)),
                persistence_turns=1,
                last_updated_turn=turn_no,
                resolution_hint=None,
            )

    # Avoidance / deadlock signal from progression (read-only use of progression)
    if progression.progression_momentum == "stalled" and progression.stalled_turn_count >= 2:
        if narrative_commit.situation_status == "continue":
            aid = _avoidance_thread_id(scene)
            upsert_thread(
                aid,
                "avoidance_deadlock",
                default_status="holding",
                paths_for_thread=paths,
                chars_for_thread=chars,
            )
            by_id[aid].status = "holding"

    # Interpersonal cluster from character-bearing state paths
    if chars:
        tid = _interpersonal_thread_id(chars)
        upsert_thread(
            tid,
            "interpersonal_tension" if len(chars) >= 2 else "interpersonal_pressure",
            default_status="active",
            paths_for_thread=paths,
            chars_for_thread=chars,
        )

    # Relationship-derived reinforcement (read-only): escalation markers strengthen existing interpersonal threads
    if relationship.has_escalation_markers and chars:
        tid = _interpersonal_thread_id(chars)
        if tid in by_id:
            t = by_id[tid]
            t.intensity = min(5, t.intensity + 1)
            if t.status in ("active", "holding"):
                t.status = "escalating"

    # Same-scene repeated meaningful state without stall → keep tension thread warm
    if (
        narrative_commit.situation_status == "continue"
        and progression.same_scene_progression_count >= 2
        and paths
        and chars
    ):
        tid = _interpersonal_thread_id(chars)
        if tid not in by_id:
            upsert_thread(
                tid,
                "interpersonal_tension" if len(chars) >= 2 else "interpersonal_pressure",
                default_status="active",
                paths_for_thread=paths,
                chars_for_thread=chars,
            )

    # Split resolved vs active (upsert may mark interpersonal threads resolved)
    new_resolved: list[NarrativeThreadState] = []
    active_list: list[NarrativeThreadState] = []
    for t in by_id.values():
        if t.status == "resolved":
            hint = t.resolution_hint or _cap_str("de_escalation_signal", _MAX_RESOLUTION_HINT_LEN)
            new_resolved.append(
                t.model_copy(
                    update={
                        "resolution_hint": _cap_str(hint, _MAX_RESOLUTION_HINT_LEN),
                        "last_updated_turn": turn_no,
                    }
                )
            )
        else:
            active_list.append(t)

    active_list = _evict_lowest_priority(active_list)
    active_list = sorted(active_list, key=lambda x: (-x.intensity, -x.persistence_turns, x.thread_id))

    merged_rr = new_resolved + prior.resolved_recent
    merged_rr = merged_rr[:_MAX_RESOLVED_RECENT]

    return NarrativeThreadSet(active=active_list, resolved_recent=merged_rr)


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
