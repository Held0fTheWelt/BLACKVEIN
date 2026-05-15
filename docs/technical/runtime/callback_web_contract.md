# Callback Web Contract

Status: Canonical technical contract for the bounded Pi17 callback-web runtime surface.

## Purpose

The callback web is a deterministic index over committed story-runtime continuity. It connects later committed turns back to earlier committed turns when the runtime can prove a bounded relationship through continuity classes, narrative threads, repeated scene anchors, or selected branch paths.

It exists so operators and the next LangGraph turn can see which earlier pressure is being reused without treating generated prose as memory or truth.

The callback web is:

- bounded by module policy,
- derived from committed runtime records,
- non-authoritative diagnostic evidence,
- persisted by the World-Engine,
- safe to expose through state, diagnostics, Langfuse/MCP matrices, and internal operator endpoints.

It is not:

- a second canon store,
- cross-session long-term memory,
- an unbounded graph database,
- a branch-state adoption mechanism,
- a prose-matching callback detector.

## Authority

Callback-web records may shape prompt context and operator diagnosis, but they do not decide story truth. Canonical truth remains in the committed `StorySession` fields, `narrative_commit` records, `environment_state`, narrative threads, and other runtime-owned state.

Every callback-web record and edge must carry the authority flags:

```json
{
  "non_authoritative": true,
  "mutates_canonical_state": false
}
```

Runtime code must never use callback-web evidence to skip validation, mutate canonical state, adopt simulated branch clone state, or override the commit seam.

## Runtime Shape

The core schemas are:

```json
{
  "record": "callback_web_record.v1",
  "observation": "callback_observation.v1",
  "edge": "callback_edge.v1",
  "snapshot": "callback_web_snapshot.v1",
  "graph_feedback": "callback_web_feedback.v1",
  "policy": "callback_web_policy.v1",
  "validation": "callback_web_validation.v1",
  "aspect": "callback_web_aspect.v1"
}
```

`callback_web_record.v1` contains:

- `callback_web_id`
- `story_session_id`
- `module_id`
- `runtime_profile_id`
- `bounds`
- `source_inputs`
- `current_session_fingerprint`
- `observations`
- `edges`
- `snapshot`

`callback_observation.v1` is one committed-turn projection. It records:

- `turn_id`
- `turn_number`
- `scene_id`
- `continuity_classes`
- `thread_ids`
- `related_entities`
- `signal_hashes`
- `has_callback_signal`

`callback_edge.v1` links an earlier committed turn to a later committed turn. Current edge kinds are:

- `repeated_continuity_class`
- `thread_continuity`
- `branch_selection_realized`
- `repeated_scene_anchor`

Edges store ids, classes, thread ids, branch tree ids, bounded evidence-field names, signal hashes, and confidence. They deliberately do not store generated narration as the evidence oracle.

## Source Inputs

The callback web derives from committed runtime surfaces only:

- `StorySession.history`
- `narrative_commit.planner_truth.continuity_impacts`
- `narrative_commit.continuity_impacts`
- `narrative_commit.open_pressures`
- `narrative_commit.committed_consequences`
- `StorySession.narrative_threads`
- durable `branch_timeline_record.v1` events
- current session fingerprint metadata

Recoverable/player-visible failure turns remain in session history for audit and
story-window continuity, but rows marked as recoverable outcomes or false
commits are filtered out before callback observations or edges are built.

Opening turn `0` is a valid callback source. This matters because the opening often establishes the pressure that later turns reuse.

Branch-derived edges only connect committed replay outcomes back to their original root turn. The callback web may observe `selection_replay_committed` or `selection_replay_conflict`, but it must not adopt simulated branch state.

## Policy and Bounds

Module runtime policy owns the runtime bounds:

```yaml
runtime_governance_policy:
  callback_web:
    enabled: true
    schema_version: callback_web_policy.v1
    max_edges: 80
    max_observations: 60
    max_graph_edges: 4
    max_evidence_refs_per_candidate: 8
    allowed_continuity_classes:
      - situational_pressure
      - dignity_injury
      - alliance_shift
      - revealed_fact
      - refused_cooperation
      - blame_pressure
```

The runtime normalizes these values through `ai_stack/callback_web_contracts.py`. Invalid or out-of-range numbers are clamped to bounded minimums and maximums. The graph feedback export is separately bounded by `max_graph_edges`.

## Flow

1. `story_runtime_core/callbacks/callback_web.py` builds observations and edges from committed history, narrative threads, and branch timeline events.
2. `JsonCallbackWebStore` persists one JSON record per `callback_web_id`.
3. `StoryRuntimeManager` rebuilds the callback web after committed turns and stores `callback_web_summary`, `callback_web_feedback`, and `callback_web_validation` on the latest history row.
4. Before the next graph run, `StoryRuntimeManager` exports bounded `callback_web_feedback.v1` as `prior_callback_web_state`.
5. `RuntimeTurnGraphExecutor` adds bounded callback values to context synthesis lanes and model prompt context.
6. `StoryRuntimeManager` records the `callback_web` runtime aspect using `callback_web_aspect.v1`.
7. State, diagnostics, Langfuse/MCP matrices, and internal operator endpoints expose the same bounded evidence.

## Operator Endpoints

The World-Engine internal API exposes:

```text
GET  /api/story/sessions/{session_id}/callback-web
GET  /api/story/sessions/{session_id}/callback-web/edges
POST /api/story/sessions/{session_id}/callback-web/rebuild
```

These routes require the internal API key. The rebuild route recomputes the record from current committed session state and branch timeline evidence; it does not mutate canonical story state.

## Diagnostics

Runtime diagnostics should use structured fields:

- `callback_web.edge_count`
- `callback_web.observation_count`
- `callback_web.callback_kind_counts`
- `callback_web.continuity_classes`
- `callback_web.thread_ids`
- `callback_web.branch_tree_ids`
- `callback_web_validation.contract_pass`
- `callback_web_validation.failure_codes`
- `turn_aspect_ledger.callback_web`
- MCP matrix fields such as `callback_web_selected_kind`, `callback_web_edge_count`, and `callback_web_contract_pass`

Operator tooling may display these values but must not infer callback correctness from visible narration.

## ADR-0039 Boundary

Gate and regression tests for this contract must derive expected behavior from exported constants, normalized module policy, schema versions, edge-kind vocabularies, session/turn ids, branch lifecycle fields, stable ids, and bounded list lengths.

Allowed test stimuli:

- literal player inputs,
- fixture turn ids,
- fixture continuity class ids,
- fixture branch tree ids.

Forbidden primary oracles:

- generated narration wording,
- copied scene prose,
- authored example paragraphs,
- branch preview text,
- hardcoded prose-shaped callbacks,
- unreviewed free-form baseline text.

Tests may assert that evidence fields name structured sources such as `narrative_commit.planner_truth.continuity_impacts` or `branch_timeline.events`. They must not assert that a specific story sentence is the callback.

## Implementation Anchors

- `story_runtime_core/callbacks/callback_web.py`
- `story_runtime_core/callbacks/__init__.py`
- `ai_stack/callback_web_contracts.py`
- `ai_stack/langgraph_runtime_state.py`
- `ai_stack/langgraph_runtime_executor.py`
- `ai_stack/module_runtime_policy.py`
- `ai_stack/runtime_aspect_ledger.py`
- `tools/mcp_server/tools_registry_handlers_langfuse_verify.py`
- `content/modules/god_of_carnage/module.yaml`
- `world-engine/app/story_runtime/callback_web_store.py`
- `world-engine/app/story_runtime/manager.py`
- `world-engine/app/api/http.py`
- `world-engine/app/config.py`
- `world-engine/app/main.py`

## Verification Anchors

- `ai_stack/tests/test_callback_web_contracts.py`
- `ai_stack/tests/test_module_runtime_policy.py`
- `tests/callbacks/test_callback_web.py`
- `tests/branching/test_branch_timeline.py`
- `tools/mcp_server/tests/test_langfuse_verify_tools.py`
- `world-engine/tests/test_callback_web_store.py`
- `world-engine/tests/test_story_runtime_callback_web.py`
- `world-engine/tests/test_story_runtime_branching_tree_api.py`
