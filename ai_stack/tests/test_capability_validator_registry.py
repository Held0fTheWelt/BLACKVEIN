from __future__ import annotations

import re

from ai_stack.capability_selector import validate_semantic_capability_name
from ai_stack.capability_validator_dispatch import (
    ValidatorDispatchMode,
    build_validator_dispatch_report,
)
from ai_stack.capability_validator_plan import JUDGE_VALIDATORS, build_validator_execution_plan
from pathlib import Path

from ai_stack.capability_selector import ActiveActor, TurnKind, TurnSituation, select_capabilities
from ai_stack.capability_validator_plan import build_validator_execution_plan
from ai_stack.capability_validator_registry import (
    NORMAL_PLAYER_TURN_CAPABILITY_PLAN_VALIDATOR_IDS,
    OPENING_SCENE_CAPABILITY_PLAN_VALIDATOR_IDS,
    PLANNED_ALL_DISPATCH_IDS,
    PLANNED_JUDGE_IDS,
    build_available_semantic_validator_registry,
    build_default_semantic_validator_registry,
    build_opening_enforced_semantic_validator_registry,
    build_player_turn_enforced_semantic_validator_registry,
    build_semantic_validator_registry,
    get_turn_class_enforced_validators,
    unavailable_validator_result,
)
from ai_stack.environment_state_contracts import build_environment_model, initial_environment_state
from ai_stack.environment_state_contracts import evaluate_environment_state_contract
from ai_stack.narrator_authority_validation import evaluate_narrator_authority_contract
from ai_stack.player_turn_validator_evaluation import (
    evaluate_action_resolution_contract,
    evaluate_player_intent_contract,
)
from ai_stack.goc_seam_mirror_validator_adapters import SEAM_MIRROR_VALIDATOR_IDS
from ai_stack.npc_agency.npc_agency_contracts import normalize_npc_agency_plan
from ai_stack.tests.test_capability_validator_dispatch_plan_enforced import _opening_plan


def _scene_energy_target_contained(*, minimum_actor_response_count: int = 1) -> dict:
    return {
        "energy_level": "contained",
        "pressure_vector": "social",
        "tempo": "standard",
        "density": "focused",
        "volatility": "stable",
        "target_transition": "hold",
        "minimum_actor_response_count": minimum_actor_response_count,
    }


def _scene_energy_transition_for(target: dict) -> dict:
    return {
        "to_energy_level": target["energy_level"],
        "transition_intent": target["target_transition"],
        "allowed": True,
    }


def _npc_dispatch_context() -> dict:
    actors = {
        "primary": "veronique_vallon",
        "secondary": "michel_longstreet",
    }
    plan = normalize_npc_agency_plan(
        {
            "primary_responder_id": actors["primary"],
            "secondary_responder_ids": [actors["secondary"]],
            "npc_initiatives": [
                {"actor_id": actors["primary"], "target_actor_id": actors["secondary"], "required": True},
                {"actor_id": actors["secondary"], "target_actor_id": actors["primary"], "required": True},
            ],
        }
    )
    structured_output = {
        "narration_summary": (
            "Die Konfrontation zwischen Veronique und Michel spitzt sich zu; "
            "ein sichtbarer Machtwechsel liegt in der Luft."
        ),
        "spoken_lines": [
            {"speaker_id": row["actor_id"], "text": "Visible beat."}
            for row in plan["npc_initiatives"]
        ],
        "action_lines": [],
    }
    proposed_state_effects = [
        {
            "effect_type": "narrative_projection",
            "description": (
                "Veronique und Michel tauschen scharfe Worte; die Konfrontation "
                "zieht sich wie ein Strick um den Abend."
            ),
        }
    ]
    se = _scene_energy_target_contained()
    return {
        "module_id": "god_of_carnage",
        "turn_number": 2,
        "npc_agency_plan": plan,
        "structured_output": structured_output,
        "scene_energy_target": se,
        "scene_energy_transition": _scene_energy_transition_for(se),
        "information_disclosure_target": {"policy_enabled": False},
        "voice_profiles": [],
        "voice_validation_mode": "schema_only",
        "generation": {"success": True, "metadata": {"structured_output": structured_output}},
        "proposed_state_effects": proposed_state_effects,
        "actor_lane_context": {
            "human_actor_id": "annette_reille",
            "ai_forbidden_actor_ids": ["annette_reille"],
        },
    }


def test_default_registry_does_not_register_unavailable_validators_as_success() -> None:
    registry = build_default_semantic_validator_registry()

    assert registry == {}
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=registry,
        feature_flag_enabled=True,
    )

    assert report.actually_executed == ()
    assert set(report.validators_unavailable) == set(report.validators_would_run)


def test_registry_uses_semantic_ids_only() -> None:
    active_pi = re.compile(
        r"(?<![A-Za-z0-9])pi_\d+\b|(?<![A-Za-z0-9])pi\d+_[A-Za-z0-9_]+\b|Π\d+\b",
        re.IGNORECASE,
    )
    registry = build_available_semantic_validator_registry()

    for validator_id in registry:
        validate_semantic_capability_name(validator_id)
        assert not active_pi.search(validator_id)
    for judge_id in PLANNED_JUDGE_IDS:
        assert judge_id not in registry


def test_registry_does_not_register_judges_by_default() -> None:
    default_registry = build_default_semantic_validator_registry()
    available_registry = build_available_semantic_validator_registry()

    for judge_id in JUDGE_VALIDATORS.values():
        assert judge_id not in default_registry
        assert judge_id not in available_registry


def test_unknown_validator_reports_unavailable() -> None:
    result = unavailable_validator_result("scene_energy_contract", reason="validator_not_registered")

    assert result["available"] is False
    assert result["passed"] is False
    assert result["status"] == "unavailable"


def test_plan_enforced_with_available_registry_does_not_false_green_missing_context() -> None:
    registry = build_available_semantic_validator_registry()
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=registry,
        dispatch_context={},
        feature_flag_enabled=True,
    )

    assert "scene_energy_contract" in report.validators_unavailable
    assert "scene_energy_contract" not in report.actually_executed


def test_plan_enforced_with_populated_context_can_execute_scene_energy() -> None:
    registry = build_available_semantic_validator_registry()
    se = _scene_energy_target_contained()
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=registry,
        dispatch_context={
            "scene_energy_target": se,
            "scene_energy_transition": _scene_energy_transition_for(se),
            "structured_output": {"spoken_lines": [{"speaker_id": "narrator", "text": "A door opens."}]},
        },
        feature_flag_enabled=True,
    )

    assert "scene_energy_contract" in report.actually_executed


def test_build_semantic_validator_registry_include_flag() -> None:
    assert build_semantic_validator_registry() == {}
    available = build_semantic_validator_registry(include_available_adapters=True)
    assert "scene_energy_contract" in available
    assert available == build_available_semantic_validator_registry()


def test_opening_enforced_ids_subset_of_planned_local_validators() -> None:
    for validator_id in get_turn_class_enforced_validators("opening_scene"):
        assert validator_id in PLANNED_ALL_DISPATCH_IDS or validator_id in SEAM_MIRROR_VALIDATOR_IDS


def test_opening_registry_contains_safe_opening_enforced_adapters() -> None:
    opening_registry = build_opening_enforced_semantic_validator_registry()

    assert set(opening_registry) == set(get_turn_class_enforced_validators("opening_scene"))


def test_narrator_authority_adapter_requires_context() -> None:
    result = evaluate_narrator_authority_contract(structured_output=None, proposed_state_effects=None)

    assert result["available"] is False
    assert result["passed"] is False
    assert result["reason"] == "missing_required_context"


def test_environment_state_adapter_requires_context() -> None:
    result = evaluate_environment_state_contract(environment_state=None, module_id=None)

    assert result["available"] is False
    assert result["passed"] is False
    assert result["reason"] == "missing_required_context"


def test_narrator_authority_adapter_returns_local_only_result() -> None:
    result = evaluate_narrator_authority_contract(
        structured_output={"narration_summary": "A narrator sets the room."},
        turn_number=0,
        narrator_required=True,
    )

    assert result["available"] is True
    assert result["passed"] is True
    assert result["proof_level"] == "local_only"
    assert result["live_or_staging_evidence"] is False


def test_environment_state_adapter_returns_local_only_result() -> None:
    model = build_environment_model(module_id="god_of_carnage")
    state = initial_environment_state(module_id="god_of_carnage", environment_model=model, turn_number=0)
    result = evaluate_environment_state_contract(
        environment_state=state,
        module_id="god_of_carnage",
        environment_model=model,
        turn_number=0,
    )

    assert result["available"] is True
    assert result["passed"] is True
    assert result["proof_level"] == "local_only"
    assert result["live_or_staging_evidence"] is False


def _opening_dispatch_context() -> dict:
    module_id = "god_of_carnage"
    model = build_environment_model(module_id=module_id)
    environment_state = initial_environment_state(
        module_id=module_id,
        environment_model=model,
        turn_number=0,
    )
    structured = {
        "narration_summary": "The foyer waits in brittle calm.",
        "spoken_lines": [{"speaker_id": "narrator", "text": "The light stays low."}],
    }
    proposed = [{"effect_type": "narrative_projection", "description": "The foyer waits in brittle calm."}]
    scene_energy_target = _scene_energy_target_contained()
    return {
        "module_id": module_id,
        "turn_number": 0,
        "narrator_required": True,
        "turn_input_class": "opening",
        "structured_output": structured,
        "generation": {"success": True, "metadata": {"structured_output": structured}},
        "proposed_state_effects": proposed,
        "environment_state": environment_state,
        "environment_model": model,
        "scene_energy_target": scene_energy_target,
        "scene_energy_transition": _scene_energy_transition_for(scene_energy_target),
        "information_disclosure_target": {"policy_enabled": False},
        "voice_profiles": [],
        "actor_lane_context": {
            "human_actor_id": "annette_reille",
            "ai_forbidden_actor_ids": ["annette_reille"],
        },
    }


def test_opening_plan_enforced_executes_all_available_opening_enforced_validators() -> None:
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=build_opening_enforced_semantic_validator_registry(),
        dispatch_context=_opening_dispatch_context(),
        feature_flag_enabled=True,
    )

    assert set(report.actually_executed) == set(OPENING_SCENE_CAPABILITY_PLAN_VALIDATOR_IDS)
    assert report.execution_changed is True


def test_opening_plan_enforced_does_not_execute_excluded_validators() -> None:
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=build_opening_enforced_semantic_validator_registry(),
        dispatch_context=_opening_dispatch_context(),
        feature_flag_enabled=True,
    )

    for validator_id in (
        "npc_agency_contract",
        "player_intent_contract",
        "action_resolution_contract",
        "consequence_cascade_contract",
        "forecast_contract",
        "silence_negative_space_contract",
        "dramatic_irony_contract",
    ):
        assert validator_id in report.validators_would_skip
        assert validator_id not in report.actually_executed


def test_default_registry_remains_empty() -> None:
    assert build_default_semantic_validator_registry() == {}


def test_default_dispatch_remains_dry_run() -> None:
    report = build_validator_dispatch_report(_opening_plan())

    assert report.mode.value == "dry_run"
    assert report.execution_changed is False
    assert report.actually_executed == ()


def test_unavailable_still_does_not_false_green() -> None:
    registry = build_opening_enforced_semantic_validator_registry()
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=registry,
        dispatch_context={},
        feature_flag_enabled=True,
    )

    assert report.actually_executed == ()
    assert set(report.validators_unavailable) == set(OPENING_SCENE_CAPABILITY_PLAN_VALIDATOR_IDS)


def _player_plan():
    selection = select_capabilities(
        TurnSituation(
            turn_kind=TurnKind.PLAYER_INPUT,
            active_actor=ActiveActor.PLAYER,
            player_input_present=True,
            action_resolution_required=True,
            visible_projection_required=True,
        )
    )
    return build_validator_execution_plan(selection)


def _content_root() -> Path:
    return Path(__file__).resolve().parents[2] / "content" / "modules"


def _runtime_projection() -> dict:
    return {
        "human_actor_id": "annette_reille",
        "selected_player_role": "annette_reille",
        "npc_actor_ids": ["alain_reille", "veronique_vallon", "michel_longstreet"],
        "actor_lanes": {
            "annette_reille": "human",
            "alain_reille": "npc",
            "veronique_vallon": "npc",
            "michel_longstreet": "npc",
        },
    }


def _player_dispatch_context() -> dict:
    se_target = _scene_energy_target_contained()
    structured = {
        "narration_summary": "Die Spannung im Raum liegt wie Staub über dem Tisch.",
        "spoken_lines": [{"speaker_id": "narrator", "text": "Der Raum bleibt schwer."}],
    }
    proposed = [
        {
            "effect_type": "narrative_projection",
            "description": (
                "Die Flurhaustür fällt ins Schloss; der Weg ins Bad bleibt unausgesprochen "
                "zwischen den vier Erwachsenen."
            ),
        }
    ]
    return {
        "module_id": "god_of_carnage",
        "turn_number": 1,
        "raw_player_input": "Gehe ins Bad",
        "interpreted_input": {
            "player_input_kind": "action",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "projection_captures": {"room": "ins Bad"},
            "actor_id": "annette_reille",
        },
        "player_action_frame": {
            "actor_id": "annette_reille",
            "verb": "move",
            "action_kind": "movement",
            "target_id": "bathroom",
            "validation_surface": "authoritative_action_resolution",
        },
        "affordance_resolution": {
            "status": "allowed",
            "action_commit_policy": "commit",
            "target_id": "bathroom",
            "resolution_source": "fixture_authoritative_action_resolution",
        },
        "runtime_projection": _runtime_projection(),
        "content_modules_root": _content_root(),
        "scene_energy_target": se_target,
        "scene_energy_transition": _scene_energy_transition_for(se_target),
        "information_disclosure_target": {"policy_enabled": False},
        "voice_profiles": [],
        "structured_output": structured,
        "generation": {"success": True, "metadata": {"structured_output": structured}},
        "proposed_state_effects": proposed,
        "actor_lane_context": {
            "human_actor_id": "annette_reille",
            "ai_forbidden_actor_ids": ["annette_reille"],
        },
    }


def test_player_turn_registry_contains_safe_player_turn_enforced_adapters() -> None:
    player_registry = build_player_turn_enforced_semantic_validator_registry()

    assert set(player_registry) == set(get_turn_class_enforced_validators("normal_player_turn"))


def test_player_intent_adapter_requires_context() -> None:
    result = evaluate_player_intent_contract(interpreted_input=None)

    assert result["available"] is False
    assert result["passed"] is False
    assert result["reason"] == "missing_required_context"


def test_action_resolution_adapter_requires_context() -> None:
    result = evaluate_action_resolution_contract(
        raw_player_input=None,
        interpreted_input=None,
        module_id=None,
        runtime_projection=None,
    )

    assert result["available"] is False
    assert result["passed"] is False
    assert result["reason"] == "missing_required_context"


def test_player_intent_adapter_returns_local_only_result() -> None:
    result = evaluate_player_intent_contract(
        raw_player_input="Gehe ins Bad",
        interpreted_input={
            "player_input_kind": "action",
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
    )

    assert result["available"] is True
    assert result["passed"] is True
    assert result["proof_level"] == "local_only"
    assert result["live_or_staging_evidence"] is False


def test_action_resolution_adapter_returns_local_only_result() -> None:
    result = evaluate_action_resolution_contract(
        player_action_frame={
            "actor_id": "annette_reille",
            "verb": "move",
            "action_kind": "movement",
            "target_id": "bathroom",
            "validation_surface": "authoritative_action_resolution",
        },
        affordance_resolution={
            "status": "allowed",
            "action_commit_policy": "commit",
            "target_id": "bathroom",
            "resolution_source": "fixture_authoritative_action_resolution",
        },
    )

    assert result["available"] is True
    assert result["passed"] is True
    assert result["proof_level"] == "local_only"
    assert result["live_or_staging_evidence"] is False


def test_player_turn_plan_enforced_executes_available_player_turn_validators() -> None:
    report = build_validator_dispatch_report(
        _player_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=build_player_turn_enforced_semantic_validator_registry(),
        dispatch_context=_player_dispatch_context(),
        feature_flag_enabled=True,
    )

    assert set(report.actually_executed) == set(NORMAL_PLAYER_TURN_CAPABILITY_PLAN_VALIDATOR_IDS)
    assert report.execution_changed is True


def test_player_turn_plan_enforced_does_not_execute_excluded_validators() -> None:
    report = build_validator_dispatch_report(
        _player_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=build_player_turn_enforced_semantic_validator_registry(),
        dispatch_context=_player_dispatch_context(),
        feature_flag_enabled=True,
    )

    for validator_id in (
        "narrator_authority_contract",
        "npc_agency_contract",
        "consequence_cascade_contract",
        "forecast_contract",
        "silence_negative_space_contract",
        "dramatic_irony_contract",
    ):
        assert validator_id in report.validators_would_skip
        assert validator_id not in report.actually_executed

    assert "environment_state_contract" not in report.actually_executed
    assert "environment_state_contract" not in report.validators_would_run
