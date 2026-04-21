"""Single source for ``app.runtime`` module layering (canonical vs transitional).

Aligned with ``docs/technical/architecture/backend-runtime-classification.md``:
**transitional** modules host or execute in-process narrative/session flows; **canonical**
modules are reusable contracts, policies, presenters, and registries without implying
live play runs in Flask.

Every ``*.py`` directly under ``app/runtime/`` (except this file and ``__init__.py``)
must appear in exactly one of the two frozensets. The test suite enforces completeness.
"""

from __future__ import annotations

# In-process turn/session execution and AI orchestration entrypoints (Block 2 “class 2”).
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

# Explicit union = all runtime root modules (maintain when adding files).
_ALL_RUNTIME_ROOT_MODULES: frozenset[str] = frozenset(
    {
        "_string_utils",
        "adapter_registry",
        "agent_registry",
        "ai_adapter",
        "ai_decision",
        "ai_decision_logging",
        "ai_failure_recovery",
        "ai_output",
        "ai_turn_adapter_bridge",
        "ai_turn_constants",
        "ai_turn_decision_helpers",
        "ai_turn_execute_integration",
        "ai_turn_execute_integration_phases",
        "ai_turn_executor",
        "ai_turn_generation",
        "ai_turn_orchestration_branch",
        "ai_turn_orchestration_logging",
        "ai_turn_orchestration_sections",
        "ai_turn_parse_helpers",
        "ai_turn_post_parse_pipeline",
        "ai_turn_pre_adapter",
        "ai_turn_preview",
        "ai_turn_primary_tool_loop",
        "ai_turn_recovery_generation_failure_exhausted",
        "ai_turn_recovery_paths",
        "ai_turn_routing_builders",
        "ai_turn_runtime_sections",
        "ai_turn_shared_types",
        "area2_no_eligible_operator_meaning",
        "area2_operational_state",
        "area2_operator_truth",
        "area2_routing_authority",
        "area2_startup_profiles",
        "area2_validation_commands",
        "context_types",
        "debug_presenter",
        "debug_presenter_sections",
        "decision_policy",
        "engine",
        "event_log",
        "helper_functions",
        "history_presenter",
        "input_interpreter",
        "lore_direction_context",
        "lore_direction_context_derivation",
        "lore_direction_context_types",
        "manager",
        "model_inventory_contract",
        "model_inventory_report",
        "model_routing",
        "model_routing_contracts",
        "model_routing_evidence",
        "models",
        "mutation_policy",
        "narrative_commit",
        "narrative_state_transfer_dto",
        "narrative_threads",
        "narrative_threads_commit_path_utils",
        "narrative_threads_update_from_commit",
        "narrative_threads_update_from_commit_phases",
        "next_situation",
        "npc_behaviors",
        "operator_audit",
        "orchestration_cache",
        "parsed_ai_decision_types",
        "pipeline_decision_guards",
        "preview_delta",
        "preview_models",
        "progression_summary",
        "progression_summary_derive_constants",
        "reference_policy",
        "relationship_context",
        "relationship_context_derive",
        "role_contract",
        "role_structured_decision",
        "routing_registry_bootstrap",
        "runtime_ai_stages",
        "runtime_ai_stages_sections",
        "runtime_models",
        "runtime_stage_ids",
        "scene_legality",
        "scene_presenter",
        "scene_presenter_conflict_helpers",
        "scene_presenter_conflict_sections",
        "session_history",
        "session_history_constants",
        "session_mirror",
        "session_persistence",
        "session_start",
        "session_store",
        "short_term_context",
        "store",
        "supervisor_execution_types",
        "supervisor_invoke_agent",
        "supervisor_invoke_agent_sections",
        "supervisor_invoke_agent_tool_loop_phases",
        "supervisor_merge_finalize_finalizer_budget",
        "supervisor_merge_finalize_finalizer_budget_paths",
        "supervisor_orchestrate_execute",
        "supervisor_orchestrate_execute_sections",
        "supervisor_orchestrate_merge_finalize_sections",
        "supervisor_orchestrate_non_finalizer_budget_and_invoke",
        "supervisor_orchestrate_non_finalizer_loop_phases",
        "supervisor_orchestrate_working_state",
        "supervisor_orchestration_audit",
        "supervisor_orchestrator",
        "supervisor_orchestrator_finalize_with_agent",
        "supervisor_orchestrator_finalize_with_agent_fallbacks",
        "supervisor_orchestrator_finalize_with_agent_records",
        "tool_loop",
        "turn_dispatcher",
        "turn_execution_types",
        "turn_executor",
        "turn_executor_decision_delta",
        "turn_executor_validated_pipeline",
        "turn_executor_validated_pipeline_apply",
        "turn_executor_validated_pipeline_narrative_log",
        "validators",
        "validators_action_structure",
        "visibility",
    }
)

CANONICAL_RUNTIME_MODULE_NAMES: frozenset[str] = frozenset(
    _ALL_RUNTIME_ROOT_MODULES - TRANSITIONAL_RUNTIME_MODULE_NAMES
)

assert not (CANONICAL_RUNTIME_MODULE_NAMES & TRANSITIONAL_RUNTIME_MODULE_NAMES)
assert CANONICAL_RUNTIME_MODULE_NAMES | TRANSITIONAL_RUNTIME_MODULE_NAMES == _ALL_RUNTIME_ROOT_MODULES

__all__ = [
    "CANONICAL_RUNTIME_MODULE_NAMES",
    "TRANSITIONAL_RUNTIME_MODULE_NAMES",
    "_ALL_RUNTIME_ROOT_MODULES",
]
