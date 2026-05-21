"""Build semantic capability, validator-plan, and dispatch projections."""

from __future__ import annotations

from typing import Any, Callable

from ai_stack.capabilities.capability_validator_dispatch import ValidatorDispatchMode, resolve_validator_dispatch_mode

from ..authority_preview import _build_adr0041_plan_enforced_runtime_projection_dispatch
from ..capability_projection import (
    build_semantic_capability_selection_projection,
    build_semantic_validator_dispatch_report_projection,
    build_semantic_validator_execution_plan_projection,
)
from ..constants import ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY


def build_semantic_dispatch_sources(
    values: dict[str, Any],
    *,
    registry_for_turn_class: Callable[[str], dict[str, Any]] | None,
) -> dict[str, Any]:
    src = values["src"]
    capability_context = values["capability_context"]
    semantic_capability_selection = build_semantic_capability_selection_projection(
        **capability_context
    )
    semantic_validator_execution_plan = build_semantic_validator_execution_plan_projection(
        **capability_context
    )
    graph_bundle = src.get(ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY)
    graph_bundle = graph_bundle if isinstance(graph_bundle, dict) else None
    resolved_dispatch_mode, runtime_dispatch_mode_warnings = resolve_validator_dispatch_mode()
    if (
        graph_bundle is not None
        and resolved_dispatch_mode is ValidatorDispatchMode.PLAN_ENFORCED
    ):
        semantic_validator_dispatch_report = _build_adr0041_plan_enforced_runtime_projection_dispatch(
            capability_context=capability_context,
            graph_bundle=graph_bundle,
            dispatch_mode_warnings=runtime_dispatch_mode_warnings,
            registry_for_turn_class=registry_for_turn_class,
        )
    else:
        semantic_validator_dispatch_report = build_semantic_validator_dispatch_report_projection(
            **capability_context,
            dispatch_mode=ValidatorDispatchMode.DRY_RUN,
        )
    return {
        "semantic_capability_selection": semantic_capability_selection,
        "semantic_validator_execution_plan": semantic_validator_execution_plan,
        "semantic_validator_dispatch_report": semantic_validator_dispatch_report,
        "graph_bundle": graph_bundle,
        "resolved_dispatch_mode": resolved_dispatch_mode,
        "runtime_dispatch_mode_warnings": runtime_dispatch_mode_warnings,
    }
