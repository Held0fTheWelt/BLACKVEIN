"""Commit-Pfad: Narrative-Threads aus NarrativeCommit ableiten (DS-049)."""

from __future__ import annotations

import hashlib
from typing import Any

from app.runtime.progression_summary import ProgressionSummary
from app.runtime.relationship_context import RelationshipAxisContext
from app.runtime.runtime_models import NarrativeCommitRecord
from app.runtime.session_history import SessionHistory
from app.runtime.narrative_threads import (
    NarrativeThreadSet,
    NarrativeThreadState,
    ThreadStatus,
    _cap_str,
    _DE_ESCALATION_SEGMENTS,
    _ESCALATION_SEGMENTS,
    _MAX_ACTIVE_THREADS,
    _MAX_EVIDENCE,
    _MAX_RELATED_CHARACTERS,
    _MAX_RELATED_PATHS,
    _MAX_RESOLUTION_HINT_LEN,
    _MAX_RESOLVED_RECENT,
    _STATE_CHANGED_PREFIX,
)


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
    ranked = sorted(active, key=lambda t: (t.intensity, t.persistence_turns, t.thread_id))
    drop = len(active) - _MAX_ACTIVE_THREADS
    return ranked[drop:]


def update_narrative_threads_from_commit_impl(
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

    if chars:
        tid = _interpersonal_thread_id(chars)
        upsert_thread(
            tid,
            "interpersonal_tension" if len(chars) >= 2 else "interpersonal_pressure",
            default_status="active",
            paths_for_thread=paths,
            chars_for_thread=chars,
        )

    if relationship.has_escalation_markers and chars:
        tid = _interpersonal_thread_id(chars)
        if tid in by_id:
            t = by_id[tid]
            t.intensity = min(5, t.intensity + 1)
            if t.status in ("active", "holding"):
                t.status = "escalating"

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
