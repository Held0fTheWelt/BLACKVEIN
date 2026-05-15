from __future__ import annotations

from ai_stack.expectation_variation_contracts import (
    EXPECTATION_VARIATION_BOUNDED_REVEAL,
    EXPECTATION_VARIATION_FAILURE_OVER_BUDGET,
    EXPECTATION_VARIATION_FAILURE_UNEARNED_EVENT,
    EXPECTATION_VARIATION_FAILURE_UNSELECTED_EVENT,
    EXPECTATION_VARIATION_SCHEMA_VERSION,
    normalize_expectation_variation_policy,
)
from ai_stack.expectation_variation_engine import (
    build_expectation_variation_aspect_record,
    compact_expectation_variation_context,
    derive_expectation_variation,
    validate_expectation_variation_realization,
)


def _policy(*, require_events: bool = True) -> dict[str, object]:
    return normalize_expectation_variation_policy(
        {
            "enabled": True,
            "require_structured_events": require_events,
            "max_variation_units_per_turn": 1,
            "allowed_variation_types": [
                EXPECTATION_VARIATION_BOUNDED_REVEAL,
                "ironic_misread",
            ],
        }
    )


def test_expectation_variation_selects_bounded_event_and_validates() -> None:
    policy = _policy()
    result = derive_expectation_variation(
        scene_plan_record={"selected_scene_function": "pressure_exchange"},
        information_disclosure_target={"selected_unit_ids": ["unit_alpha"]},
        dramatic_irony_record={"selected_opportunity_ids": ["opportunity_alpha"]},
        module_runtime_policy={"expectation_variation_policy": policy},
    )

    target = result["target"]
    state = result["state"]
    compact = compact_expectation_variation_context(target)
    variation_id = target["selected_variation_ids"][0]
    validation = validate_expectation_variation_realization(
        expectation_variation_target=target,
        expectation_variation_state=state,
        structured_output={
            "expectation_variation_events": [
                {
                    "variation_id": variation_id,
                    "variation_type": target["selected_variation_types"][0],
                    "source_refs": target["required_setup_refs"],
                }
            ]
        },
    )
    aspect = build_expectation_variation_aspect_record(
        target=target,
        state=state,
        validation=validation,
        policy=policy,
        source="validator",
    )

    assert target["schema_version"] == EXPECTATION_VARIATION_SCHEMA_VERSION
    assert target["selected_variation_types"] == [EXPECTATION_VARIATION_BOUNDED_REVEAL]
    assert compact["selected_variation_ids"] == [variation_id]
    assert "unit_alpha" in str(compact)
    assert validation["status"] == "approved"
    assert validation["contract_pass"] is True
    assert aspect["status"] == "passed"
    assert aspect["selected"]["selected_variation_ids"] == [variation_id]


def test_expectation_variation_rejects_unselected_or_unearned_events() -> None:
    policy = _policy()
    result = derive_expectation_variation(
        information_disclosure_target={"selected_unit_ids": ["unit_alpha"]},
        module_runtime_policy={"expectation_variation_policy": policy},
    )
    target = result["target"]
    state = result["state"]
    over_budget = validate_expectation_variation_realization(
        expectation_variation_target=target,
        expectation_variation_state=state,
        structured_output={
            "expectation_variation_events": [
                {
                    "variation_id": target["selected_variation_ids"][0],
                    "variation_type": target["selected_variation_types"][0],
                    "source_refs": target["required_setup_refs"],
                },
                {
                    "variation_id": "expectation_variation:other",
                    "variation_type": "new_world_branch",
                    "source_refs": [],
                },
            ]
        },
    )

    assert over_budget["contract_pass"] is False
    assert EXPECTATION_VARIATION_FAILURE_OVER_BUDGET in over_budget["failure_codes"]
    assert EXPECTATION_VARIATION_FAILURE_UNSELECTED_EVENT in over_budget["failure_codes"]
    assert EXPECTATION_VARIATION_FAILURE_UNEARNED_EVENT in over_budget["failure_codes"]


def test_expectation_variation_applies_prior_cooldown() -> None:
    policy = _policy(require_events=False)
    first = derive_expectation_variation(
        information_disclosure_target={"selected_unit_ids": ["unit_alpha"]},
        module_runtime_policy={"expectation_variation_policy": policy},
    )
    second = derive_expectation_variation(
        information_disclosure_target={"selected_unit_ids": ["unit_alpha"]},
        prior_expectation_variation_state=first["state"],
        module_runtime_policy={"expectation_variation_policy": policy},
    )

    assert first["target"]["selected_variation_ids"]
    assert second["target"]["selected_variation_ids"] == []
    assert second["state"]["cooldown_blocked_ids"] == first["target"]["selected_variation_ids"]
