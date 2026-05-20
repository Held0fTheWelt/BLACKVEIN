"""Single source for ``app.runtime`` module packages and runtime layering.

Aligned with ``docs/technical/architecture/backend-runtime-classification.md``:
**transitional** modules host or execute in-process narrative/session flows; **canonical**
modules are reusable contracts, policies, presenters, and registries without implying
live play runs in Flask.

Global runtime modules stay directly under ``app/runtime``. Domain-specific runtime
modules live in subpackages such as ``turn``, ``session``, ``presentation``, and
``routing``. The tests enforce that every runtime module appears exactly once here.
"""

from __future__ import annotations

GLOBAL_RUNTIME_MODULE_NAMES: frozenset[str] = frozenset(
    {
        "_string_utils",
        "adapter_registry",
        "agent_registry",
        "ai_adapter",
        "context_types",
        "engine",
        "event_log",
        "helper_functions",
        "input_interpreter",
        "manager",
        "model_routing",
        "model_routing_contracts",
        "models",
        "parsed_ai_decision_types",
        "routing_registry_bootstrap",
        "runtime_models",
        "runtime_stage_ids",
        "scene_legality",
        "visibility",
    }
)

RUNTIME_MODULE_PACKAGES: dict[str, str] = {
    "ai_decision": "ai",
    "ai_decision_logging": "ai",
    "ai_failure_recovery": "ai",
    "ai_output": "ai",
    "role_contract": "ai",
    "role_structured_decision": "ai",
    "ai_turn_adapter_bridge": "ai_turn",
    "ai_turn_constants": "ai_turn",
    "ai_turn_decision_helpers": "ai_turn",
    "ai_turn_execute_integration": "ai_turn",
    "ai_turn_execute_integration_phases": "ai_turn",
    "ai_turn_executor": "ai_turn",
    "ai_turn_generation": "ai_turn",
    "ai_turn_orchestration_branch": "ai_turn",
    "ai_turn_orchestration_logging": "ai_turn",
    "ai_turn_orchestration_sections": "ai_turn",
    "ai_turn_parse_helpers": "ai_turn",
    "ai_turn_post_parse_pipeline": "ai_turn",
    "ai_turn_pre_adapter": "ai_turn",
    "ai_turn_preview": "ai_turn",
    "ai_turn_primary_tool_loop": "ai_turn",
    "ai_turn_recovery_generation_failure_exhausted": "ai_turn",
    "ai_turn_recovery_paths": "ai_turn",
    "ai_turn_recovery_state": "ai_turn",
    "ai_turn_routing_builders": "ai_turn",
    "ai_turn_runtime_sections": "ai_turn",
    "ai_turn_shared_types": "ai_turn",
    "runtime_ai_stages": "ai_turn",
    "runtime_ai_stages_sections": "ai_turn",
    "orchestration_cache": "cache",
    "lore_direction_context": "narrative",
    "lore_direction_context_derivation": "narrative",
    "lore_direction_context_types": "narrative",
    "narrative_commit": "narrative",
    "narrative_state_transfer_dto": "narrative",
    "narrative_threads": "narrative",
    "narrative_threads_commit_path_utils": "narrative",
    "narrative_threads_update_from_commit": "narrative",
    "narrative_threads_update_from_commit_phases": "narrative",
    "next_situation": "narrative",
    "npc_behaviors": "narrative",
    "progression_summary": "narrative",
    "progression_summary_derive_constants": "narrative",
    "relationship_context": "narrative",
    "relationship_context_derive": "narrative",
    "short_term_context": "narrative",
    "debug_presenter": "presentation",
    "debug_presenter_sections": "presentation",
    "history_presenter": "presentation",
    "preview_delta": "presentation",
    "preview_models": "presentation",
    "scene_presenter": "presentation",
    "scene_presenter_conflict_helpers": "presentation",
    "scene_presenter_conflict_models": "presentation",
    "scene_presenter_conflict_sections": "presentation",
    "model_inventory_contract": "routing",
    "model_inventory_report": "routing",
    "model_routing_evidence": "routing",
    "no_eligible_operator_meaning": "routing",
    "operational_state": "routing",
    "operator_audit": "routing",
    "operator_truth": "routing",
    "routing_authority": "routing",
    "startup_profiles": "routing",
    "session_history": "session",
    "session_history_constants": "session",
    "session_mirror": "session",
    "session_persistence": "session",
    "session_start": "session",
    "session_store": "session",
    "store": "session",
    "supervisor_execution_types": "supervisor",
    "supervisor_invoke_agent": "supervisor",
    "supervisor_invoke_agent_sections": "supervisor",
    "supervisor_invoke_agent_tool_loop_phases": "supervisor",
    "supervisor_merge_finalize_finalizer_budget": "supervisor",
    "supervisor_merge_finalize_finalizer_budget_paths": "supervisor",
    "supervisor_orchestrate_execute": "supervisor",
    "supervisor_orchestrate_execute_sections": "supervisor",
    "supervisor_orchestrate_merge_finalize_sections": "supervisor",
    "supervisor_orchestrate_non_finalizer_budget_and_invoke": "supervisor",
    "supervisor_orchestrate_non_finalizer_loop_phases": "supervisor",
    "supervisor_orchestrate_working_state": "supervisor",
    "supervisor_orchestration_audit": "supervisor",
    "supervisor_orchestrator": "supervisor",
    "supervisor_orchestrator_finalize_with_agent": "supervisor",
    "supervisor_orchestrator_finalize_with_agent_fallbacks": "supervisor",
    "supervisor_orchestrator_finalize_with_agent_records": "supervisor",
    "tool_loop": "turn",
    "turn_dispatcher": "turn",
    "turn_execution_types": "turn",
    "turn_executor": "turn",
    "turn_executor_decision_delta": "turn",
    "turn_executor_validated_pipeline": "turn",
    "turn_executor_validated_pipeline_apply": "turn",
    "turn_executor_validated_pipeline_narrative_log": "turn",
    "decision_policy": "validation",
    "mutation_policy": "validation",
    "pipeline_decision_guards": "validation",
    "reference_policy": "validation",
    "validators": "validation",
    "validators_action_structure": "validation",
}

RUNTIME_PACKAGE_NAMES: frozenset[str] = frozenset(RUNTIME_MODULE_PACKAGES.values())

# In-process turn/session execution and AI orchestration entrypoints (Block 2 "class 2").
TRANSITIONAL_RUNTIME_MODULE_NAMES: frozenset[str] = frozenset(
    {
        "ai_turn_constants",
        "ai_turn_executor",
        "ai_turn_generation",
        "ai_turn_orchestration_branch",
        "ai_turn_preview",
        "ai_turn_primary_tool_loop",
        "ai_turn_routing_builders",
        "engine",
        "manager",
        "runtime_ai_stages",
        "session_start",
        "session_store",
        "store",
        "turn_dispatcher",
        "turn_executor",
    }
)

_ALL_RUNTIME_ROOT_MODULES: frozenset[str] = GLOBAL_RUNTIME_MODULE_NAMES
_ALL_RUNTIME_MODULE_NAMES: frozenset[str] = frozenset(
    GLOBAL_RUNTIME_MODULE_NAMES | frozenset(RUNTIME_MODULE_PACKAGES)
)

CANONICAL_RUNTIME_MODULE_NAMES: frozenset[str] = frozenset(
    _ALL_RUNTIME_MODULE_NAMES - TRANSITIONAL_RUNTIME_MODULE_NAMES
)


def runtime_module_import_path(name: str) -> str:
    """Return the fully qualified import path for a classified runtime module."""
    package = RUNTIME_MODULE_PACKAGES.get(name)
    if package:
        return f"app.runtime.{package}.{name}"
    if name in GLOBAL_RUNTIME_MODULE_NAMES:
        return f"app.runtime.{name}"
    raise KeyError(name)


assert not (GLOBAL_RUNTIME_MODULE_NAMES & frozenset(RUNTIME_MODULE_PACKAGES))
assert not (CANONICAL_RUNTIME_MODULE_NAMES & TRANSITIONAL_RUNTIME_MODULE_NAMES)
assert CANONICAL_RUNTIME_MODULE_NAMES | TRANSITIONAL_RUNTIME_MODULE_NAMES == _ALL_RUNTIME_MODULE_NAMES

__all__ = [
    "CANONICAL_RUNTIME_MODULE_NAMES",
    "GLOBAL_RUNTIME_MODULE_NAMES",
    "RUNTIME_MODULE_PACKAGES",
    "RUNTIME_PACKAGE_NAMES",
    "TRANSITIONAL_RUNTIME_MODULE_NAMES",
    "_ALL_RUNTIME_MODULE_NAMES",
    "_ALL_RUNTIME_ROOT_MODULES",
    "runtime_module_import_path",
]
