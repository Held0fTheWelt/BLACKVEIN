from __future__ import annotations

from ai_stack.capability_validator_plan import (
    JUDGE_VALIDATORS,
    LOCAL_VALIDATORS,
    OBSERVER_DIAGNOSTICS,
)
from ai_stack.capability_validator_registry import (
    PLANNED_ALL_DISPATCH_IDS,
    STATUS_JUDGE_ONLY,
    STATUS_OBSERVER_ONLY,
    VALIDATOR_REGISTRY_INVENTORY,
    inventory_rows_by_validator_id,
)


def test_registry_inventory_matches_planned_local_validator_ids() -> None:
    by_id = inventory_rows_by_validator_id()

    for capability, validator_id in LOCAL_VALIDATORS.items():
        assert validator_id in by_id, validator_id
        assert by_id[validator_id].capability == capability

    for capability, diagnostic_id in OBSERVER_DIAGNOSTICS.items():
        assert diagnostic_id in by_id, diagnostic_id
        assert by_id[diagnostic_id].capability == capability


def test_registry_inventory_covers_all_planned_dispatch_ids_except_judges() -> None:
    by_id = inventory_rows_by_validator_id()
    local_and_observer = set(LOCAL_VALIDATORS.values()) | set(OBSERVER_DIAGNOSTICS.values())

    assert set(by_id) == local_and_observer
    assert set(PLANNED_ALL_DISPATCH_IDS) == local_and_observer | set(JUDGE_VALIDATORS.values())


def test_observer_diagnostics_marked_non_blocking() -> None:
    by_id = inventory_rows_by_validator_id()

    for diagnostic_id in OBSERVER_DIAGNOSTICS.values():
        row = by_id[diagnostic_id]
        assert row.current_status == STATUS_OBSERVER_ONLY
        assert row.blocking_or_non_blocking == "non_blocking"
        assert row.judge_required is False


def test_judge_ids_are_not_in_inventory_rows() -> None:
    by_id = inventory_rows_by_validator_id()

    for judge_id in JUDGE_VALIDATORS.values():
        assert judge_id not in by_id


def test_inventory_rows_do_not_claim_judge_execution() -> None:
    for row in VALIDATOR_REGISTRY_INVENTORY:
        assert row.judge_required is False


def test_safe_for_plan_enforced_subset_is_conservative() -> None:
    safe_ids = {row.validator_id for row in VALIDATOR_REGISTRY_INVENTORY if row.safe_for_local_plan_enforced}

    assert "scene_energy_contract" in safe_ids
    assert "narrator_authority_contract" in safe_ids
    assert "environment_state_contract" in safe_ids
    assert "forecast_contract" not in safe_ids
    for diagnostic_id in OBSERVER_DIAGNOSTICS.values():
        row = inventory_rows_by_validator_id()[diagnostic_id]
        if row.current_status == STATUS_OBSERVER_ONLY and diagnostic_id != "sensory_context_diagnostic":
            assert diagnostic_id not in safe_ids
