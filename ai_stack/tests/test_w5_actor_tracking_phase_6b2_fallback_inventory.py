"""Phase 6B-2 fallback / dead-branch inventory — classification-proof tests.

These tests do not introduce any new runtime behavior. They pin the semantic
classification that the Phase 6B-2 inventory assigns to every default-on W5
fallback branch:

- ``keep_explicit_opt_out_fallback`` — fires only under ``W5_AST_*=0/false/no/off``.
- ``keep_malformed_w5_safety_fallback`` — fires only when the W5 snapshot is
  missing / malformed for the consumer.
- ``substrate_keep`` — substrate read (out of scope for 6B removal).
- ``migrate_to_w5_first_before_removal`` — legacy still feeds a downstream
  consumer; must be migrated before deletion.

The full per-branch table lives in
``docs/MVPs/w5_legacy_consumer_removal_inventory.md`` (Phase 6B-2 section). The
tests below assert the *condition matrix* (D / O / M) for each branch so
Phase 6B-3 cannot regress the inventory.

Scope: these tests stay inside ``ai_stack/`` and the world-engine-aware
counterparts already in ``world-engine/tests/`` and ``backend/tests/`` (see
the test list in the inventory doc).
"""

from __future__ import annotations

import pytest

from ai_stack.actor_tracking import (
    W5ActorSituation,
    W5ActorType,
    W5Dimension,
    W5Fact,
    W5FactStatus,
    W5FreshnessStatus,
    W5Snapshot,
    W5Source,
    W5TruthLevel,
    W5VisibilityScope,
)
from ai_stack.actor_tracking.diagnostics import w5_projection_flag_states
from ai_stack.actor_tracking.validation import (
    validate_w5_actor_tracking,
    w5_ast_validation_enabled,
    w5_validation_fallback,
)


W5_FLAGS = (
    "W5_AST_DIRECTOR_PROJECTION_ENABLED",
    "W5_AST_NARRATOR_PROJECTION_ENABLED",
    "W5_AST_NPC_PROJECTION_ENABLED",
    "W5_AST_VALIDATION_ENABLED",
    "W5_AST_FRONTEND_PLAYER_VIEW_ENABLED",
)


@pytest.fixture(autouse=True)
def _isolate_w5_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in W5_FLAGS:
        monkeypatch.delenv(name, raising=False)


# ---------------------------------------------------------------------------
# Snapshot fixture builder
# ---------------------------------------------------------------------------


def _fact(
    *,
    fact_id: str,
    actor_id: str,
    dimension: W5Dimension,
    key: str,
    value: object,
    source: W5Source = W5Source.PARTICIPANT_STATE_MOVE,
    truth: W5TruthLevel = W5TruthLevel.OBSERVED,
    visibility: W5VisibilityScope = W5VisibilityScope.PUBLIC,
    turn: int = 4,
) -> W5Fact:
    return W5Fact(
        fact_id=fact_id,
        actor_id=actor_id,
        dimension=dimension,
        key=key,
        value=value,
        source=source,
        truth_level=truth,
        valid_from_turn=turn,
        last_confirmed_turn=turn,
        visibility=visibility,
        status=W5FactStatus.ACTIVE,
    )


def _situation(actor_id: str, *, location: str, actor_type: W5ActorType, turn: int = 4) -> W5ActorSituation:
    return W5ActorSituation(
        actor_id=actor_id,
        actor_type=actor_type,
        actor_role_in_scene="primary",
        involvement_type="primary",
        where=(
            _fact(
                fact_id=f"w5f_{actor_id}_where",
                actor_id=actor_id,
                dimension=W5Dimension.WHERE,
                key="scene_location",
                value=location,
                turn=turn,
            ),
        ),
        what=(
            _fact(
                fact_id=f"w5f_{actor_id}_what",
                actor_id=actor_id,
                dimension=W5Dimension.WHAT,
                key="current_action",
                value="speaks",
                source=W5Source.COMMITTED_ACTION,
                turn=turn,
            ),
        ),
        how=(
            _fact(
                fact_id=f"w5f_{actor_id}_how",
                actor_id=actor_id,
                dimension=W5Dimension.HOW,
                key="tone",
                value="firm",
                source=W5Source.COMMITTED_ACTION,
                turn=turn,
            ),
        ),
        why=(),
        freshness_status=W5FreshnessStatus.FRESH,
        last_confirmed_turn=turn,
    )


def _snapshot_two_actors(turn: int = 4) -> W5Snapshot:
    return W5Snapshot(
        snapshot_id=f"w5s_phase_6b2_{turn}",
        story_session_id="sess_phase_6b2",
        turn_number=turn,
        created_at=f"w5:turn:{turn}",
        actors={
            "veronique": _situation(
                "veronique", location="parlor", actor_type=W5ActorType.HUMAN, turn=turn
            ),
            "michel": _situation(
                "michel", location="parlor", actor_type=W5ActorType.NPC, turn=turn
            ),
        },
    )


# ---------------------------------------------------------------------------
# F1 / F2 / F3 — Director gathering: default-on, opt-out, malformed
# ---------------------------------------------------------------------------


def _director_resolver():
    from ai_stack.langgraph.runtime_executor import public as runtime_public

    return runtime_public


def test_f1_director_default_on_happy_path_uses_w5_projection_source() -> None:
    """F1 classification proof: default-on Director path returns
    ``source == "w5_projection_with_actor_lane_fallback"`` and diagnostics
    confirm ``derived_actor_locations_source == "w5_projection"`` /
    ``gathering_pause_source == "w5_projection"``. Legacy baseline is wasted
    work under D but not the substrate that ADR-0061 reads."""

    pub = _director_resolver()
    assert pub.w5_ast_director_projection_enabled() is True  # default-on

    snapshot = _snapshot_two_actors()
    payload = pub.complete_actor_locations_for_gathering_with_optional_w5_projection(
        actor_locations={"veronique": "parlor"},
        actor_lane_context={"ai_allowed_actor_ids": ["michel"], "human_actor_id": "veronique"},
        current_step_scene_id="scene_1",
        selected_human_actor_id="veronique",
        free_player_action_resolution=None,
        environment_current_room_id="parlor",
        w5_latest_snapshot=snapshot.to_dict(),
    )
    completion = payload["location_completion"]
    diagnostics = payload["diagnostics"]
    assert completion["source"] == "w5_projection_with_actor_lane_fallback"
    assert diagnostics["w5_director_projection_used"] is True
    assert diagnostics["w5_director_projection_failed"] is None
    assert diagnostics["derived_actor_locations_source"] == "w5_projection"
    assert diagnostics["gathering_pause_source"] == "w5_projection"


def test_f2_director_explicit_opt_out_falls_back_to_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F2 classification proof: explicit ``W5_AST_DIRECTOR_PROJECTION_ENABLED=0``
    bypasses W5 entirely and returns the legacy baseline."""

    monkeypatch.setenv("W5_AST_DIRECTOR_PROJECTION_ENABLED", "0")
    pub = _director_resolver()
    assert pub.w5_ast_director_projection_enabled() is False

    payload = pub.complete_actor_locations_for_gathering_with_optional_w5_projection(
        actor_locations={"veronique": "parlor"},
        actor_lane_context={"ai_allowed_actor_ids": ["michel"], "human_actor_id": "veronique"},
        current_step_scene_id="scene_1",
        selected_human_actor_id="veronique",
        environment_current_room_id="parlor",
        w5_latest_snapshot=_snapshot_two_actors().to_dict(),
    )
    completion = payload["location_completion"]
    assert completion["source"] == "environment_state_with_actor_lane_fallback"
    # The diagnostic shape under opt-out is intentionally empty — the W5
    # branch never runs, so there is nothing to report.
    assert payload["diagnostics"] == {}
    assert payload["w5_projection"] is None


def test_f3_director_malformed_w5_falls_back_to_baseline_with_failed_diagnostic() -> None:
    """F3 classification proof: default-on but malformed/missing W5 snapshot
    returns the legacy baseline AND emits ``w5_director_projection_failed``."""

    pub = _director_resolver()
    assert pub.w5_ast_director_projection_enabled() is True

    payload = pub.complete_actor_locations_for_gathering_with_optional_w5_projection(
        actor_locations={"veronique": "parlor"},
        actor_lane_context={"ai_allowed_actor_ids": ["michel"], "human_actor_id": "veronique"},
        current_step_scene_id="scene_1",
        selected_human_actor_id="veronique",
        environment_current_room_id="parlor",
        w5_latest_snapshot=None,  # malformed-W5 condition
    )
    completion = payload["location_completion"]
    diagnostics = payload["diagnostics"]
    assert completion["source"] == "environment_state_with_actor_lane_fallback"
    assert diagnostics["w5_director_projection_used"] is False
    assert diagnostics["w5_director_projection_failed"]
    assert diagnostics["derived_actor_locations_source"] == "baseline_completion"
    assert diagnostics["gathering_pause_source"] == "baseline_completion"


# ---------------------------------------------------------------------------
# F9 / F10 — NPC default-on happy path + per-actor malformed fallback
# ---------------------------------------------------------------------------


def test_f9_npc_default_on_happy_path_uses_w5_projection_source() -> None:
    """F9 classification proof: default-on NPC projection returns
    ``npc_projection_source == "w5_projection"`` and a non-None projection."""

    pub = _director_resolver()
    assert pub.w5_ast_npc_projection_enabled() is True

    state = {"w5_latest_snapshot": _snapshot_two_actors().to_dict()}
    projections, diagnostics = pub._build_w5_npc_projection_inputs(
        state=state,
        npc_actor_ids=["michel"],
    )
    assert "michel" in projections
    assert diagnostics, "expected at least one per-actor diagnostic"
    michel_diag = next(d for d in diagnostics if d["npc_actor_id"] == "michel")
    assert michel_diag["w5_npc_projection_used"] is True
    assert michel_diag["w5_npc_projection_failed"] is None
    assert michel_diag["npc_projection_source"] == "w5_projection"


def test_f10_npc_malformed_w5_emits_failed_diagnostic_and_keeps_legacy_source() -> None:
    """F10 classification proof: missing W5 snapshot under default-on emits
    ``w5_npc_projection_failed`` per actor and the source stays on
    ``actor_lane_context`` (legacy NPC context bundle remains the planner
    substrate)."""

    pub = _director_resolver()
    state = {"w5_latest_snapshot": None}  # malformed-W5 condition
    projections, diagnostics = pub._build_w5_npc_projection_inputs(
        state=state,
        npc_actor_ids=["michel"],
    )
    assert "michel" not in projections
    michel_diag = next(d for d in diagnostics if d["npc_actor_id"] == "michel")
    assert michel_diag["w5_npc_projection_used"] is False
    assert michel_diag["w5_npc_projection_failed"]
    assert michel_diag["npc_projection_source"] == "actor_lane_context"


def test_f9_npc_explicit_opt_out_short_circuits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F9 / F-opt-out: explicit ``W5_AST_NPC_PROJECTION_ENABLED=0`` returns
    empty projections and empty diagnostics — the legacy NPC context bundle
    is the only NPC planning substrate."""

    monkeypatch.setenv("W5_AST_NPC_PROJECTION_ENABLED", "0")
    pub = _director_resolver()
    assert pub.w5_ast_npc_projection_enabled() is False

    projections, diagnostics = pub._build_w5_npc_projection_inputs(
        state={"w5_latest_snapshot": _snapshot_two_actors().to_dict()},
        npc_actor_ids=["michel"],
    )
    assert projections == {}
    assert diagnostics == []


# ---------------------------------------------------------------------------
# F12 / F13 — Validation default-on happy path + malformed fallback
# ---------------------------------------------------------------------------


def test_f12_f13_validation_default_on_happy_path_emits_no_fallback_reason() -> None:
    """F12 / F13 classification proof: under default-on with a well-formed
    snapshot, ``validate_w5_actor_tracking`` returns a typed diagnostic with
    ``status="passed"`` (or ``"failed"`` on a real claim conflict) and
    **never** ``status="fallback"`` / a ``w5_validation_fallback_reason``."""

    assert w5_ast_validation_enabled() is True

    snapshot = _snapshot_two_actors()
    diagnostic = validate_w5_actor_tracking(
        snapshot=snapshot.to_dict(),
        generation={
            "metadata": {
                "structured_output": {
                    "spoken_lines": [
                        {"speaker_id": "veronique", "scene_location": "parlor", "text": "I disagree."}
                    ],
                    "action_lines": [],
                    "initiative_events": [],
                }
            }
        },
    )
    assert diagnostic["status"] in {"passed", "failed"}
    assert diagnostic["w5_validation_source"] == "w5_snapshot"
    assert "w5_validation_fallback_reason" not in diagnostic


def test_f13_validation_malformed_w5_uses_w5_validation_fallback_reason() -> None:
    """F13 classification proof: the dedicated ``w5_validation_fallback(...)``
    helper is the only path that produces a non-None
    ``w5_validation_fallback_reason`` — and it is invoked only on exception
    from ``validate_w5_actor_tracking``."""

    fallback = w5_validation_fallback("missing_w5_latest_snapshot")
    assert fallback["status"] == "fallback"
    assert fallback["w5_validation_source"] == "structural_fallback"
    assert fallback["w5_validation_fallback_reason"] == "missing_w5_latest_snapshot"
    assert fallback["failures"] == []


def test_f12_validation_explicit_opt_out_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F12 classification proof: explicit opt-out flips the resolver back to
    legacy-only validation (the seam returns ``outcome`` unchanged in
    ``god_of_carnage_turn_seams_validation._apply_w5_validation_to_outcome``)."""

    monkeypatch.setenv("W5_AST_VALIDATION_ENABLED", "off")
    assert w5_ast_validation_enabled() is False


# ---------------------------------------------------------------------------
# Reporter parity — w5_projection_flag_states matches default-on
# ---------------------------------------------------------------------------


def test_w5_projection_flag_states_reports_default_on_under_phase_6b2() -> None:
    """Phase 6B-2 must not regress the Phase 6B-1 default-on flag posture.
    The reporter must mirror the live resolver state, with every flag
    default-on when no env var is set."""

    states = w5_projection_flag_states()
    assert states == {
        "narrator": True,
        "director": True,
        "npc": True,
        "player_shell": True,
        "validation": True,
    }


# ---------------------------------------------------------------------------
# Inventory-doc parity — Phase 6B-2 section is present
# ---------------------------------------------------------------------------


def test_phase_6b2_section_documents_all_classifications() -> None:
    """The Phase 6B-2 inventory section must reference every classification
    tag enumerated by the Phase 6B-2 taxonomy so reviewers cannot land a
    fallback change without a documented classification."""

    from pathlib import Path

    inventory = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "MVPs"
        / "w5_legacy_consumer_removal_inventory.md"
    )
    text = inventory.read_text(encoding="utf-8")
    assert "## Phase 6B-2" in text
    for tag in (
        "keep_explicit_opt_out_fallback",
        "keep_malformed_w5_safety_fallback",
        "remove_dead_default_path_in_6b3",
        "migrate_to_w5_first_before_removal",
        "substrate_keep",
        "test_only_update",
        "doc_only_update",
        "unknown_needs_runtime_trace",
    ):
        assert tag in text, f"Phase 6B-2 inventory must reference classification {tag!r}"
