# Symbolic Object Resonance Contract

`symbolic_object_resonance` is the bounded runtime contract for Pi33 symbolic
resonance. The Pi label remains matrix vocabulary only. Runtime code,
schemas, ledger rows, Langfuse scores, MCP fields, and tests use the semantic
aspect name.

## Scope

The contract selects canonical object ids and symbolic roles from structured
runtime state. It does not infer symbolism from generated narration and does
not validate prose quality.

Structured sources may include:

- `environment_state.salient_object_ids`
- canonical object records from the module environment/object model
- `player_action_frame.resolved_target`
- adjacent runtime targets such as `sensory_context`, `social_pressure`,
  `relationship_state`, and `expectation_variation`
- committed callback/consequence feedback and prior planner truth

The selected target is bounded by `max_symbols_per_turn`, allowed resonance
roles, source references, and module policy.

## Runtime Flow

1. `ModuleRuntimePolicy.runtime_governance_policy.symbolic_object_resonance`
   normalizes the module policy.
2. LangGraph derives `symbolic_object_resonance_state` and
   `symbolic_object_resonance_target` from structured inputs.
3. The dramatic generation packet receives only bounded object ids, symbol ids,
   roles, and source refs.
4. Structured output may emit `symbolic_object_resonance_events`.
5. Validation checks selected object ids, selected symbol ids, allowed roles,
   source refs, event presence, and per-turn budget.
6. `RuntimeAspectLedger.symbolic_object_resonance` records expected, selected,
   actual, failure codes, and contract status for Langfuse/MCP projection.
7. `PlannerTruth` persists state/target/validation so the next turn can rehydrate
   bounded resonance history.

## Contract Fields

- Schema: `symbolic_object_resonance.v1`
- Policy: `symbolic_object_resonance_policy.v1`
- Structured event key: `symbolic_object_resonance_events`
- Runtime aspect: `symbolic_object_resonance`
- Failure codes:
  - `symbolic_object_resonance_target_mismatch`
  - `symbolic_object_resonance_unselected_object`
  - `symbolic_object_resonance_role_mismatch`
  - `symbolic_object_resonance_missing_required_event`
  - `symbolic_object_resonance_source_ref_mismatch`
  - `symbolic_object_resonance_budget_exceeded`

## ADR-0039 Boundary

Tests and gates use schema constants, normalized policy, canonical object
content, structured event rows, ledger projection, MCP extraction fields, and
planner-truth persistence as oracles. Generated symbolic prose, copied module
examples, and Pi-number runtime keys are not valid pass/fail evidence.

Primary implementation anchors:

- `ai_stack/contracts/symbolic_object_resonance_contracts.py`
- `ai_stack/story_runtime/narrative/symbolic_object_resonance_engine.py`
- `ai_stack/module_runtime_policy.py`
- `ai_stack/langgraph/langgraph_runtime_executor.py`
- `ai_stack/story_runtime/runtime_aspect_ledger/__init__.py`
- `world-engine/app/story_runtime/commit_models.py`
- `world-engine/app/story_runtime/manager/`
- `tools/mcp_server/handlers/tools_registry_handlers_langfuse_verify.py`
