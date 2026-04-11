"""Bounded persistent narrative consequence threads derived from Task B narrative commits.

Thread continuity is session-local and deterministic. It is not diagnostics and must not
replace narrative_commit as authoritative per-turn truth.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.story_runtime.commit_models import StoryNarrativeCommitRecord

# --- Capacity caps (session thread set) ---
MAX_ACTIVE_THREADS = 8
MAX_RESOLVED_RECENT = 6
MAX_EVIDENCE_TOKENS_PER_THREAD = 8
MAX_RELATED_SCENES = 6
MAX_RELATED_ENTITIES = 6
MAX_RESOLUTION_HINT_LEN = 96
MAX_THREAD_KIND_LEN = 48
MAX_SCENE_ANCHOR_LEN = 64

# --- Graph export (tight; no full thread objects or evidence in graph state) ---
GRAPH_EXPORT_MAX_ACTIVE = 4
THREAD_PRESSURE_SUMMARY_MAX = 128
GRAPH_RELATED_ENTITIES_MAX = 4
GRAPH_RESOLUTION_HINT_MAX = 48

# --- History window for pattern detection ---
NARRATIVE_COMMIT_HISTORY_TAIL = 10

# --- Trace bounds (diagnostics only; single latest trace stored on session) ---
TRACE_LIST_MAX_RULES = 16
TRACE_LIST_MAX_IDS = 8
TRACE_LIST_MAX_UPDATED = 16
TRACE_RULE_TOKEN_MAX = 64
TRACE_SUMMARY_MAX = 128

ThreadStatus = Literal["active", "holding", "escalating", "de_escalating", "resolved"]


def _short(s: str, max_len: int) -> str:
    t = s.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _token_key(kind: str, anchor: str, seed: str) -> str:
    base = f"{kind}|{anchor}|{seed}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def _parse_commit(commit: StoryNarrativeCommitRecord | dict[str, Any]) -> dict[str, Any]:
    if isinstance(commit, StoryNarrativeCommitRecord):
        d = commit.model_dump(mode="json")
    else:
        d = dict(commit)
    return d


def _commit_scene_id(d: dict[str, Any]) -> str:
    sid = d.get("committed_scene_id")
    return str(sid).strip() if isinstance(sid, str) else ""


def _has_block(d: dict[str, Any]) -> bool:
    if d.get("situation_status") == "blocked":
        return True
    cons = d.get("committed_consequences")
    if not isinstance(cons, list):
        return False
    for x in cons:
        s = str(x)
        if "proposal_blocked:" in s or s.startswith("proposal_blocked:"):
            return True
    return False


def _has_ambiguity(d: dict[str, Any]) -> bool:
    op = d.get("open_pressures")
    if not isinstance(op, list) or not op:
        return False
    return any(str(x).strip() for x in op)


def _is_terminal_commit(d: dict[str, Any]) -> bool:
    return bool(d.get("is_terminal")) or d.get("situation_status") == "terminal"


def _first_evidence_token(d: dict[str, Any]) -> str:
    cons = d.get("committed_consequences")
    if isinstance(cons, list) and cons:
        return _short(str(cons[0]), 80)
    op = d.get("open_pressures")
    if isinstance(op, list) and op:
        return _short(str(op[0]), 80)
    return "commit_signal"


def _tail_blocked_or_ambiguity_count(tail: list[dict[str, Any]], scene: str) -> int:
    n = 0
    for row in tail:
        nc = row.get("narrative_commit") if isinstance(row, dict) else None
        if not isinstance(nc, dict):
            continue
        if _commit_scene_id(nc) != scene:
            continue
        if _has_block(nc) or _has_ambiguity(nc):
            n += 1
    return n


class StoryNarrativeThread(BaseModel):
    model_config = {"extra": "forbid"}

    thread_id: str = Field(..., min_length=8, max_length=32)
    thread_kind: str = Field(..., max_length=MAX_THREAD_KIND_LEN)
    status: ThreadStatus
    scene_anchor: str | None = Field(default=None, max_length=MAX_SCENE_ANCHOR_LEN)
    intensity: int = Field(default=0, ge=0, le=10)
    persistence_turns: int = Field(default=0, ge=0, le=10_000)
    related_scenes: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    evidence_tokens: list[str] = Field(default_factory=list)
    last_updated_turn: int = Field(default=0, ge=0)
    resolution_hint: str | None = Field(default=None, max_length=MAX_RESOLUTION_HINT_LEN)

    @field_validator("related_scenes", mode="after")
    @classmethod
    def cap_scenes(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for x in v[:MAX_RELATED_SCENES]:
            s = _short(str(x), MAX_SCENE_ANCHOR_LEN)
            if s and s not in out:
                out.append(s)
        return out

    @field_validator("related_entities", mode="after")
    @classmethod
    def cap_entities(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for x in v[:MAX_RELATED_ENTITIES]:
            s = _short(re.sub(r"\s+", "_", str(x)), 48)
            if s and s not in out:
                out.append(s)
        return out

    @field_validator("evidence_tokens", mode="after")
    @classmethod
    def cap_evidence(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for x in v[:MAX_EVIDENCE_TOKENS_PER_THREAD]:
            t = _short(str(x), 96)
            if t and t not in out:
                out.append(t)
        return out


class StoryNarrativeThreadSet(BaseModel):
    model_config = {"extra": "forbid"}

    active: list[StoryNarrativeThread] = Field(default_factory=list)
    resolved_recent: list[StoryNarrativeThread] = Field(default_factory=list)

    @field_validator("active", mode="after")
    @classmethod
    def cap_active(cls, v: list[StoryNarrativeThread]) -> list[StoryNarrativeThread]:
        return v[:MAX_ACTIVE_THREADS]

    @field_validator("resolved_recent", mode="after")
    @classmethod
    def cap_resolved(cls, v: list[StoryNarrativeThread]) -> list[StoryNarrativeThread]:
        return v[:MAX_RESOLVED_RECENT]


class ThreadUpdateTrace(BaseModel):
    """Bounded diagnostic trace for the latest thread update only (not authoritative)."""

    model_config = {"extra": "forbid"}

    rules_fired: list[str] = Field(default_factory=list)
    evicted_thread_ids: list[str] = Field(default_factory=list)
    created_thread_ids: list[str] = Field(default_factory=list)
    updated_thread_ids: list[str] = Field(default_factory=list)
    summary: str = Field(default="", max_length=TRACE_SUMMARY_MAX)

    @field_validator("rules_fired", mode="after")
    @classmethod
    def cap_rules(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for x in v[:TRACE_LIST_MAX_RULES]:
            out.append(_short(str(x), TRACE_RULE_TOKEN_MAX))
        return out

    @field_validator("evicted_thread_ids", "created_thread_ids", mode="after")
    @classmethod
    def cap_ids(cls, v: list[str]) -> list[str]:
        return [_short(str(x), 32) for x in v[:TRACE_LIST_MAX_IDS]]

    @field_validator("updated_thread_ids", mode="after")
    @classmethod
    def cap_updated(cls, v: list[str]) -> list[str]:
        return [_short(str(x), 32) for x in v[:TRACE_LIST_MAX_UPDATED]]


def _append_evidence(th: StoryNarrativeThread, token: str) -> StoryNarrativeThread:
    ev = list(th.evidence_tokens)
    t = _short(token, 96)
    if t and t not in ev:
        ev.append(t)
    return th.model_copy(update={"evidence_tokens": ev[:MAX_EVIDENCE_TOKENS_PER_THREAD]})


def _resolve_thread(th: StoryNarrativeThread, *, turn: int, hint: str) -> StoryNarrativeThread:
    return th.model_copy(
        update={
            "status": "resolved",
            "intensity": 0,
            "last_updated_turn": turn,
            "resolution_hint": _short(hint, MAX_RESOLUTION_HINT_LEN),
        }
    )


def _evict_deterministic(
    active: list[StoryNarrativeThread], trace: ThreadUpdateTrace
) -> tuple[list[StoryNarrativeThread], ThreadUpdateTrace]:
    """When over capacity, evict lowest persistence, then lowest intensity, then thread_id."""

    if len(active) <= MAX_ACTIVE_THREADS:
        return active, trace
    ranked = sorted(active, key=lambda t: (t.persistence_turns, t.intensity, t.thread_id))
    out = list(active)
    evicted: list[str] = []
    while len(out) > MAX_ACTIVE_THREADS:
        victim = ranked.pop(0)
        out = [x for x in out if x.thread_id != victim.thread_id]
        evicted.append(victim.thread_id)
        ranked = sorted(out, key=lambda t: (t.persistence_turns, t.intensity, t.thread_id))
    nf = list(trace.rules_fired)
    nf.append("evict_capacity")
    new_trace = trace.model_copy(
        update={
            "evicted_thread_ids": (list(trace.evicted_thread_ids) + evicted)[:TRACE_LIST_MAX_IDS],
            "rules_fired": nf[:TRACE_LIST_MAX_RULES],
        }
    )
    return out, new_trace


def update_narrative_threads(
    *,
    prior: StoryNarrativeThreadSet,
    latest_commit: StoryNarrativeCommitRecord | dict[str, Any],
    history_tail: list[dict[str, Any]],
    committed_scene_id: str,
    turn_number: int,
) -> tuple[StoryNarrativeThreadSet, ThreadUpdateTrace]:
    """Derive the next thread set from authoritative narrative commits only."""
    from app.story_runtime.narrative_threads_update import update_narrative_threads_impl

    return update_narrative_threads_impl(
        prior=prior,
        latest_commit=latest_commit,
        history_tail=history_tail,
        committed_scene_id=committed_scene_id,
        turn_number=turn_number,
    )


def build_graph_thread_export(
    thread_set: StoryNarrativeThreadSet,
) -> tuple[list[dict[str, Any]], str | None]:
    """Compact prior-thread snapshot for graph state (bounded; no evidence lists)."""

    act = [t for t in thread_set.active if t.status != "resolved"]
    act = sorted(act, key=lambda t: (-t.intensity, t.thread_id))[:GRAPH_EXPORT_MAX_ACTIVE]
    export: list[dict[str, Any]] = []
    parts: list[str] = []
    for th in act:
        ents = th.related_entities[:GRAPH_RELATED_ENTITIES_MAX]
        hint = th.resolution_hint or ""
        export.append(
            {
                "thread_id": th.thread_id,
                "thread_kind": _short(th.thread_kind, MAX_THREAD_KIND_LEN),
                "status": th.status,
                "intensity": th.intensity,
                "related_entities": ents,
                "resolution_hint": _short(hint, GRAPH_RESOLUTION_HINT_MAX) if hint else None,
            }
        )
        parts.append(f"{th.thread_kind}:{th.intensity}")
    summary: str | None = None
    if parts:
        raw = "|".join(parts)
        summary = _short(raw, THREAD_PRESSURE_SUMMARY_MAX)
    return export, summary


def thread_continuity_metrics(thread_set: StoryNarrativeThreadSet) -> dict[str, Any]:
    act = [t for t in thread_set.active if t.status != "resolved"]
    if not act:
        return {
            "thread_count": 0,
            "dominant_thread_kind": None,
            "thread_pressure_level": 0,
        }
    dominant = max(act, key=lambda t: (t.intensity, t.persistence_turns, t.thread_id))
    pressure = min(10, max(t.intensity for t in act))
    return {
        "thread_count": len(act),
        "dominant_thread_kind": dominant.thread_kind,
        "thread_pressure_level": pressure,
    }
