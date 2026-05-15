from __future__ import annotations

from ai_stack.improvisational_coherence_contracts import (
    IMPROV_ACCEPT,
    IMPROV_FAILURE_PLAYER_CONTRIBUTION_DROPPED,
    IMPROV_FAILURE_SCENE_ANCHOR_MISSING,
    IMPROV_FAILURE_UNBOUNDED_WORLD_EXPANSION,
    IMPROV_REDIRECT_WITH_ACKNOWLEDGEMENT,
    IMPROVISATIONAL_COHERENCE_SCHEMA_VERSION,
    normalize_improvisational_coherence_policy,
)
from ai_stack.improvisational_coherence_engine import (
    build_improvisational_coherence_aspect_record,
    compact_improvisational_coherence_context,
    derive_improvisational_coherence,
    validate_improvisational_coherence_realization,
)


def _policy(*, require_events: bool = True, min_anchor_refs: int = 2) -> dict[str, object]:
    return normalize_improvisational_coherence_policy(
        {
            "enabled": True,
            "require_structured_events": require_events,
            "min_anchor_refs": min_anchor_refs,
            "allowed_acceptance_modes": [
                IMPROV_ACCEPT,
                IMPROV_REDIRECT_WITH_ACKNOWLEDGEMENT,
            ],
            "allowed_advance_classes": ["pressure_raise", "beat_deepen"],
        }
    )


def test_improvisational_coherence_selects_bounded_target_and_validates_event() -> None:
    policy = _policy()
    result = derive_improvisational_coherence(
        player_input="Ich drehe den Vorwurf auf die kaputte Vase.",
        interpreted_input={"player_input_kind": "speech"},
        semantic_move_record={"move_type": "speech"},
        scene_plan_record={"selected_scene_function": "domestic_pressure"},
        current_scene_id="scene_alpha",
        selected_responder_set=[{"actor_id": "npc_alpha"}],
        scene_energy_target={"target_transition": "rise"},
        pacing_rhythm_target={"cadence": "press"},
        module_runtime_policy={"improvisational_coherence_policy": policy},
    )

    target = result["target"]
    compact = compact_improvisational_coherence_context(target)
    required_refs = target["required_anchor_refs"][: target["min_anchor_refs"]]
    validation = validate_improvisational_coherence_realization(
        improvisational_coherence_target=target,
        structured_output={
            "improvisational_coherence_events": [
                {
                    "contribution_id": target["contribution_id"],
                    "acceptance_mode": target["acceptance_mode"],
                    "advance_class": "pressure_raise",
                    "anchor_refs": required_refs,
                }
            ]
        },
    )
    aspect = build_improvisational_coherence_aspect_record(
        target=target,
        validation=validation,
        policy=policy,
        source="validator",
    )

    assert target["schema_version"] == IMPROVISATIONAL_COHERENCE_SCHEMA_VERSION
    assert target["policy_enabled"] is True
    assert target["min_anchor_refs"] == policy["min_anchor_refs"]
    assert compact["contribution_id"] == target["contribution_id"]
    assert "Ich drehe" not in str(compact)
    assert validation["status"] == "approved"
    assert validation["contract_pass"] is True
    assert aspect["status"] == "passed"
    assert aspect["selected"]["min_anchor_refs"] == policy["min_anchor_refs"]


def test_improvisational_coherence_rejects_missing_or_unbounded_structured_event() -> None:
    policy = _policy()
    result = derive_improvisational_coherence(
        player_input="Meta: springe an einen anderen Ort.",
        interpreted_input={"player_input_kind": "meta"},
        semantic_move_record={"move_type": "meta"},
        scene_plan_record={"selected_scene_function": "domestic_pressure"},
        current_scene_id="scene_alpha",
        module_runtime_policy={"improvisational_coherence_policy": policy},
    )
    target = result["target"]

    missing = validate_improvisational_coherence_realization(
        improvisational_coherence_target=target,
        structured_output={},
    )
    unbounded = validate_improvisational_coherence_realization(
        improvisational_coherence_target=target,
        structured_output={
            "improvisational_coherence_events": [
                {
                    "contribution_id": target["contribution_id"],
                    "acceptance_mode": "invent_new_location",
                    "advance_class": "new_world_branch",
                    "anchor_refs": [],
                }
            ]
        },
    )

    assert target["acceptance_mode"] == IMPROV_REDIRECT_WITH_ACKNOWLEDGEMENT
    assert missing["failure_codes"] == [IMPROV_FAILURE_PLAYER_CONTRIBUTION_DROPPED]
    assert IMPROV_FAILURE_UNBOUNDED_WORLD_EXPANSION in unbounded["failure_codes"]
    assert IMPROV_FAILURE_SCENE_ANCHOR_MISSING in unbounded["failure_codes"]
    assert unbounded["contract_pass"] is False
