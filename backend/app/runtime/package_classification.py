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
        "adapter_registry",
        "agent_registry",
        "ai_adapter",
        "ai_decision",
        "ai_decision_logging",
        "ai_failure_recovery",
        "ai_output",
        "ai_turn_constants",
        "ai_turn_executor",
        "ai_turn_generation",
        "ai_turn_orchestration_branch",
        "ai_turn_preview",
        "ai_turn_primary_tool_loop",
        "ai_turn_routing_builders",
        "area2_operational_state",
        "area2_operator_truth",
        "area2_routing_authority",
        "area2_startup_profiles",
        "area2_validation_commands",
        "decision_policy",
        "debug_presenter",
        "engine",
        "event_log",
        "helper_functions",
        "history_presenter",
        "input_interpreter",
        "lore_direction_context",
        "manager",
        "model_inventory_contract",
        "model_inventory_report",
        "model_routing",
        "model_routing_contracts",
        "model_routing_evidence",
        "models",
        "mutation_policy",
        "narrative_commit",
        "narrative_threads",
        "next_situation",
        "npc_behaviors",
        "operator_audit",
        "orchestration_cache",
        "parsed_ai_decision_types",
        "preview_delta",
        "preview_models",
        "progression_summary",
        "reference_policy",
        "relationship_context",
        "role_contract",
        "role_structured_decision",
        "routing_registry_bootstrap",
        "runtime_ai_stages",
        "runtime_models",
        "scene_legality",
        "scene_presenter",
        "session_history",
        "session_persistence",
        "session_start",
        "session_store",
        "short_term_context",
        "store",
        "supervisor_orchestration_audit",
        "supervisor_orchestrator",
        "tool_loop",
        "turn_dispatcher",
        "turn_execution_types",
        "turn_executor",
        "validators",
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
