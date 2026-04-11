"""Pure helpers for narrative thread derivation from commit consequences (DS-003)."""

from __future__ import annotations

import hashlib

from app.runtime.narrative_threads import (
    NarrativeThreadState,
    _DE_ESCALATION_SEGMENTS,
    _ESCALATION_SEGMENTS,
    _MAX_ACTIVE_THREADS,
    _MAX_EVIDENCE,
    _STATE_CHANGED_PREFIX,
)


def paths_from_consequences(consequences: list[str]) -> list[str]:
    out: list[str] = []
    for c in consequences:
        if not c.startswith(_STATE_CHANGED_PREFIX):
            continue
        p = c[len(_STATE_CHANGED_PREFIX) :].strip()
        if p:
            out.append(p)
    return out


def character_ids_from_paths(paths: list[str]) -> list[str]:
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


def path_signal(path: str) -> str | None:
    lower = path.lower()
    for seg in _ESCALATION_SEGMENTS:
        if seg in lower:
            return "escalation"
    for seg in _DE_ESCALATION_SEGMENTS:
        if seg in lower:
            return "de_escalation"
    return None


def stable_anchor_id(kind: str, *parts: str) -> str:
    payload = "|".join(sorted(parts))
    h = hashlib.sha256(f"{kind}:{payload}".encode()).hexdigest()[:12]
    return f"{kind}:{h}"


def interpersonal_thread_id(chars: list[str]) -> str:
    if len(chars) >= 2:
        a, b = sorted(chars)[:2]
        return stable_anchor_id("interpersonal_tension", a, b)
    if len(chars) == 1:
        return stable_anchor_id("interpersonal_pressure", chars[0])
    return stable_anchor_id("interpersonal_pressure", "none")


def avoidance_thread_id(scene_id: str) -> str:
    return stable_anchor_id("avoidance_deadlock", scene_id or "unknown")


def merge_evidence(existing: list[str], new_tokens: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for x in list(existing) + new_tokens:
        if x not in seen:
            seen.add(x)
            merged.append(x)
        if len(merged) >= _MAX_EVIDENCE:
            break
    return merged


def evict_lowest_priority(active: list[NarrativeThreadState]) -> list[NarrativeThreadState]:
    if len(active) <= _MAX_ACTIVE_THREADS:
        return active
    ranked = sorted(active, key=lambda t: (t.intensity, t.persistence_turns, t.thread_id))
    drop = len(active) - _MAX_ACTIVE_THREADS
    return ranked[drop:]
