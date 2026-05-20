from __future__ import annotations

from ai_stack.capabilities.capability_selector import (
    CAP_ACTION_RESOLUTION,
    CAP_CALLBACK_WEB,
    CAP_CONSEQUENCE_CASCADE,
    CAP_DRAMATIC_IRONY,
    CAP_ENVIRONMENT_STATE,
    CAP_GENRE_AWARENESS,
    CAP_INFORMATION_DISCLOSURE,
    CAP_LONG_HORIZON_FORECAST,
    CAP_NARRATOR_AUTHORITY,
    CAP_NPC_AGENCY,
    CAP_PLAYER_INTENT_INFERENCE,
    CAP_SCENE_ENERGY,
    CAP_SENSORY_CONTEXT,
    CAP_SILENCE_NEGATIVE_SPACE,
    CAP_THEMATIC_TRACKING,
    CAP_VOICE_CONSISTENCY,
    validate_semantic_capability_name,
)
from ai_stack.runtime_aspect_ledger import (
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_COMMIT,
    ASPECT_NPC_AGENCY,
    ASPECT_VALIDATION,
    initialize_runtime_aspect_ledger,
    make_aspect_record,
    set_aspect_record,
)


def _opening_projection() -> dict:
    ledger = initialize_runtime_aspect_ledger(
        session_id="selector-opening",
        module_id="example_module",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    return ledger["runtime_intelligence_projection"]["capability_selection"]


def test_opening_runtime_projection_contains_capability_selection() -> None:
    projection = _opening_projection()

    assert projection["turn_kind"] == "opening"
    assert projection["active_actor"] == "narrator"
    assert projection["selected"] == [
        CAP_NARRATOR_AUTHORITY,
        CAP_SCENE_ENERGY,
        CAP_ENVIRONMENT_STATE,
        CAP_INFORMATION_DISCLOSURE,
        CAP_VOICE_CONSISTENCY,
    ]
    assert projection["observed_only"] == [
        CAP_THEMATIC_TRACKING,
        CAP_CALLBACK_WEB,
        CAP_SENSORY_CONTEXT,
        CAP_GENRE_AWARENESS,
    ]
    assert projection["budget"]["max_enforced"] == 5


def test_opening_runtime_projection_is_local_only() -> None:
    projection = _opening_projection()

    assert projection["evidence_scope"] == "local_runtime_selection"
    assert projection["proof_level"] == "local_only"
    assert projection["live_or_staging_evidence"] is False
    assert projection["implemented_by_runtime"] is False
    assert projection["live_verified"] is False
    assert projection["staging_verified"] is False
    assert projection["provider_verified"] is False
    assert projection["capability_promoted"] is False


def test_opening_runtime_projection_uses_semantic_names_only() -> None:
    projection = _opening_projection()
    capability_names = [
        *projection["selected"],
        *projection["observed_only"],
        *projection["judged"],
        *projection["excluded"],
        *projection["activation_modes"],
    ]

    assert capability_names
    assert all(validate_semantic_capability_name(name) == name for name in capability_names)


def test_opening_runtime_projection_does_not_enable_npc_or_action_capabilities() -> None:
    projection = _opening_projection()

    assert CAP_NPC_AGENCY in projection["excluded"]
    assert CAP_PLAYER_INTENT_INFERENCE in projection["excluded"]
    assert CAP_ACTION_RESOLUTION in projection["excluded"]
    assert CAP_CONSEQUENCE_CASCADE in projection["excluded"]
    assert CAP_LONG_HORIZON_FORECAST in projection["excluded"]
    assert CAP_SILENCE_NEGATIVE_SPACE in projection["excluded"]
    assert CAP_DRAMATIC_IRONY in projection["excluded"]
    assert CAP_NPC_AGENCY not in projection["selected"]
    assert CAP_ACTION_RESOLUTION not in projection["selected"]


def test_player_turn_projection_selects_action_resolution_without_forecast_by_default() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="selector-player",
        module_id="example_module",
        turn_number=1,
        turn_kind="player",
        raw_player_input="I open the painted door.",
        input_kind="action",
    )
    projection = ledger["runtime_intelligence_projection"]["capability_selection"]

    assert projection["turn_kind"] == "player_input"
    assert projection["active_actor"] == "player"
    assert CAP_ACTION_RESOLUTION in projection["selected"]
    assert CAP_PLAYER_INTENT_INFERENCE in projection["selected"]
    assert CAP_LONG_HORIZON_FORECAST in projection["excluded"]
    assert projection["budget"]["heavy_forecast_allowed"] is False


def test_player_turn_projection_keeps_player_input_when_npc_agency_evidence_exists() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="selector-player-npc-evidence",
        module_id="example_module",
        turn_number=2,
        turn_kind="player",
        raw_player_input="I ask what they are hiding.",
        input_kind="speech",
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_NPC_AGENCY,
        make_aspect_record(
            applicable=True,
            status="passed",
            expected={"candidate_actor_ids": ["npc_primary"]},
            selected={"selected_private_plan_actor_ids": ["npc_primary"]},
            actual={"planned_actor_ids": ["npc_primary"]},
            source="runtime",
        ),
    )

    projection = ledger["runtime_intelligence_projection"]["capability_selection"]

    assert projection["turn_kind"] == "player_input"
    assert projection["active_actor"] == "player"
    assert CAP_PLAYER_INTENT_INFERENCE in projection["selected"]
    assert CAP_ACTION_RESOLUTION in projection["selected"]
    assert CAP_NPC_AGENCY in projection["selected"]


def test_projection_does_not_change_commit_or_readiness_status() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="selector-readiness",
        module_id="example_module",
        turn_number=1,
        turn_kind="player",
        raw_player_input="I listen at the door.",
    )

    aspects = ledger["turn_aspect_ledger"]
    assert "capability_selection" in ledger["runtime_intelligence_projection"]
    assert aspects[ASPECT_CAPABILITY_SELECTION]["status"] == "missing"
    assert aspects[ASPECT_VALIDATION]["status"] == "missing"
    assert aspects[ASPECT_COMMIT]["status"] == "missing"
