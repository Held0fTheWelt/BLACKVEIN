"""Area 2 — compact ``no_eligible_operator_meaning`` payload (flat decision tree)."""

from __future__ import annotations

from typing import Any

from app.runtime.area2_operational_state import Area2OperationalState


def _discipline_worst_case(discipline: dict[str, Any]) -> str:
    worst = "not_applicable"
    if isinstance(discipline, dict):
        w = discipline.get("rollup_worst_case")
        if isinstance(w, str) and w:
            worst = w
    return worst


def _token_when_stages_report_no_eligible(worst: str) -> str:
    if worst == "true_no_eligible_adapter":
        return "routing_true_no_eligible_adapter_on_stage"
    if worst == "intentional_degraded_route":
        return "routing_no_eligible_with_task2e_degrade"
    if worst == "bounded_executor_mismatch":
        return "routing_bounded_executor_mismatch"
    if worst == "test_isolated_empty_registry":
        return "routing_no_eligible_test_isolated_discipline"
    if worst == "missing_registration_or_specs":
        return "routing_no_eligible_missing_specs"
    return "routing_no_eligible_on_stage_other_discipline"


def build_no_eligible_operator_meaning_payload(
    *,
    operational_state: Area2OperationalState,
    discipline: dict[str, Any],
    stages_nea: list[str],
) -> dict[str, Any]:
    """Same keys/shape as legacy ``_no_eligible_operator_meaning`` (operator_audit contract)."""

    worst = _discipline_worst_case(discipline)

    if operational_state is Area2OperationalState.test_isolated:
        token = "operational_test_isolated_empty_registry_expected"
    elif operational_state is Area2OperationalState.misconfigured:
        token = "operational_misconfigured_registry_or_inventory"
    elif operational_state is Area2OperationalState.intentionally_degraded:
        token = "operational_bootstrap_disabled_intentional"
    elif stages_nea:
        token = _token_when_stages_report_no_eligible(worst)
    elif worst != "not_applicable":
        token = "routing_discipline_signal_without_staged_no_eligible_list"
    else:
        token = "no_no_eligible_operator_concern_on_compact_view"

    applicable = (
        operational_state is not Area2OperationalState.healthy
        or bool(stages_nea)
        or (worst != "not_applicable")
    )

    return {
        "applicable": applicable,
        "operator_meaning_token": token,
        "discipline_worst_case": worst if worst != "not_applicable" else None,
        "stages_reporting_no_eligible_adapter": list(stages_nea),
    }
