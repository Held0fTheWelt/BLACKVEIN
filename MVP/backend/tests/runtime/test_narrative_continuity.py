"""Multi-turn coherence and narrative progression grounding tests."""

from __future__ import annotations

from datetime import datetime, timezone

from app.runtime.ai_turn_executor import build_adapter_request
from app.runtime.lore_direction_context import derive_lore_direction_context
from app.runtime.progression_summary import ProgressionSummary, derive_progression_summary
from app.runtime.relationship_context import derive_relationship_axis_context
from app.runtime.runtime_models import (
    ExecutionFailureReason,
    GuardOutcome,
    NarrativeCommitRecord,
)
from app.runtime.session_history import HistoryEntry, SessionHistory
from app.runtime.short_term_context import ShortTermTurnContext, build_short_term_context
from app.runtime.turn_executor import MockDecision, TurnExecutionResult


def _minimal_result(
    *,
    turn_number: int = 1,
    narrative_commit: NarrativeCommitRecord | None = None,
    updated_scene_id: str = "scene_a",
    updated_ending_id: str | None = None,
    execution_status: str = "success",
) -> TurnExecutionResult:
    return TurnExecutionResult(
        turn_number=turn_number,
        session_id="sid",
        execution_status=execution_status,
        decision=MockDecision(detected_triggers=["t_one"], narrative_text="", rationale=""),
        validation_errors=[],
        accepted_deltas=[],
        rejected_deltas=[],
        updated_canonical_state={"conflict_state": {"pressure": 1}},
        updated_scene_id=updated_scene_id,
        updated_ending_id=updated_ending_id,
        guard_outcome=GuardOutcome.ACCEPTED,
        failure_reason=ExecutionFailureReason.NONE,
        narrative_commit=narrative_commit,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_ms=1.0,
        events=[],
    )


def test_short_term_context_includes_bounded_narrative_commit_fields():
    nc = NarrativeCommitRecord(
        turn_number=2,
        prior_scene_id="scene_a",
        committed_scene_id="scene_a",
        situation_status="continue",
        committed_ending_id=None,
        accepted_delta_targets=["characters.x.y"],
        rejected_delta_targets=[],
        committed_trigger_ids=["t_one"],
        guard_outcome="ACCEPTED",
        authoritative_reason="No legal ending or legal explicit scene transition; continuing in current scene.",
        canonical_consequences=[
            "state_changed:characters.x.y",
            "scene_continue:scene_a",
        ],
        is_terminal=False,
    )
    result = _minimal_result(turn_number=2, narrative_commit=nc, updated_scene_id="scene_a")
    ctx = build_short_term_context(result, prior_scene_id="scene_a", session_state=None)
    assert ctx.situation_status == "continue"
    assert ctx.is_terminal is False
    assert "state_changed:characters.x.y" in ctx.canonical_consequences
    assert ctx.authoritative_reason is not None
    assert "continuing" in ctx.authoritative_reason.lower() or len(ctx.authoritative_reason) > 0
    assert ctx.scene_changed is False
    assert ctx.ending_reached is False


def test_history_entry_maps_short_term_narrative_fields():
    st = ShortTermTurnContext(
        turn_number=3,
        scene_id="s1",
        detected_triggers=[],
        guard_outcome="ACCEPTED",
        situation_status="continue",
        canonical_consequences=["state_changed:characters.a.b", "scene_continue:s1"],
        authoritative_reason="x" * 250,
        is_terminal=False,
    )
    he = HistoryEntry.from_short_term_context(st)
    assert he.situation_status == "continue"
    assert he.canonical_consequences
    assert he.authoritative_reason is not None
    assert len(he.authoritative_reason) <= 201
    assert he.is_terminal is False


def test_progression_same_scene_distinct_state_changes_counts():
    h = SessionHistory()
    base_kw = dict(scene_id="scene_x", guard_outcome="ACCEPTED", detected_triggers=[])
    h.add_entry(
        HistoryEntry(
            turn_number=1,
            situation_status="continue",
            canonical_consequences=["state_changed:characters.p.q", "scene_continue:scene_x"],
            **base_kw,
        )
    )
    h.add_entry(
        HistoryEntry(
            turn_number=2,
            situation_status="continue",
            canonical_consequences=["state_changed:characters.r.s", "scene_continue:scene_x"],
            **base_kw,
        )
    )
    s = derive_progression_summary(h)
    assert s.same_scene_progression_count == 2
    assert s.progression_momentum in ("developing", "resolving", "holding")
    assert s.stalled_turn_count == 0


def test_progression_same_scene_counts_trailing_contiguous_phase_only():
    """Re-entering the same scene_id must not count earlier blocks."""
    h = SessionHistory()
    base_a = dict(scene_id="scene_a", guard_outcome="ACCEPTED", detected_triggers=[])
    h.add_entry(
        HistoryEntry(
            turn_number=1,
            situation_status="continue",
            canonical_consequences=["state_changed:characters.old.one", "scene_continue:scene_a"],
            **base_a,
        )
    )
    h.add_entry(
        HistoryEntry(
            turn_number=2,
            situation_status="continue",
            canonical_consequences=["state_changed:characters.old.two", "scene_continue:scene_a"],
            **base_a,
        )
    )
    h.add_entry(
        HistoryEntry(
            turn_number=3,
            scene_id="scene_b",
            guard_outcome="ACCEPTED",
            detected_triggers=[],
            situation_status="continue",
            canonical_consequences=["scene_continue:scene_b"],
        )
    )
    h.add_entry(
        HistoryEntry(
            turn_number=4,
            situation_status="continue",
            canonical_consequences=["state_changed:characters.new.one", "scene_continue:scene_a"],
            **base_a,
        )
    )
    s = derive_progression_summary(h)
    assert s.current_scene_id == "scene_a"
    assert s.same_scene_progression_count == 1


def test_progression_stalled_repeated_signatures():
    h = SessionHistory()
    same_cons = ["state_changed:characters.a.emotional_state", "scene_continue:scene_x"]
    for tn in range(1, 5):
        h.add_entry(
            HistoryEntry(
                turn_number=tn,
                scene_id="scene_x",
                guard_outcome="ACCEPTED",
                detected_triggers=[],
                situation_status="continue",
                canonical_consequences=list(same_cons),
            )
        )
    s = derive_progression_summary(h)
    assert s.stalled_turn_count >= 2
    assert s.progression_momentum == "stalled"


def test_recent_canonical_consequences_order_newest_unique_first():
    """Newest-first unique: last-seen wins; `dup` appears last in flatten so it surfaces first."""
    h = SessionHistory()
    h.add_entry(
        HistoryEntry(
            turn_number=1,
            scene_id="a",
            guard_outcome="ACCEPTED",
            canonical_consequences=["state_changed:p1", "dup"],
        )
    )
    h.add_entry(
        HistoryEntry(
            turn_number=2,
            scene_id="a",
            guard_outcome="ACCEPTED",
            canonical_consequences=["state_changed:p2", "dup"],
        )
    )
    s = derive_progression_summary(h)
    assert s.recent_canonical_consequences[0] == "dup"
    i2 = s.recent_canonical_consequences.index("state_changed:p2")
    i1 = s.recent_canonical_consequences.index("state_changed:p1")
    assert i2 < i1


def test_consequence_frequency_sorted_deterministic():
    h = SessionHistory()
    h.add_entry(
        HistoryEntry(
            turn_number=1,
            scene_id="a",
            guard_outcome="ACCEPTED",
            canonical_consequences=["a", "b", "b"],
        )
    )
    s = derive_progression_summary(h)
    keys = list(s.consequence_frequency.keys())
    assert keys == sorted(keys, key=lambda k: (-s.consequence_frequency[k], k))


def test_relationship_salience_from_state_changed_paths_not_only_triggers():
    h = SessionHistory()
    h.add_entry(
        HistoryEntry(
            turn_number=1,
            scene_id="scene_x",
            guard_outcome="ACCEPTED",
            detected_triggers=[],
            situation_status="continue",
            canonical_consequences=[
                "state_changed:relationships.alice_bob.hostility",
            ],
        )
    )
    ctx = derive_relationship_axis_context(h)
    assert ctx.salient_axes
    ax = ctx.salient_axes[0]
    assert ("alice", "bob") == (ax.character_a, ax.character_b) or {"alice", "bob"} == {
        ax.character_a,
        ax.character_b,
    }
    assert any("state_path:" in t for t in ax.involved_in_recent_triggers)


def test_lore_direction_rationale_responds_to_progression_momentum(
    god_of_carnage_module, content_modules_root
):
    from app.runtime.session_start import start_session

    started = start_session("god_of_carnage", root_path=content_modules_root)
    session = started.session
    history = SessionHistory()
    history.add_entry(
        HistoryEntry(
            turn_number=1,
            scene_id=session.current_scene_id,
            guard_outcome="ACCEPTED",
            detected_triggers=[],
            situation_status="continue",
            canonical_consequences=["state_changed:characters.veronique.x"],
        )
    )
    rel = derive_relationship_axis_context(history)

    stalled_ps = ProgressionSummary(
        first_turn_covered=1,
        last_turn_covered=4,
        total_turns_in_source=4,
        current_scene_id=session.current_scene_id,
        session_phase="early",
        progression_momentum="stalled",
        stalled_turn_count=3,
        recent_canonical_consequences=["state_changed:characters.veronique.x"],
    )
    resolving_ps = stalled_ps.model_copy(
        update={
            "progression_momentum": "resolving",
            "stalled_turn_count": 0,
            "same_scene_progression_count": 3,
            "ending_reached": False,
        }
    )

    lore_stalled = derive_lore_direction_context(
        god_of_carnage_module,
        session.current_scene_id,
        history,
        stalled_ps,
        rel,
    )
    lore_resolving = derive_lore_direction_context(
        god_of_carnage_module,
        session.current_scene_id,
        history,
        resolving_ps,
        rel,
    )
    assert "momentum=stalled" in lore_stalled.selection_rationale
    assert "momentum=resolving" in lore_resolving.selection_rationale
    assert "approaching_resolution" in lore_resolving.selection_rationale
    assert len(lore_stalled.selected_units) <= 15
    assert len(lore_resolving.selected_units) <= 15


def test_build_adapter_request_includes_continuity_without_diagnostic_blobs(
    god_of_carnage_module, content_modules_root
):
    from app.runtime.session_start import start_session

    session = start_session("god_of_carnage", root_path=content_modules_root).session
    st = ShortTermTurnContext(
        turn_number=1,
        scene_id=session.current_scene_id,
        detected_triggers=["alpha"],
        guard_outcome="ACCEPTED",
        situation_status="continue",
        canonical_consequences=["state_changed:characters.x.y"],
        authoritative_reason="reason",
        is_terminal=False,
        execution_result_full={"should_not": "appear"},
        ai_decision_log_full={"also_not": "here"},
    )
    session.context_layers.short_term_context = st
    session.context_layers.progression_summary = ProgressionSummary(
        first_turn_covered=1,
        last_turn_covered=1,
        total_turns_in_source=1,
        current_scene_id=session.current_scene_id,
        progression_momentum="holding",
    )
    session.context_layers.relationship_axis_context = None
    session.context_layers.lore_direction_context = None

    req = build_adapter_request(session, god_of_carnage_module, operator_input="Hello.")
    assert req.input_interpretation is not None
    assert req.continuity_context is not None
    st_out = req.continuity_context.get("short_term_turn_context") or {}
    assert "execution_result_full" not in st_out
    assert "ai_decision_log_full" not in st_out
    assert st_out.get("situation_status") == "continue"
    assert "progression_summary" in req.continuity_context
    assert "active_narrative_threads" in req.continuity_context
    assert isinstance(req.continuity_context["active_narrative_threads"], list)


def test_system_error_short_term_leaves_narrative_fields_empty():
    result = _minimal_result(
        turn_number=1,
        narrative_commit=None,
        execution_status="system_error",
        updated_scene_id="scene_a",
    )
    result.guard_outcome = GuardOutcome.STRUCTURALLY_INVALID
    ctx = build_short_term_context(result, prior_scene_id="scene_a")
    assert ctx.situation_status == ""
    assert ctx.canonical_consequences == []
    assert ctx.authoritative_reason is None
    assert ctx.is_terminal is False
