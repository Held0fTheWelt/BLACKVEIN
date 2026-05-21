# Relationship State Machine Contract

Status: Canonical technical contract for the bounded Pi27 durable relationship
state-machine runtime aspect.

## Purpose

`relationship_state_machine` carries durable, bounded relationship feedback
across committed turns. It derives pair and axis state from structured runtime
signals, records transition events, feeds the next turn as prior state, and
exposes validation/observability fields through the runtime aspect ledger.

Relationship state is:

- policy-backed by `runtime_intelligence.relationship_state_machine`;
- derived from canonical relationship definitions, social-state codes,
  social-pressure state, NPC initiative-pressure edges, continuity classes, and
  prior committed relationship state;
- represented as bounded pair scores, axis aggregates, transition events, and a
  generation-facing target;
- persisted through planner truth after commit;
- rehydrated into the next turn as `prior_relationship_state_record`;
- exposed through `turn_aspect_ledger.relationship_state`, Langfuse, and MCP.

Relationship state is not:

- a prose or psychology judge over generated narration;
- a replacement for canonical module content, actor-lane safety, or commit
  validation;
- an unbounded full social simulator;
- frontend-owned inference;
- a second story-truth store outside the normal validated commit path.

## Authority

The authoritative policy source is:

```text
content/modules/god_of_carnage/module.yaml
runtime_intelligence.relationship_state_machine
```

Runtime code consumes the normalized
`ModuleRuntimePolicy.runtime_governance_policy.relationship_state_machine`
shape. Tests must load policy and canonical relationship YAML rather than
duplicating GoC-specific relationship truth.

The World-Engine remains the authority for committed session state. The
relationship state machine may shape prompt context, diagnostics, and recovery
feedback, but it does not mutate canon by itself.

## Runtime Shape

Core schemas:

```json
{
  "policy": "relationship_state_policy.v1",
  "state": "relationship_state_machine.v1",
  "target": "relationship_state_machine.v1",
  "validation": "relationship_state_machine.v1",
  "aspect": "turn_aspect_ledger.relationship_state"
}
```

`RelationshipStateRecord` carries:

- `pair_states`
- `axis_states`
- `transition_events`
- `active_relationship_axis_ids`
- `dominant_relationship_axis_id`
- `prior_record_fingerprint`
- `source_evidence`
- `rationale_codes`

`RelationshipDynamicsTarget` carries:

- `target_axis_ids`
- `target_relationship_ids`
- `required_transition_codes`
- `pressure_band`
- `requires_visible_relationship_beat`
- `source_evidence`
- `rationale_codes`

## Flow

1. `ModuleRuntimePolicy` normalizes the module policy.
2. LangGraph derives scene energy, pacing rhythm, social pressure, sensory
   context, improvisational coherence, information disclosure, and dramatic
   irony.
3. LangGraph derives `relationship_state_record` and
   `relationship_dynamics_target` from canonical relationships, social state,
   social pressure, NPC initiative edges, prior relationship state, and prior
   planner truth.
4. The dramatic generation packet receives both durable `relationship_state`
   and bounded `relationship_dynamics_context`.
5. Validation checks schema bounds, target ids, transition codes, and
   actor-lane compatibility for any structured `relationship_dynamics_events`.
6. `turn_aspect_ledger.relationship_state` records policy, target, counts,
   contract pass/fail, and failure codes.
7. World-Engine persists state, target, and validation in planner truth.
8. The next turn receives the latest committed state as
   `prior_relationship_state_record`.
9. Langfuse and MCP expose target presence, pressure band, pair/transition
   counts, pass/fail, and failure-code evidence.

## ADR-0039 Boundary

Allowed test oracles:

- exported schema constants;
- normalized module policy;
- canonical relationship YAML;
- structured social-state fields;
- structured NPC initiative graph edges;
- committed planner-truth fields;
- runtime aspect ledger fields;
- MCP matrix fields;
- validation failure codes.

Forbidden primary oracles:

- generated narration wording;
- copied dialogue or authored example prose;
- LLM-as-a-Judge relationship labels;
- frontend card shape;
- hardcoded GoC actor, location, phase, or relationship truths in generic
  runtime code;
- Table-B labels outside reviewed canonical surfaces.

## Implementation Anchors

- `ai_stack/contracts/relationship_state_contracts.py`
- `ai_stack/story_runtime/narrative/relationship_state_engine.py`
- `ai_stack/module_runtime_policy.py`
- `ai_stack/langgraph/langgraph_runtime_state.py`
- `ai_stack/langgraph/langgraph_runtime_executor.py`
- `ai_stack/story_runtime/runtime_aspect_ledger/__init__.py`
- `world-engine/app/story_runtime/commit_models.py`
- `world-engine/app/story_runtime/manager/`
- `tools/mcp_server/handlers/langfuse_verify/`
- `content/modules/god_of_carnage/module.yaml`
