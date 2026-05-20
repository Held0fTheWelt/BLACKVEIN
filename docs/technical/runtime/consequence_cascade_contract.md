# Consequence Cascade Contract

Status: Canonical technical contract for the bounded Pi21 consequence-cascade runtime aspect.

## Purpose

`consequence_cascade` is the deterministic continuity projection for consequences that remain active across committed turns. It turns committed runtime truth into bounded consequence atoms and edges, then feeds a compact snapshot back into the next LangGraph turn and operator diagnostics.

The cascade exists so the runtime can see which prior pressures still matter without treating generated narration, branch preview text, or authored examples as memory.

Consequence cascade is:

- policy-backed by `runtime_intelligence.consequence_cascade`;
- derived only from committed session records, narrative threads, and durable branch timeline events;
- bounded by module policy before graph export;
- persisted by the World-Engine as one record per story session;
- exposed through `turn_aspect_ledger.consequence_cascade`, state, diagnostics, Langfuse/MCP matrices, and internal operator endpoints.

Consequence cascade is not:

- a second canon store;
- cross-session long-term memory;
- an unbounded graph database;
- an authority to adopt simulated branch state;
- a generated-prose consequence judge;
- a Table-B label that production code may reference outside reviewed canonical surfaces.

## Authority

The authoritative value source is committed runtime state. The cascade may shape prompt context and operator diagnosis, but it cannot decide story truth, bypass validation, mutate canonical state, or replace narrative threads.

Every cascade record and edge must preserve the authority boundary:

```json
{
  "derived_from_committed_truth": true,
  "mutates_canonical_state": false,
  "forecast_only": false,
  "inactive_branches_authoritative": false
}
```

Branch-derived edges may observe committed replay outcomes such as `selection_replay_committed` or `selection_replay_conflict`. They must not adopt inactive branch preview state.

## Runtime Shape

The core schemas are:

```json
{
  "record": "consequence_cascade_record.v1",
  "atom": "consequence_atom.v1",
  "edge": "consequence_edge.v1",
  "snapshot": "consequence_cascade_snapshot.v1",
  "graph_feedback": "consequence_cascade_feedback.v1",
  "policy": "consequence_cascade_policy.v1",
  "validation": "consequence_cascade_validation.v1",
  "aspect": "consequence_cascade_aspect.v1"
}
```

`consequence_cascade_record.v1` contains:

- `cascade_id`
- `story_session_id`
- `module_id`
- `runtime_profile_id`
- `bounds`
- `derived_from_committed_truth`
- `mutates_canonical_state`
- `forecast_only`
- `inactive_branches_authoritative`
- `callback_web_id`
- `atoms`
- `edges`
- `snapshot`

`consequence_atom.v1` is one committed-turn consequence projection. It records:

- `consequence_id`
- `source_turn_id`
- `source_turn_number`
- `source_kind`
- `source_field`
- `scene_id`
- `continuity_class`
- `related_entities`
- `thread_ids`
- `status` (`active`, `fading`, or `resolved`)
- `freshness_turns`
- `salience`
- bounded `evidence.source_fields`
- bounded `evidence.signal_hashes`

`consequence_edge.v1` links two consequence atoms. Current edge kinds are:

- `carry_forward`
- `thread_continuity`
- `resolution`
- `branch_selection_realized`

Edges store ids, source/target turn ids, source/target turn numbers, continuity class, thread ids, and bounded evidence-field names. They deliberately do not store generated narration as the evidence oracle.

## Source Inputs

The cascade derives from committed runtime surfaces only:

- `StorySession.history`
- `narrative_commit.planner_truth.continuity_impacts`
- `narrative_commit.continuity_impacts`
- `narrative_commit.beat_progression.pressure_state`
- `narrative_commit.open_pressures`
- `narrative_commit.committed_consequences`
- `narrative_commit.resolved_pressures`
- `StorySession.narrative_threads`
- durable `branch_timeline_record.v1` events
- optional `callback_web_id` correlation

Recoverable/player-visible failure turns remain in session history for audit and
story-window continuity, but rows marked as recoverable outcomes or false
commits are filtered out before consequence atoms or edges are built.

The graph feedback export omits atom evidence and returns only bounded ids, classes, statuses, turn numbers, and thread ids.

## Policy and Bounds

Module runtime policy owns the bounds:

```yaml
runtime_intelligence:
  consequence_cascade:
    enabled: true
    schema_version: consequence_cascade_policy.v1
    max_atoms: 80
    max_edges: 120
    max_graph_items: 5
    max_evidence_refs_per_consequence: 8
    decay_after_turns: 4
    allowed_continuity_classes:
      - situational_pressure
      - dignity_injury
      - alliance_shift
```

`ModuleRuntimePolicy` normalizes this into `runtime_governance_policy.consequence_cascade` through `ai_stack/contracts/consequence_cascade_contracts.py`. Invalid or out-of-range numbers are clamped to bounded minimums and maximums. The graph feedback export is separately bounded by `max_graph_items`.

## Flow

1. `ModuleRuntimePolicy` normalizes `runtime_intelligence.consequence_cascade`.
2. `story_runtime_core/consequences/consequence_cascade.py` builds atoms and edges from committed history, narrative threads, branch timeline events, and optional callback-web correlation.
3. `JsonConsequenceCascadeStore` persists one JSON record per `cascade_id`.
4. `StoryRuntimeManager` rebuilds the cascade after committed turns and stores `consequence_cascade_summary`, `consequence_cascade_feedback`, and `consequence_cascade_validation` on the latest history row.
5. Before the next graph run, `StoryRuntimeManager` exports bounded `consequence_cascade_feedback.v1` as `prior_consequence_cascade_state`.
6. `RuntimeTurnGraphExecutor` adds bounded cascade values to context synthesis lanes, scene assessment, retrieve-context prompt, dramatic generation packet, and final model context.
7. `StoryRuntimeManager` records the `consequence_cascade` runtime aspect using `consequence_cascade_aspect.v1`.
8. State, diagnostics, Langfuse/MCP matrices, and internal operator endpoints expose the same bounded evidence.

## Operator Endpoints

The World-Engine internal API exposes:

```text
GET  /api/story/sessions/{session_id}/consequence-cascade
GET  /api/story/sessions/{session_id}/consequence-cascade/edges
POST /api/story/sessions/{session_id}/consequence-cascade/rebuild
```

These routes require the internal API key. The rebuild route recomputes the record from current committed session state and branch timeline evidence; it does not mutate canonical story state.

## Diagnostics

Runtime diagnostics should use structured fields:

- `consequence_cascade.atom_count`
- `consequence_cascade.edge_count`
- `consequence_cascade.active_atom_count`
- `consequence_cascade.status_counts`
- `consequence_cascade.edge_kind_counts`
- `consequence_cascade.continuity_classes`
- `consequence_cascade_validation.contract_pass`
- `consequence_cascade_validation.failure_codes`
- `turn_aspect_ledger.consequence_cascade`
- MCP matrix fields such as `consequence_cascade_selected_consequence_ids`, `consequence_cascade_atom_count`, `consequence_cascade_edge_count`, and `consequence_cascade_contract_pass`

Operator tooling may display these values but must not infer cascade correctness from visible narration.

## ADR-0039 Boundary

Gate and regression tests for this contract must derive expectations from exported schema constants, normalized module policy, edge-kind vocabularies, status vocabularies, session/turn ids, branch lifecycle fields, stable ids, authority flags, and bounded list lengths.

Allowed test stimuli:

- literal player inputs;
- fixture turn ids;
- fixture continuity class ids loaded from policy;
- fixture branch tree ids;
- fixture narrative-thread ids.

Forbidden primary oracles:

- generated narration wording;
- copied scene prose;
- authored example paragraphs;
- branch preview text;
- hardcoded prose-shaped consequences;
- unreviewed Table-B control labels in production logic;
- duplicated policy truth in tests when the policy can be loaded.

Tests may assert that evidence fields name structured sources such as `narrative_commit.planner_truth.continuity_impacts`, `narrative_commit.beat_progression.pressure_state`, `narrative_commit.resolved_pressures`, `session.narrative_threads`, or `branch_timeline.events`. They must not assert that a specific story sentence is the consequence.

## Implementation Anchors

- `content/modules/god_of_carnage/module.yaml`
- `story_runtime_core/consequences/consequence_cascade.py`
- `story_runtime_core/consequences/__init__.py`
- `ai_stack/contracts/consequence_cascade_contracts.py`
- `ai_stack/langgraph/langgraph_runtime_state.py`
- `ai_stack/langgraph/langgraph_runtime_executor.py`
- `ai_stack/module_runtime_policy.py`
- `ai_stack/story_runtime/runtime_aspect_ledger/__init__.py`
- `tools/mcp_server/handlers/tools_registry_handlers_langfuse_verify.py`
- `world-engine/app/story_runtime/consequence_cascade_store.py`
- `world-engine/app/story_runtime/manager/`
- `world-engine/app/api/http.py`
- `world-engine/app/config.py`
- `world-engine/app/main.py`

## Verification Anchors

- `ai_stack/tests/test_consequence_cascade_contracts.py`
- `ai_stack/tests/test_module_runtime_policy.py`
- `ai_stack/tests/test_runtime_aspect_ledger.py`
- `tests/consequences/test_consequence_cascade.py`
- `tools/mcp_server/tests/test_langfuse_verify_tools.py`
- `world-engine/tests/test_consequence_cascade_store.py`
- `world-engine/tests/test_story_runtime_consequence_cascade.py`
- `world-engine/tests/test_story_runtime_branching_tree_api.py`
- `tests/gates/test_table_b_anti_hardcoding_gate.py`
