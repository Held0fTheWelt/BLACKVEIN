"""Phases for narrative thread updates from a narrative commit (DS-003 despaghettification).

Algorithm extracted from ``update_narrative_threads_from_commit_impl`` for smaller surfaces
and explicit ``NarrativeCommitThreadDrive`` (commit-derived inputs used after parsing).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from app.runtime.progression_summary import ProgressionSummary
from app.runtime.relationship_context import RelationshipAxisContext
from app.runtime.runtime_models import NarrativeCommitRecord
from app.runtime.narrative_threads import (
    NarrativeThreadSet,
    NarrativeThreadState,
    ThreadStatus,
    _cap_str,
    _MAX_RESOLVED_RECENT,
    _MAX_RELATED_CHARACTERS,
    _MAX_RELATED_PATHS,
    _MAX_RESOLUTION_HINT_LEN,
    _STATE_CHANGED_PREFIX,
)
from app.runtime.narrative_state_transfer_dto import NarrativeCommitEvent
from app.runtime.narrative_threads_commit_path_utils import (
    avoidance_thread_id,
    character_ids_from_paths,
    evict_lowest_priority,
    interpersonal_thread_id,
    merge_evidence,
    path_signal,
    paths_from_consequences,
)


@dataclass(frozen=True)
class NarrativeCommitThreadDrive:
    """Explicit commit-derived inputs for thread mutation (sub-step contract)."""

    cons: list[str]
    paths: list[str]
    chars: list[str]
    turn_no: int
    scene: str
    is_terminal: bool
    situation_status: str
    has_escalation_path: bool
    has_de_path: bool
    evidence_tokens: list[str]


def build_narrative_commit_thread_drive(
    narrative_commit: Union[NarrativeCommitRecord, NarrativeCommitEvent],
) -> NarrativeCommitThreadDrive:
    if isinstance(narrative_commit, NarrativeCommitEvent):
        payload = narrative_commit.commit_payload
        cons = list(payload.get("canonical_consequences") or [])
        turn_no = payload.get("turn_number", 0)
        scene = payload.get("committed_scene_id", "")
        is_terminal = payload.get("is_terminal", False)
        situation_status = payload.get("situation_status", "continue")
    else:
        cons = list(narrative_commit.canonical_consequences or [])
        turn_no = narrative_commit.turn_number
        scene = narrative_commit.committed_scene_id or ""
        is_terminal = narrative_commit.is_terminal
        situation_status = narrative_commit.situation_status

    paths = paths_from_consequences(cons)
    chars = character_ids_from_paths(paths)
    path_pairs = [(p, path_signal(p)) for p in paths]
    has_escalation_path = any(s == "escalation" for _, s in path_pairs)
    has_de_path = any(s == "de_escalation" for _, s in path_pairs)
    evidence_tokens = [c for c in cons if c.startswith(_STATE_CHANGED_PREFIX)][:4]

    return NarrativeCommitThreadDrive(
        cons=cons,
        paths=paths,
        chars=chars,
        turn_no=turn_no,
        scene=scene,
        is_terminal=is_terminal,
        situation_status=situation_status,
        has_escalation_path=has_escalation_path,
        has_de_path=has_de_path,
        evidence_tokens=evidence_tokens,
    )


def maybe_thread_set_for_terminal_ending(
    prior: NarrativeThreadSet,
    drive: NarrativeCommitThreadDrive,
) -> NarrativeThreadSet | None:
    if not (drive.is_terminal or drive.situation_status == "ending_reached"):
        return None
    resolved_batch = [
        t.model_copy(
            update={
                "status": "resolved",
                "resolution_hint": _cap_str("narrative_ending", _MAX_RESOLUTION_HINT_LEN),
                "last_updated_turn": drive.turn_no,
            }
        )
        for t in prior.active
    ]
    merged_resolved = resolved_batch + prior.resolved_recent
    return NarrativeThreadSet(
        active=[],
        resolved_recent=merged_resolved[:_MAX_RESOLVED_RECENT],
    )


def _upsert_narrative_thread(
    by_id: dict[str, NarrativeThreadState],
    *,
    thread_id: str,
    kind: str,
    default_status: ThreadStatus,
    paths_for_thread: list[str],
    chars_for_thread: list[str],
    drive: NarrativeCommitThreadDrive,
    progression: ProgressionSummary,
) -> None:
    rel_paths = sorted(set(paths_for_thread))[:_MAX_RELATED_PATHS]
    rel_chars = sorted(set(chars_for_thread))[:_MAX_RELATED_CHARACTERS]
    if thread_id in by_id:
        t = by_id[thread_id]
        t.last_updated_turn = drive.turn_no
        t.persistence_turns = t.persistence_turns + 1
        t.related_paths = sorted(set(t.related_paths) | set(rel_paths))[:_MAX_RELATED_PATHS]
        t.related_characters = sorted(set(t.related_characters) | set(rel_chars))[
            :_MAX_RELATED_CHARACTERS
        ]
        t.evidence_consequences = merge_evidence(t.evidence_consequences, drive.evidence_tokens)
        t.scene_anchor = drive.scene or t.scene_anchor
        if drive.has_escalation_path:
            t.intensity = min(5, t.intensity + 1)
            t.status = "escalating"
        elif drive.has_de_path:
            t.intensity = max(0, t.intensity - 1)
            t.status = "de_escalating" if t.intensity > 0 else "resolved"
        else:
            if t.status == "escalating" and progression.stalled_turn_count == 0:
                t.status = "active"
            elif t.status == "de_escalating" and t.intensity > 0:
                t.status = "active"
    else:
        intensity = 1 if drive.has_escalation_path else (0 if drive.has_de_path else 1)
        status: ThreadStatus
        if drive.has_escalation_path:
            status = "escalating"
        elif drive.has_de_path:
            status = "de_escalating" if intensity > 0 else "resolved"
        else:
            status = default_status
        by_id[thread_id] = NarrativeThreadState(
            thread_id=thread_id,
            thread_kind=kind,
            status=status,
            scene_anchor=drive.scene,
            related_paths=rel_paths,
            related_characters=rel_chars,
            evidence_consequences=merge_evidence([], drive.evidence_tokens),
            intensity=min(5, max(0, intensity)),
            persistence_turns=1,
            last_updated_turn=drive.turn_no,
            resolution_hint=None,
        )


def apply_non_terminal_thread_updates(
    prior: NarrativeThreadSet,
    drive: NarrativeCommitThreadDrive,
    progression: ProgressionSummary,
    relationship: RelationshipAxisContext,
) -> NarrativeThreadSet:
    active = [t.model_copy(deep=True) for t in prior.active]
    by_id: dict[str, NarrativeThreadState] = {t.thread_id: t for t in active}

    if progression.progression_momentum == "stalled" and progression.stalled_turn_count >= 2:
        if drive.situation_status == "continue":
            aid = avoidance_thread_id(drive.scene)
            _upsert_narrative_thread(
                by_id,
                thread_id=aid,
                kind="avoidance_deadlock",
                default_status="holding",
                paths_for_thread=drive.paths,
                chars_for_thread=drive.chars,
                drive=drive,
                progression=progression,
            )
            by_id[aid].status = "holding"

    if drive.chars:
        tid = interpersonal_thread_id(drive.chars)
        _upsert_narrative_thread(
            by_id,
            thread_id=tid,
            kind="interpersonal_tension" if len(drive.chars) >= 2 else "interpersonal_pressure",
            default_status="active",
            paths_for_thread=drive.paths,
            chars_for_thread=drive.chars,
            drive=drive,
            progression=progression,
        )

    if relationship.has_escalation_markers and drive.chars:
        tid = interpersonal_thread_id(drive.chars)
        if tid in by_id:
            t = by_id[tid]
            t.intensity = min(5, t.intensity + 1)
            if t.status in ("active", "holding"):
                t.status = "escalating"

    if (
        drive.situation_status == "continue"
        and progression.same_scene_progression_count >= 2
        and drive.paths
        and drive.chars
    ):
        tid = interpersonal_thread_id(drive.chars)
        if tid not in by_id:
            _upsert_narrative_thread(
                by_id,
                thread_id=tid,
                kind="interpersonal_tension" if len(drive.chars) >= 2 else "interpersonal_pressure",
                default_status="active",
                paths_for_thread=drive.paths,
                chars_for_thread=drive.chars,
                drive=drive,
                progression=progression,
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
                        "last_updated_turn": drive.turn_no,
                    }
                )
            )
        else:
            active_list.append(t)

    active_list = evict_lowest_priority(active_list)
    active_list = sorted(active_list, key=lambda x: (-x.intensity, -x.persistence_turns, x.thread_id))

    merged_rr = new_resolved + prior.resolved_recent
    merged_rr = merged_rr[:_MAX_RESOLVED_RECENT]

    return NarrativeThreadSet(active=active_list, resolved_recent=merged_rr)
