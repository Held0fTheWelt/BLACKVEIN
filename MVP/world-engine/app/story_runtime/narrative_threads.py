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

    rules: list[str] = []
    created: list[str] = []
    updated: list[str] = []
    evicted: list[str] = []

    d = _parse_commit(latest_commit)
    scene = committed_scene_id.strip() or _commit_scene_id(d)
    terminal = _is_terminal_commit(d)
    blocked = _has_block(d)
    ambiguity = _has_ambiguity(d)

    latest_row = {"narrative_commit": d}
    full_tail = [*history_tail, latest_row]

    active = [t.model_copy(deep=True) for t in prior.active]
    resolved_recent = [t.model_copy(deep=True) for t in prior.resolved_recent]

    if terminal:
        rules.append("terminal_resolve_all_active")
        new_resolved: list[StoryNarrativeThread] = []
        for th in active:
            rth = _resolve_thread(th, turn=turn_number, hint="narrative_terminal")
            new_resolved.append(rth)
        merged_resolved = (new_resolved + resolved_recent)[:MAX_RESOLVED_RECENT]
        trace = ThreadUpdateTrace(
            rules_fired=rules,
            created_thread_ids=[],
            updated_thread_ids=[t.thread_id for t in new_resolved][:TRACE_LIST_MAX_UPDATED],
            evicted_thread_ids=[],
            summary=_short("terminal:" + str(len(new_resolved)), TRACE_SUMMARY_MAX),
        )
        return StoryNarrativeThreadSet(active=[], resolved_recent=merged_resolved), trace

    def _find(kind: str, anchor: str) -> StoryNarrativeThread | None:
        for th in active:
            if th.thread_kind == kind and (th.scene_anchor or "") == anchor:
                return th
        return None

    def _upsert(
        *,
        kind: str,
        anchor: str,
        seed: str,
        bump_intensity: int,
        status: ThreadStatus,
        evidence: str,
    ) -> None:
        nonlocal active, rules, created, updated
        tid = _token_key(kind, anchor, seed)
        th = _find(kind, anchor)
        if th is None:
            rules.append(f"create:{kind}")
            created.append(tid)
            th = StoryNarrativeThread(
                thread_id=tid,
                thread_kind=_short(kind, MAX_THREAD_KIND_LEN),
                status=status,
                scene_anchor=anchor or None,
                intensity=min(10, max(0, bump_intensity)),
                persistence_turns=1,
                related_scenes=[anchor] if anchor else [],
                related_entities=[],
                evidence_tokens=[],
                last_updated_turn=turn_number,
            )
            th = _append_evidence(th, evidence)
            active.append(th)
            updated.append(tid)
            return
        rules.append(f"update:{kind}")
        new_int = min(10, th.intensity + bump_intensity)
        new_p = th.persistence_turns + 1
        th2 = th.model_copy(
            update={
                "intensity": new_int,
                "persistence_turns": new_p,
                "status": status,
                "last_updated_turn": turn_number,
            }
        )
        th2 = _append_evidence(th2, evidence)
        active = [th2 if x.thread_id == tid else x for x in active]
        updated.append(tid)

    if blocked:
        seed = "block"
        tok = _first_evidence_token(d)
        _upsert(
            kind="progression_blocked",
            anchor=scene,
            seed=seed,
            bump_intensity=1,
            status="active",
            evidence=tok,
        )
    if ambiguity:
        seed = "ambiguity"
        tok = _first_evidence_token(d)
        _upsert(
            kind="interpretation_pressure",
            anchor=scene,
            seed=seed,
            bump_intensity=1,
            status="active",
            evidence=tok,
        )

    # De-escalate / hold threads anchored at this scene when this commit is clean continue
    if (
        not blocked
        and not ambiguity
        and d.get("situation_status") == "continue"
    ):
        rules.append("clean_continue_adjust")
        summary = d.get("committed_interpretation_summary")
        loc_only = isinstance(summary, dict) and bool(summary.get("local_narrative_continuation_only"))
        new_active: list[StoryNarrativeThread] = []
        for th in active:
            if (th.scene_anchor or "") != scene:
                new_active.append(th)
                continue
            if th.thread_kind not in {"progression_blocked", "interpretation_pressure"}:
                new_active.append(th)
                continue
            updated.append(th.thread_id)
            if loc_only and th.intensity > 0:
                ni = max(0, th.intensity - 1)
                st: ThreadStatus = "de_escalating" if ni < th.intensity else th.status
                th2 = th.model_copy(
                    update={
                        "intensity": ni,
                        "persistence_turns": th.persistence_turns + 1,
                        "status": st,
                        "last_updated_turn": turn_number,
                    }
                )
                if ni == 0:
                    rules.append(f"resolve_clean:{th.thread_kind}")
                    rth = _resolve_thread(th2, turn=turn_number, hint="stabilized_continue")
                    resolved_recent = ([rth] + resolved_recent)[:MAX_RESOLVED_RECENT]
                else:
                    th2 = th2.model_copy(update={"status": "holding"})
                    new_active.append(th2)
            else:
                th2 = th.model_copy(
                    update={
                        "persistence_turns": th.persistence_turns + 1,
                        "status": "holding",
                        "last_updated_turn": turn_number,
                    }
                )
                new_active.append(th2)
        active = new_active

    # Escalation: repeated pressure at the same scene in the tail
    press_count = _tail_blocked_or_ambiguity_count(full_tail, scene)
    if press_count >= 3:
        rules.append("escalate_repeated_pressure")
        new_active = []
        for th in active:
            if (th.scene_anchor or "") != scene:
                new_active.append(th)
                continue
            if th.status == "resolved":
                new_active.append(th)
                continue
            updated.append(th.thread_id)
            new_active.append(
                th.model_copy(
                    update={
                        "status": "escalating",
                        "intensity": min(10, th.intensity + 1),
                        "last_updated_turn": turn_number,
                    }
                )
            )
        active = new_active

    # Deadlock / hold labeling: blocked repeats at scene without transition
    blocked_turns = 0
    for row in full_tail:
        nc = row.get("narrative_commit") if isinstance(row, dict) else None
        if not isinstance(nc, dict):
            continue
        if _commit_scene_id(nc) != scene:
            continue
        if _has_block(nc):
            blocked_turns += 1
    if blocked_turns >= 2 and blocked:
        rules.append("pattern_deadlock_hold")
        new_active = []
        for th in active:
            if th.thread_kind == "progression_blocked" and (th.scene_anchor or "") == scene:
                updated.append(th.thread_id)
                new_active.append(
                    th.model_copy(
                        update={
                            "status": "holding",
                            "last_updated_turn": turn_number,
                        }
                    )
                )
            else:
                new_active.append(th)
        active = new_active

    trace = ThreadUpdateTrace(
        rules_fired=rules,
        created_thread_ids=created[:TRACE_LIST_MAX_IDS],
        updated_thread_ids=list(dict.fromkeys(updated))[:TRACE_LIST_MAX_UPDATED],
        evicted_thread_ids=evicted[:TRACE_LIST_MAX_IDS],
        summary=_short(
            f"rules={len(rules)};active={len(active)}",
            TRACE_SUMMARY_MAX,
        ),
    )

    active, trace = _evict_deterministic(active, trace)

    return StoryNarrativeThreadSet(active=active[:MAX_ACTIVE_THREADS], resolved_recent=resolved_recent), trace


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
