"""Hilfskontext für Thread-Upserts (DS-019)."""

from __future__ import annotations

from app.story_runtime.narrative_threads import (
    MAX_THREAD_KIND_LEN,
    StoryNarrativeThread,
    ThreadStatus,
    _append_evidence,
    _token_key,
    _short,
)


class ThreadUpsertContext:
    """Hält mutable active/rules/created/updated für find/upsert (vorher verschachtelte Funktionen)."""

    __slots__ = ("active", "rules", "created", "updated", "turn_number")

    def __init__(
        self,
        *,
        active: list[StoryNarrativeThread],
        rules: list[str],
        created: list[str],
        updated: list[str],
        turn_number: int,
    ) -> None:
        self.active = active
        self.rules = rules
        self.created = created
        self.updated = updated
        self.turn_number = turn_number

    def find(self, kind: str, anchor: str) -> StoryNarrativeThread | None:
        for th in self.active:
            if th.thread_kind == kind and (th.scene_anchor or "") == anchor:
                return th
        return None

    def upsert(
        self,
        *,
        kind: str,
        anchor: str,
        seed: str,
        bump_intensity: int,
        status: ThreadStatus,
        evidence: str,
    ) -> None:
        tid = _token_key(kind, anchor, seed)
        th = self.find(kind, anchor)
        if th is None:
            self.rules.append(f"create:{kind}")
            self.created.append(tid)
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
                last_updated_turn=self.turn_number,
            )
            th = _append_evidence(th, evidence)
            self.active.append(th)
            self.updated.append(tid)
            return
        self.rules.append(f"update:{kind}")
        new_int = min(10, th.intensity + bump_intensity)
        new_p = th.persistence_turns + 1
        th2 = th.model_copy(
            update={
                "intensity": new_int,
                "persistence_turns": new_p,
                "status": status,
                "last_updated_turn": self.turn_number,
            }
        )
        th2 = _append_evidence(th2, evidence)
        self.active = [th2 if x.thread_id == tid else x for x in self.active]
        self.updated.append(tid)
