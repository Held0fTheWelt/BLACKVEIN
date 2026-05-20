from __future__ import annotations

from ai_stack.contracts.information_disclosure_contracts import (
    INFORMATION_DISCLOSURE_POLICY_VERSION,
    normalize_information_disclosure_policy,
)
from ai_stack.story_runtime.narrative.information_disclosure_engine import (
    derive_information_disclosure,
    validate_information_disclosure_realization,
)


def _policy(*, required: bool = False) -> dict:
    return normalize_information_disclosure_policy(
        {
            "enabled": True,
            "default_commit_impact": "recover",
            "require_structured_events": required,
            "max_visible_units_per_turn": 1,
            "units": [
                {
                    "id": "unit_alpha",
                    "stage": "hint",
                    "allowed_modes": ["visible_hint"],
                    "unlock_conditions": {"scene_functions_any": ["probe"]},
                    "semantic_profile": {"hint": "pressure omission"},
                },
                {
                    "id": "unit_beta",
                    "stage": "confirm",
                    "allowed_modes": ["confirmation"],
                    "unlock_conditions": {"scene_functions_any": ["confirm"]},
                },
            ],
        }
    )


def test_information_disclosure_policy_normalizes_units() -> None:
    policy = _policy()

    assert policy["schema_version"] == INFORMATION_DISCLOSURE_POLICY_VERSION
    assert policy["enabled"] is True
    assert [row["id"] for row in policy["units"]] == ["unit_alpha", "unit_beta"]
    assert policy["units"][0]["semantic_profile"]


def test_information_disclosure_derivation_selects_from_policy_context() -> None:
    result = derive_information_disclosure(
        scene_plan_record={"selected_scene_function": "probe"},
        semantic_move_record={"move_type": "ask"},
        module_runtime_policy={"information_disclosure_policy": _policy()},
    )

    target = result["target"]
    assert target["policy_enabled"] is True
    assert target["selected_unit_ids"] == ["unit_alpha"]
    assert target["withheld_unit_ids"] == ["unit_beta"]
    assert target["max_visible_units_per_turn"] == 1


def test_information_disclosure_validation_rejects_forbidden_unit() -> None:
    result = derive_information_disclosure(
        scene_plan_record={"selected_scene_function": "probe"},
        module_runtime_policy={"information_disclosure_policy": _policy(required=True)},
    )

    validation = validate_information_disclosure_realization(
        information_disclosure_target=result["target"],
        structured_output={
            "disclosure_events": [
                {"unit_id": "unit_beta", "stage": "confirm", "mode": "confirmation"}
            ]
        },
    )

    assert validation["status"] == "rejected"
    assert "information_disclosure_forbidden_unit" in validation["failure_codes"]
    assert validation["actual"]["forbidden_event_unit_ids"] == ["unit_beta"]


def test_information_disclosure_validation_accepts_selected_event() -> None:
    result = derive_information_disclosure(
        scene_plan_record={"selected_scene_function": "probe"},
        module_runtime_policy={"information_disclosure_policy": _policy(required=True)},
    )

    validation = validate_information_disclosure_realization(
        information_disclosure_target=result["target"],
        structured_output={
            "disclosure_events": [
                {"unit_id": "unit_alpha", "stage": "hint", "mode": "visible_hint"}
            ]
        },
    )

    assert validation["status"] == "approved"
    assert validation["contract_pass"] is True
    assert validation["actual"]["budget_used"] == 1
