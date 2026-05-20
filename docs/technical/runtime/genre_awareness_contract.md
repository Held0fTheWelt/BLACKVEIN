# Genre Awareness Contract

`genre_awareness` is the bounded runtime contract for Pi32 genre awareness. The
Pi label remains Capability Matrix vocabulary only. Runtime code, schemas,
ledger rows, Langfuse scores, MCP fields, and tests use the semantic aspect
name.

## Scope

The contract selects a module-authored genre profile and validates structured
realization evidence for that profile. It does not infer genre quality from
generated narration and does not score prose style.

Structured sources may include:

- `ModuleRuntimePolicy.runtime_governance_policy.genre_awareness`
- selected scene function and scene id
- adjacent runtime targets such as `scene_energy`, `social_pressure`, and
  `relationship_state`
- prior committed `genre_awareness_state` from planner truth
- structured generation output under `genre_awareness_events`

The selected target is bounded by the module policy: profile id, allowed
registers, required conventions, forbidden marker ids, event requirement, and
per-turn signal budget.

## Runtime Flow

1. `ModuleRuntimePolicy.runtime_governance_policy.genre_awareness` normalizes
   the module policy from `runtime_intelligence.genre_awareness`.
2. LangGraph derives `genre_awareness_state` and `genre_awareness_target` from
   structured runtime context.
3. The dramatic generation packet receives only bounded profile, register,
   convention, forbidden-marker, and budget fields.
4. Structured output may emit `genre_awareness_events`.
5. Validation checks selected profile id, allowed register, required
   conventions, forbidden markers, event presence, and per-turn budget.
6. `RuntimeAspectLedger.genre_awareness` records expected, selected, actual,
   failure codes, and contract status for Langfuse/MCP projection.
7. `PlannerTruth` persists state/target/validation so the next turn can
   rehydrate bounded genre context.

## Contract Fields

- Schema: `genre_awareness.v1`
- Policy: `genre_awareness_policy.v1`
- Structured event key: `genre_awareness_events`
- Runtime aspect: `genre_awareness`
- Failure codes:
  - `genre_awareness_target_mismatch`
  - `genre_awareness_missing_required_event`
  - `genre_awareness_event_budget_exceeded`
  - `genre_awareness_unselected_profile`
  - `genre_awareness_register_not_allowed`
  - `genre_awareness_missing_required_convention`
  - `genre_awareness_forbidden_marker`

## Authority Boundary

`genre_awareness` is prompt/runtime governance and diagnostic evidence. It may
shape bounded context, retry feedback, RuntimeAspectLedger rows, Langfuse spans,
and MCP matrix extraction. It does not mutate canon by itself and does not
bypass validation or the normal narrative commit seam.

The current implementation is local/diagnostic evidence. It is not a live or
staging claim for general multi-genre adaptation.

## ADR-0039 Boundary

Tests and gates use schema constants, normalized module policy, structured
event rows, ledger projection, MCP extraction fields, and planner-truth
persistence as oracles. Generated genre prose, copied module examples, judge
labels, and Pi-number runtime keys are not valid pass/fail evidence.

Primary implementation anchors:

- `ai_stack/contracts/genre_awareness_contracts.py`
- `ai_stack/story_runtime/narrative/genre_awareness_engine.py`
- `ai_stack/module_runtime_policy.py`
- `ai_stack/langgraph/langgraph_runtime_executor.py`
- `ai_stack/story_runtime/runtime_aspect_ledger/__init__.py`
- `world-engine/app/story_runtime/commit_models.py`
- `world-engine/app/story_runtime/manager/`
- `tools/mcp_server/handlers/tools_registry_handlers_langfuse_verify.py`

Primary verification anchors:

- `ai_stack/tests/test_genre_awareness_engine.py`
- `ai_stack/tests/test_module_runtime_policy.py`
- `ai_stack/tests/test_runtime_aspect_ledger.py`
- `world-engine/tests/test_planner_truth_and_runtime_surfaces.py`
- `tools/mcp_server/tests/test_langfuse_verify_tools.py`
- `tests/gates/test_table_b_anti_hardcoding_gate.py`
