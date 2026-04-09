"""Bounded narrative consequence thread progression tests."""

from __future__ import annotations

from datetime import datetime, timezone

from app.runtime.ai_turn_executor import build_adapter_request
from app.runtime.narrative_threads import (
    NarrativeThreadSet,
    NarrativeThreadState,
    coerce_narrative_thread_set,
    compact_threads_for_adapter,
    hydrate_narrative_threads_layer,
    sync_narrative_thread_set,
    update_narrative_threads_from_commit,
)
from app.runtime.progression_summary import ProgressionSummary
from app.runtime.relationship_context import RelationshipAxisContext
from app.runtime.runtime_models import GuardOutcome, NarrativeCommitRecord, SessionContextLayers, SessionState
from app.runtime.session_history import HistoryEntry, SessionHistory
from app.runtime.short_term_context import ShortTermTurnContext
from app.runtime.turn_executor import MockDecision, TurnExecutionResult, _derive_runtime_context


def _nc(
    *,
    turn: int,
    scene: str = "scene_a",
    consequences: list[str],
    situation: str = "continue",
    terminal: bool = False,
) -> NarrativeCommitRecord:
    return NarrativeCommitRecord(
        turn_number=turn,
        prior_scene_id=scene,
        committed_scene_id=scene,
        situation_status=situation if not terminal else "ending_reached",
        committed_ending_id="e1" if terminal else None,
        accepted_delta_targets=[],
        rejected_delta_targets=[],
        committed_trigger_ids=[],
        guard_outcome="ACCEPTED",
        authoritative_reason="test",
        canonical_consequences=consequences,
        is_terminal=terminal,
    )


def _minimal_session() -> SessionState:
    return SessionState(
        module_id="god_of_carnage",
        module_version="1",
        current_scene_id="scene_a",
        context_layers=SessionContextLayers(),
    )


def _progression_holding() -> ProgressionSummary:
    return ProgressionSummary(
        first_turn_covered=1,
        last_turn_covered=1,
        total_turns_in_source=1,
        current_scene_id="scene_a",
        progression_momentum="holding",
        stalled_turn_count=0,
        same_scene_progression_count=1,
    )


def _relationship_neutral() -> RelationshipAxisContext:
    return RelationshipAxisContext()


def _relationship_escalating() -> RelationshipAxisContext:
    return RelationshipAxisContext(has_escalation_markers=True)


def test_thread_id_deterministic_for_same_inputs():
    cons = [
        "state_changed:characters.alice.relationships.bob.tension",
        "state_changed:characters.bob.emotional_state",
        "scene_continue:scene_a",
    ]
    nc = _nc(turn=1, consequences=cons)
    h = SessionHistory()
    h.add_entry(
        HistoryEntry(
            turn_number=1,
            scene_id="scene_a",
            guard_outcome="ACCEPTED",
            canonical_consequences=cons,
            situation_status="continue",
        )
    )
    a = update_narrative_threads_from_commit(
        NarrativeThreadSet(),
        narrative_commit=nc,
        _history=h,
        progression=_progression_holding(),
        relationship=_relationship_neutral(),
    )
    b = update_narrative_threads_from_commit(
        NarrativeThreadSet(),
        narrative_commit=nc,
        _history=h,
        progression=_progression_holding(),
        relationship=_relationship_neutral(),
    )
    assert a.active and b.active
    assert a.active[0].thread_id == b.active[0].thread_id
    assert a.active[0].thread_kind == b.active[0].thread_kind


def test_same_scene_escalation_raises_intensity():
    base_cons = [
        "state_changed:characters.alice.relationships.bob.tension",
        "state_changed:characters.bob.emotional_state",
        "scene_continue:scene_a",
    ]
    nc1 = _nc(turn=1, consequences=base_cons)
    h = SessionHistory()
    h.add_entry(
        HistoryEntry(
            turn_number=1,
            scene_id="scene_a",
            guard_outcome="ACCEPTED",
            canonical_consequences=base_cons,
            situation_status="continue",
        )
    )
    ps1 = ProgressionSummary(
        first_turn_covered=1,
        last_turn_covered=1,
        total_turns_in_source=1,
        current_scene_id="scene_a",
        same_scene_progression_count=1,
        progression_momentum="holding",
        stalled_turn_count=0,
    )
    s1 = update_narrative_threads_from_commit(
        NarrativeThreadSet(),
        narrative_commit=nc1,
        _history=h,
        progression=ps1,
        relationship=_relationship_escalating(),
    )
    assert s1.active
    i1 = s1.active[0].intensity

    h.add_entry(
        HistoryEntry(
            turn_number=2,
            scene_id="scene_a",
            guard_outcome="ACCEPTED",
            canonical_consequences=base_cons,
            situation_status="continue",
        )
    )
    nc2 = _nc(turn=2, consequences=base_cons)
    ps2 = ProgressionSummary(
        first_turn_covered=1,
        last_turn_covered=2,
        total_turns_in_source=2,
        current_scene_id="scene_a",
        same_scene_progression_count=2,
        progression_momentum="developing",
        stalled_turn_count=0,
    )
    s2 = update_narrative_threads_from_commit(
        s1,
        narrative_commit=nc2,
        _history=h,
        progression=ps2,
        relationship=_relationship_escalating(),
    )
    assert s2.active[0].intensity >= i1


def test_avoidance_deadlock_thread_when_stalled():
    cons = [
        "state_changed:characters.x.y",
        "scene_continue:scene_a",
    ]
    nc = _nc(turn=3, consequences=cons)
    h = SessionHistory()
    for t in (1, 2, 3):
        h.add_entry(
            HistoryEntry(
                turn_number=t,
                scene_id="scene_a",
                guard_outcome="ACCEPTED",
                canonical_consequences=cons,
                situation_status="continue",
            )
        )
    ps = ProgressionSummary(
        first_turn_covered=1,
        last_turn_covered=3,
        total_turns_in_source=3,
        current_scene_id="scene_a",
        progression_momentum="stalled",
        stalled_turn_count=2,
        same_scene_progression_count=1,
    )
    out = update_narrative_threads_from_commit(
        NarrativeThreadSet(),
        narrative_commit=nc,
        _history=h,
        progression=ps,
        relationship=_relationship_neutral(),
    )
    kinds = {t.thread_kind for t in out.active}
    assert "avoidance_deadlock" in kinds
    assert any(t.status == "holding" for t in out.active if t.thread_kind == "avoidance_deadlock")


def test_de_escalation_resolves_interpersonal_thread():
    cons_esc = [
        "state_changed:characters.alice.relationships.bob.tension",
        "scene_continue:scene_a",
    ]
    nc1 = _nc(turn=1, consequences=cons_esc)
    h = SessionHistory()
    h.add_entry(
        HistoryEntry(
            turn_number=1,
            scene_id="scene_a",
            guard_outcome="ACCEPTED",
            canonical_consequences=cons_esc,
            situation_status="continue",
        )
    )
    s1 = update_narrative_threads_from_commit(
        NarrativeThreadSet(),
        narrative_commit=nc1,
        _history=h,
        progression=_progression_holding(),
        relationship=_relationship_neutral(),
    )
    assert s1.active

    cons_calm = [
        "state_changed:characters.alice.relationships.bob.trust",
        "scene_continue:scene_a",
    ]
    nc2 = _nc(turn=2, consequences=cons_calm)
    h.add_entry(
        HistoryEntry(
            turn_number=2,
            scene_id="scene_a",
            guard_outcome="ACCEPTED",
            canonical_consequences=cons_calm,
            situation_status="continue",
        )
    )
    s2 = update_narrative_threads_from_commit(
        s1,
        narrative_commit=nc2,
        _history=h,
        progression=_progression_holding(),
        relationship=_relationship_neutral(),
    )
    assert any(t.thread_kind.startswith("interpersonal") and t.status == "resolved" for t in s2.resolved_recent)


def test_eviction_keeps_max_active_threads_deterministically():
    filler = [
        NarrativeThreadState(
            thread_id=f"fill_{i}",
            thread_kind="filler",
            status="active",
            intensity=1,
            persistence_turns=1,
            last_updated_turn=1,
        )
        for i in range(8)
    ]
    prior = NarrativeThreadSet(active=filler)
    cons = [
        "state_changed:characters.zoe.relationships.quinn.tension",
        "state_changed:characters.quinn.emotional_state",
        "scene_continue:scene_a",
    ]
    nc = _nc(turn=5, consequences=cons)
    h = SessionHistory()
    h.add_entry(
        HistoryEntry(turn_number=5, scene_id="scene_a", guard_outcome="ACCEPTED", situation_status="continue")
    )
    out = update_narrative_threads_from_commit(
        prior,
        narrative_commit=nc,
        _history=h,
        progression=_progression_holding(),
        relationship=_relationship_neutral(),
    )
    assert len(out.active) == 8


def test_terminal_clears_active_threads():
    prior = update_narrative_threads_from_commit(
        NarrativeThreadSet(),
        narrative_commit=_nc(
            turn=1,
            consequences=[
                "state_changed:characters.alice.emotional_state",
                "state_changed:characters.bob.emotional_state",
                "scene_continue:scene_a",
            ],
        ),
        _history=SessionHistory(),
        progression=_progression_holding(),
        relationship=_relationship_neutral(),
    )
    assert prior.active
    term = _nc(
        turn=2,
        consequences=["ending_reached:e1", "scene_continue:scene_a"],
        terminal=True,
    )
    out = update_narrative_threads_from_commit(
        prior,
        narrative_commit=term,
        _history=SessionHistory(),
        progression=_progression_holding(),
        relationship=_relationship_neutral(),
    )
    assert out.active == []


def test_migration_hydrate_from_metadata():
    session = _minimal_session()
    dumped = NarrativeThreadSet(
        active=[
            NarrativeThreadState(
                thread_id="tid_x",
                thread_kind="interpersonal_tension",
                status="active",
                intensity=2,
                last_updated_turn=1,
            )
        ]
    ).model_dump(mode="json")
    session.metadata["narrative_threads"] = dumped
    hydrate_narrative_threads_layer(session)
    assert session.context_layers.narrative_threads is not None
    assert coerce_narrative_thread_set(session.context_layers.narrative_threads).active[0].thread_id == "tid_x"


def test_dual_sync_metadata_and_context_layers():
    session = _minimal_session()
    ts = NarrativeThreadSet(
        active=[
            NarrativeThreadState(
                thread_id="sync_id",
                thread_kind="interpersonal_tension",
                status="escalating",
                intensity=3,
                last_updated_turn=2,
            )
        ]
    )
    sync_narrative_thread_set(session, ts)
    assert session.metadata["narrative_threads"]["active"][0]["thread_id"] == "sync_id"
    assert coerce_narrative_thread_set(session.context_layers.narrative_threads).active[0].thread_id == "sync_id"


def test_derive_without_commit_skips_overlay_and_lore_thread_tags(god_of_carnage_module):
    session = _minimal_session()
    session.context_layers.session_history = SessionHistory(max_size=100)
    session.context_layers.session_history.add_entry(
        HistoryEntry(turn_number=1, scene_id="scene_a", guard_outcome="ACCEPTED", situation_status="continue")
    )
    result = TurnExecutionResult(
        turn_number=1,
        session_id=session.session_id,
        execution_status="system_error",
        decision=MockDecision(detected_triggers=[], narrative_text="", rationale=""),
        validation_errors=[],
        accepted_deltas=[],
        rejected_deltas=[],
        updated_canonical_state={},
        updated_scene_id="scene_a",
        guard_outcome=GuardOutcome.STRUCTURALLY_INVALID,
        narrative_commit=None,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_ms=1.0,
        events=[],
    )
    session.context_layers.short_term_context = ShortTermTurnContext(
        turn_number=1,
        scene_id="scene_a",
        guard_outcome="STRUCTURALLY_INVALID",
    )
    _derive_runtime_context(session, god_of_carnage_module, last_result=None)
    st = session.context_layers.short_term_context
    assert st.active_thread_ids == []
    assert st.dominant_thread_kind == ""
    lore = session.context_layers.lore_direction_context
    assert lore is not None
    assert not any(x.startswith("thread_kind=") for x in lore.selection_rationale)


def test_derive_with_commit_applies_markers_and_lore_thread_tags(god_of_carnage_module):
    session = _minimal_session()
    session.context_layers.session_history = SessionHistory(max_size=100)
    nc = _nc(
        turn=1,
        consequences=[
            "state_changed:characters.alice.relationships.bob.tension",
            "state_changed:characters.bob.emotional_state",
            "scene_continue:scene_a",
        ],
    )
    tr = TurnExecutionResult(
        turn_number=1,
        session_id=session.session_id,
        execution_status="success",
        decision=MockDecision(detected_triggers=[], narrative_text="", rationale=""),
        validation_errors=[],
        accepted_deltas=[],
        rejected_deltas=[],
        updated_canonical_state={},
        updated_scene_id="scene_a",
        guard_outcome=GuardOutcome.ACCEPTED,
        narrative_commit=nc,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_ms=1.0,
        events=[],
    )
    session.context_layers.short_term_context = ShortTermTurnContext(
        turn_number=1,
        scene_id="scene_a",
        guard_outcome="ACCEPTED",
        situation_status="continue",
        canonical_consequences=nc.canonical_consequences,
    )
    session.context_layers.session_history.add_entry(
        HistoryEntry.from_short_term_context(session.context_layers.short_term_context)
    )
    _derive_runtime_context(session, god_of_carnage_module, last_result=tr)
    st = session.context_layers.short_term_context
    assert st.active_thread_ids
    assert st.dominant_thread_kind
    lore = session.context_layers.lore_direction_context
    assert any(x.startswith("thread_kind=") for x in lore.selection_rationale)


def test_compact_adapter_payload_json_safe_bounded():
    ts = NarrativeThreadSet(
        active=[
            NarrativeThreadState(
                thread_id="a",
                thread_kind="k",
                status="active",
                intensity=2,
                related_characters=["x"] * 10,
                related_paths=["p"] * 10,
                evidence_consequences=["e"] * 20,
                resolution_hint="hint",
            )
        ]
    )
    rows = compact_threads_for_adapter(ts)
    assert len(rows) == 1
    assert "evidence_consequences" not in rows[0]
    assert len(rows[0]["related_characters"]) <= 5
    assert len(rows[0]["related_paths"]) <= 5


def test_build_adapter_request_active_narrative_threads_from_context_layers_only(
    god_of_carnage_module, content_modules_root
):
    from app.runtime.session_start import start_session

    session = start_session("god_of_carnage", root_path=content_modules_root).session

    ts = NarrativeThreadSet(
        active=[
            NarrativeThreadState(
                thread_id="adapter_t",
                thread_kind="interpersonal_tension",
                status="escalating",
                intensity=4,
                related_characters=["alice", "bob"],
                related_paths=["characters.alice.relationships.bob.tension"],
                last_updated_turn=1,
            )
        ]
    )
    session.context_layers.narrative_threads = ts
    session.context_layers.short_term_context = ShortTermTurnContext(
        turn_number=1,
        scene_id=session.current_scene_id,
        guard_outcome="ACCEPTED",
    )
    session.context_layers.progression_summary = ProgressionSummary(
        first_turn_covered=1,
        last_turn_covered=1,
        total_turns_in_source=1,
        current_scene_id=session.current_scene_id,
    )
    req = build_adapter_request(session, god_of_carnage_module)
    threads = req.continuity_context.get("active_narrative_threads") if req.continuity_context else None
    assert threads
    assert threads[0]["thread_id"] == "adapter_t"
    assert threads[0]["intensity"] == 4
    assert "evidence_consequences" not in threads[0]
