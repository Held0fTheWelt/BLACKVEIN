"""Narrative thread derivation steps (DS-019 split from narrative_threads)."""

from __future__ import annotations

from typing import Any

from app.story_runtime.commit_models import StoryNarrativeCommitRecord
from app.story_runtime.narrative_threads import (
    MAX_ACTIVE_THREADS,
    TRACE_LIST_MAX_IDS,
    TRACE_LIST_MAX_UPDATED,
    TRACE_SUMMARY_MAX,
    StoryNarrativeThreadSet,
    ThreadUpdateTrace,
    _commit_scene_id,
    _evict_deterministic,
    _first_evidence_token,
    _has_ambiguity,
    _has_block,
    _is_terminal_commit,
    _parse_commit,
    _short,
)
from app.story_runtime.narrative_threads_update_ops import ThreadUpsertContext
from app.story_runtime.narrative_threads_update_passes import (
    apply_clean_continue_adjustment,
    apply_deadlock_hold_pattern,
    apply_repeated_pressure_escalation,
    terminal_resolve_all_active,
)


def update_narrative_threads_impl(
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
        return terminal_resolve_all_active(
            prior_active=active,
            prior_resolved=resolved_recent,
            turn_number=turn_number,
        )

    ctx = ThreadUpsertContext(
        active=active,
        rules=rules,
        created=created,
        updated=updated,
        turn_number=turn_number,
    )

    if blocked:
        seed = "block"
        tok = _first_evidence_token(d)
        ctx.upsert(
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
        ctx.upsert(
            kind="interpretation_pressure",
            anchor=scene,
            seed=seed,
            bump_intensity=1,
            status="active",
            evidence=tok,
        )
    active = ctx.active
    rules = ctx.rules
    created = ctx.created
    updated = ctx.updated

    active, resolved_recent = apply_clean_continue_adjustment(
        blocked=blocked,
        ambiguity=ambiguity,
        d=d,
        scene=scene,
        active=active,
        rules=rules,
        updated=updated,
        resolved_recent=resolved_recent,
        turn_number=turn_number,
    )

    active = apply_repeated_pressure_escalation(
        full_tail=full_tail,
        scene=scene,
        active=active,
        rules=rules,
        updated=updated,
        turn_number=turn_number,
    )

    active = apply_deadlock_hold_pattern(
        full_tail=full_tail,
        scene=scene,
        blocked=blocked,
        active=active,
        rules=rules,
        updated=updated,
        turn_number=turn_number,
    )

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
