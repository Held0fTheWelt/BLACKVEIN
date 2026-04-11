"""Deterministic narrative-thread update passes (DS-044), extracted from update_narrative_threads_impl."""

from __future__ import annotations

from typing import Any

from app.story_runtime.narrative_threads import (
    MAX_RESOLVED_RECENT,
    StoryNarrativeThread,
    StoryNarrativeThreadSet,
    ThreadStatus,
    ThreadUpdateTrace,
    TRACE_LIST_MAX_UPDATED,
    TRACE_SUMMARY_MAX,
    _commit_scene_id,
    _has_block,
    _resolve_thread,
    _short,
    _tail_blocked_or_ambiguity_count,
)


def terminal_resolve_all_active(
    *,
    prior_active: list[StoryNarrativeThread],
    prior_resolved: list[StoryNarrativeThread],
    turn_number: int,
) -> tuple[StoryNarrativeThreadSet, ThreadUpdateTrace]:
    rules: list[str] = ["terminal_resolve_all_active"]
    new_resolved: list[StoryNarrativeThread] = []
    for th in prior_active:
        new_resolved.append(_resolve_thread(th, turn=turn_number, hint="narrative_terminal"))
    merged_resolved = (new_resolved + prior_resolved)[:MAX_RESOLVED_RECENT]
    trace = ThreadUpdateTrace(
        rules_fired=rules,
        created_thread_ids=[],
        updated_thread_ids=[t.thread_id for t in new_resolved][:TRACE_LIST_MAX_UPDATED],
        evicted_thread_ids=[],
        summary=_short("terminal:" + str(len(new_resolved)), TRACE_SUMMARY_MAX),
    )
    return StoryNarrativeThreadSet(active=[], resolved_recent=merged_resolved), trace


def apply_clean_continue_adjustment(
    *,
    blocked: bool,
    ambiguity: bool,
    d: dict[str, Any],
    scene: str,
    active: list[StoryNarrativeThread],
    rules: list[str],
    updated: list[str],
    resolved_recent: list[StoryNarrativeThread],
    turn_number: int,
) -> tuple[list[StoryNarrativeThread], list[StoryNarrativeThread]]:
    if blocked or ambiguity or d.get("situation_status") != "continue":
        return active, resolved_recent

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
    return new_active, resolved_recent


def apply_repeated_pressure_escalation(
    *,
    full_tail: list[dict[str, Any]],
    scene: str,
    active: list[StoryNarrativeThread],
    rules: list[str],
    updated: list[str],
    turn_number: int,
) -> list[StoryNarrativeThread]:
    press_count = _tail_blocked_or_ambiguity_count(full_tail, scene)
    if press_count < 3:
        return active

    rules.append("escalate_repeated_pressure")
    new_active: list[StoryNarrativeThread] = []
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
    return new_active


def apply_deadlock_hold_pattern(
    *,
    full_tail: list[dict[str, Any]],
    scene: str,
    blocked: bool,
    active: list[StoryNarrativeThread],
    rules: list[str],
    updated: list[str],
    turn_number: int,
) -> list[StoryNarrativeThread]:
    blocked_turns = 0
    for row in full_tail:
        nc = row.get("narrative_commit") if isinstance(row, dict) else None
        if not isinstance(nc, dict):
            continue
        if _commit_scene_id(nc) != scene:
            continue
        if _has_block(nc):
            blocked_turns += 1
    if blocked_turns < 2 or not blocked:
        return active

    rules.append("pattern_deadlock_hold")
    new_active: list[StoryNarrativeThread] = []
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
    return new_active
