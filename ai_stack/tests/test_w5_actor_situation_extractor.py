"""Extractor tests for W5 Actor Situation Tracker (ADR-0063).

Covers: determinism, no I/O, no mutation, committed-only OBSERVED facts,
How as first-class dimension, INFERRED Why soft-truth.
"""

from __future__ import annotations

import copy

import pytest

from ai_stack.actor_situation.extractor import (
    extract_w5_snapshot_from_committed_event,
)
from ai_stack.actor_situation.models import (
    W5Dimension,
    W5Source,
    W5TruthLevel,
)


def _committed_event(**overrides):
    base = {
        "canonical_turn_id": "ct_001",
        "turn_number": 1,
        "narrative_commit": {
            "selected_actor_id": "annette",
            "action_kind": "movement",
            "action_verb": "move_to",
            "target_actor_id": None,
        },
        "actor_turn_summary": {
            "selected_actor_id": "annette",
        },
    }
    base.update(overrides)
    return base


def _env_state_after(**overrides):
    base = {
        "schema_version": "environment_state.v1",
        "current_room_id": "foyer",
        "previous_room_id": "parlor",
        "actor_locations": {"annette": "foyer", "alain": "parlor"},
    }
    base.update(overrides)
    return base


def _actor_lane_context(**overrides):
    base = {
        "actor_lanes": {
            "annette": {
                "actor_type": "human",
                "role_in_scene": "host",
                "involvement_type": "primary",
                "manner_directive": {"tone": "guarded"},
            },
            "alain": {
                "actor_type": "npc",
                "role_in_scene": "host",
                "involvement_type": "primary",
            },
        }
    }
    base.update(overrides)
    return base


def _run_extractor(**overrides):
    defaults = dict(
        previous_snapshot=None,
        committed_event=_committed_event(),
        environment_state_after=_env_state_after(),
        director_gathering_state=None,
        free_player_action_resolution=None,
        actor_lane_context=_actor_lane_context(),
        npc_agency_simulation=None,
        character_mind_records=None,
        active_canonical_step={"step_id": "opening_004_den_arrival_positioning"},
        story_session_id="sess_w5_1",
        turn_number=1,
    )
    defaults.update(overrides)
    return extract_w5_snapshot_from_committed_event(**defaults)


def test_extractor_deterministic_for_identical_inputs() -> None:
    a = _run_extractor()
    b = _run_extractor()
    assert a == b
    assert a.snapshot_id == b.snapshot_id


def test_extractor_does_not_mutate_inputs() -> None:
    committed = _committed_event()
    env = _env_state_after()
    lane = _actor_lane_context()
    canon = {"step_id": "opening_004_den_arrival_positioning"}
    committed_snap = copy.deepcopy(committed)
    env_snap = copy.deepcopy(env)
    lane_snap = copy.deepcopy(lane)
    canon_snap = copy.deepcopy(canon)

    _run_extractor(
        committed_event=committed,
        environment_state_after=env,
        actor_lane_context=lane,
        active_canonical_step=canon,
    )

    assert committed == committed_snap
    assert env == env_snap
    assert lane == lane_snap
    assert canon == canon_snap


def test_extractor_no_io_when_called(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pure: extractor must not touch filesystem, network, or environment."""

    def _no_open(*_args, **_kwargs):
        raise AssertionError("extractor must not perform I/O (open called)")

    monkeypatch.setattr("builtins.open", _no_open)

    # network: forbid urllib.request.urlopen
    import urllib.request

    def _no_urlopen(*_args, **_kwargs):
        raise AssertionError("extractor must not perform I/O (urlopen called)")

    monkeypatch.setattr(urllib.request, "urlopen", _no_urlopen)

    snapshot = _run_extractor()
    assert snapshot.story_session_id == "sess_w5_1"


def test_observed_where_requires_committed_substrate() -> None:
    """OBSERVED where facts derive only from environment_state, never from prose."""

    snap = _run_extractor()
    where_facts = list(snap.actors["annette"].where)
    assert where_facts, "expected at least one where fact for committed actor"
    for fact in where_facts:
        assert fact.truth_level is W5TruthLevel.OBSERVED
        assert fact.source is W5Source.PARTICIPANT_STATE_MOVE
        assert fact.value == "foyer"
        assert fact.source_event_id == "ct_001"


def test_observed_what_only_when_event_committed() -> None:
    """When committed event lacks canonical_turn_id, no OBSERVED what is emitted."""

    snap_with_commit = _run_extractor()
    annette_what = snap_with_commit.actors["annette"].what
    assert any(
        f.truth_level is W5TruthLevel.OBSERVED and f.key == "current_action"
        for f in annette_what
    )

    snap_without_commit = _run_extractor(
        committed_event={"narrative_commit": {"selected_actor_id": "annette", "action_verb": "move_to"}},
    )
    observed_what = [
        f for f in snap_without_commit.actors.get("annette", _empty()).what
        if f.truth_level is W5TruthLevel.OBSERVED
    ]
    assert observed_what == [], (
        "extractor must not emit OBSERVED what facts when committed_event has no event id"
    )


def _empty():
    from ai_stack.actor_situation.models import (
        W5ActorSituation,
        W5ActorType,
        W5FreshnessStatus,
    )

    return W5ActorSituation(
        actor_id="_none_",
        actor_type=W5ActorType.NPC,
        freshness_status=W5FreshnessStatus.FRESH,
        last_confirmed_turn=0,
    )


def test_declared_what_does_not_overwrite_observed() -> None:
    """DECLARED facts must not silently overwrite OBSERVED ones for the same actor+key."""

    snap = _run_extractor(
        free_player_action_resolution={
            "selected_actor_id": "annette",
            "declared_verb": "shout",  # would conflict with OBSERVED "move_to"
            "commit_applied": False,
        },
    )
    current_actions = [
        f for f in snap.actors["annette"].what if f.key == "current_action"
    ]
    # Only the OBSERVED current_action survives; DECLARED was dropped.
    assert len(current_actions) == 1
    assert current_actions[0].truth_level is W5TruthLevel.OBSERVED
    assert current_actions[0].value == "move_to"


def test_declared_what_emitted_when_not_committed() -> None:
    snap = _run_extractor(
        committed_event={},
        free_player_action_resolution={
            "selected_actor_id": "annette",
            "declared_verb": "shout",
            "commit_applied": False,
        },
    )
    current_actions = [
        f for f in snap.actors["annette"].what if f.key == "current_action"
    ]
    assert len(current_actions) == 1
    assert current_actions[0].truth_level is W5TruthLevel.DECLARED
    assert current_actions[0].source is W5Source.FREE_PLAYER_ACTION_RESOLUTION


def test_how_is_first_class_dimension_not_collapsed_into_what() -> None:
    """How signals must appear under dimension='how', not folded into what."""

    snap = _run_extractor(
        committed_event=_committed_event(
            how_signals={"tone": "icy", "intensity": "high"},
            actor_id="annette",
        ),
    )
    how_facts = list(snap.actors["annette"].how)
    assert any(f.key == "tone" and f.value == "icy" for f in how_facts)
    assert any(f.key == "intensity" and f.value == "high" for f in how_facts)
    for fact in how_facts:
        assert fact.dimension is W5Dimension.HOW
    # And critically, none of these appear in `what`.
    for fact in snap.actors["annette"].what:
        assert fact.key not in {"tone", "intensity"}


def test_how_observed_only_with_committed_event_id() -> None:
    snap = _run_extractor(
        committed_event={
            "how_signals": {"tone": "icy"},
            "actor_id": "annette",
        },
    )
    annette = snap.actors.get("annette")
    if annette is None:
        return
    for fact in annette.how:
        assert fact.truth_level is not W5TruthLevel.OBSERVED


def test_director_assigned_how_from_actor_lane() -> None:
    snap = _run_extractor()
    annette_how = list(snap.actors["annette"].how)
    tone_facts = [f for f in annette_how if f.key == "tone"]
    assert tone_facts, "expected actor lane manner_directive to produce HOW fact"
    director_tone = next(
        (f for f in tone_facts if f.truth_level is W5TruthLevel.DIRECTOR_ASSIGNED), None
    )
    assert director_tone is not None
    assert director_tone.source is W5Source.DIRECTOR_COMPOSITION


def test_inferred_why_from_character_mind_records() -> None:
    snap = _run_extractor(
        character_mind_records={"annette": {"motive": "protect_son", "goal": "force_apology"}},
    )
    why_facts = list(snap.actors["annette"].why)
    assert any(f.key == "motive" and f.value == "protect_son" for f in why_facts)
    for fact in why_facts:
        assert fact.dimension is W5Dimension.WHY
        # Soft-truth invariant: never OBSERVED from character_mind / npc_agency.
        assert fact.truth_level in (W5TruthLevel.INFERRED, W5TruthLevel.DIRECTOR_ASSIGNED)
        assert fact.truth_level is not W5TruthLevel.OBSERVED


def test_inferred_why_from_npc_agency_simulation() -> None:
    snap = _run_extractor(
        npc_agency_simulation={
            "plans": {"alain": {"why": {"motive": "save_face", "goal": "deflect_blame"}}}
        },
    )
    why_facts = list(snap.actors["alain"].why)
    assert any(f.key == "motive" and f.value == "save_face" for f in why_facts)
    for fact in why_facts:
        assert fact.truth_level is W5TruthLevel.INFERRED
        assert fact.source is W5Source.NPC_AGENCY_SIMULATION


def test_souffleuse_and_narrator_never_produce_observed_facts() -> None:
    """Phase 1: souffleuse/narrator composition are projection-lane only.

    The extractor does not consume these sources, so a committed event that
    only contains narrator/souffleuse prose must not produce OBSERVED facts.
    """

    snap = _run_extractor(
        committed_event={
            "canonical_turn_id": "ct_002",
            "visible_output_bundle": {
                "scene_blocks": [
                    {"kind": "narrator", "text": "Annette stares at the door."},
                    {"kind": "souffleuse", "text": "Du atmest tief durch."},
                ]
            },
        },
        environment_state_after={},
        actor_lane_context=None,
    )
    for actor in snap.actors.values():
        for fact in (*actor.where, *actor.what, *actor.how, *actor.why):
            assert fact.source not in (
                W5Source.SOUFFLEUSE,
                W5Source.NARRATOR_COMPOSITION,
            ), "souffleuse / narrator must never appear as a fact source"


def test_admin_override_never_produces_observed() -> None:
    """admin_override source must never produce OBSERVED facts.

    Extractor does not consume admin_override directly in Phase 1, but if it
    did, the invariant must hold. We assert by reading every produced fact.
    """

    snap = _run_extractor()
    for actor in snap.actors.values():
        for fact in (*actor.where, *actor.what, *actor.how, *actor.why):
            if fact.source is W5Source.ADMIN_OVERRIDE:
                assert fact.truth_level is not W5TruthLevel.OBSERVED


def test_snapshot_appendonly_supersession_conflict_recorded() -> None:
    """DECLARED/INFERRED contradicting prior OBSERVED is recorded as a conflict."""

    # Turn 1: OBSERVED snapshot.
    first = _run_extractor(turn_number=1)

    # Turn 2: prior snapshot's OBSERVED current_action is "move_to";
    # this turn supplies only a DECLARED current_action.
    second = _run_extractor(
        previous_snapshot=first,
        committed_event={},  # no committed event id -> no OBSERVED what
        environment_state_after={},
        actor_lane_context=None,
        free_player_action_resolution={
            "selected_actor_id": "annette",
            "declared_verb": "shout",
            "commit_applied": False,
        },
        turn_number=2,
    )
    # The new DECLARED fact would weaken OBSERVED — must record a conflict.
    assert any(
        c.actor_id == "annette" and c.dimension is W5Dimension.WHAT
        for c in second.conflicts
    )
