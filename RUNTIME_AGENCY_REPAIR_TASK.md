# Runtime Agency Repair — Dependency-Aware Implementation Task

## Overview

This task repairs live runtime behavior so the experience is visibly actor-driven, not narration-only.  
The implementation order is dependency-aware: fix visibility first, then contract shape, then truth preservation, then agency sophistication.

## Objective

Deliver a governed runtime that:

1. renders actor behavior in the active player shell,
2. feeds dramatic planner truth into generation,
3. preserves actor-level outputs through normalize/validate/commit/render,
4. exposes degraded/fallback behavior clearly,
5. and provides telemetry proving where behavior survives or degrades.

## Non-goals

1. Remove governance or validation.
2. Replace the authoritative world-engine model.
3. Turn runtime into unrestricted freeform roleplay.

## Dependency Map

| Workstream | Name | Depends on | Why |
| --- | --- | --- | --- |
| WS-1 | Surface Repair | None | No value in deeper runtime fixes if players cannot see output. |
| WS-2 | Contract Repair | WS-1 | Actor-level output must be visible and testable while schema migrates. |
| WS-3 | Runtime Truth Repair | WS-2 | Validation and commit can only preserve fields that exist in the contract. |
| WS-4 | Agency Upgrade | WS-3 | Smarter responder logic must ride on reliable preserved truth. |
| WS-5 | Telemetry + Docs Hardening | WS-1..WS-4 (incremental) | Operator truth and docs must reflect actual behavior at each stage. |

## Workstream Plan

### WS-1 — Surface Repair (Visibility First)

**Goal:** make runtime turn output visible in the active shell.

**Primary file targets**

1. `frontend/templates/session_shell.html`
2. `frontend/static/play_shell.js`
3. `frontend/app/routes_play.py`
4. `frontend/app/routes.py` (only if route wiring is needed)
5. `frontend/tests/test_routes_extended.py`

**Tasks**

1. Add a persistent story-output panel with latest turn and recent history.
2. Render returned turn/state payload after each posted turn.
3. Render websocket updates as visible state changes (not transport-only notices).
4. Add degraded/fallback banner and selected responder visibility when present.
5. Remove or reduce redirect/flash-only behavior that discards view state.

**Acceptance criteria**

1. Submitting a turn renders visible story output in shell DOM.
2. Spoken/action lines show when returned by runtime.
3. Websocket updates mutate visible content.
4. Degraded/fallback state is visible to player/operator.
5. Frontend tests verify at least one returned turn appears in DOM.

### WS-2 — Contract Repair (Actor-Level Output Contract)

**Goal:** replace narration-first payload handling with actor-level dramatic contract.

**Primary file targets**

1. `ai_stack/langchain_integration/bridges.py`
2. `ai_stack/langgraph_runtime.py`
3. `ai_stack/langgraph_runtime_executor.py`
4. `ai_stack/langgraph_runtime_state.py`
5. `ai_stack/langgraph_runtime_package_output_sections.py`
6. `ai_stack/goc_turn_seams.py`
7. `ai_stack/tests/` (new contract/normalize tests)

**Tasks**

1. Define canonical structured turn schema with first-class `spoken_lines` and `action_lines`.
2. Add compatibility adapter for narrative-only legacy payloads during migration.
3. Preserve actor-level lanes through normalize/package seams.
4. Pass director/planner packet into generation input explicitly:
   selected responder set, scene function, pacing, silence/brevity, character minds, continuity constraints, pressure, and active scene packet.
5. Rewrite generation instructions around actor exchange (speech/action/initiative), not recap prose.

**Acceptance criteria**

1. Structured actor payload parses and survives normalize/package.
2. Snapshot/trace tests prove planner fields reach invoke layer.
3. Legacy narrative-only payloads still execute during migration window.
4. Regression tests prove non-empty `spoken_lines` are not dropped.

### WS-3 — Runtime Truth Repair (Validate + Commit + Projection)

**Goal:** preserve actor-level truth across validation and persistence.

**Primary file targets**

1. `ai_stack/langgraph_runtime_executor.py` (`validate_seam` and related)
2. `ai_stack/dramatic_effect_gate_evaluate_core.py` and related gate seams (as needed)
3. `world-engine/app/story_runtime/commit_models.py`
4. `world-engine/app/story_runtime/manager.py`
5. `world-engine/app/story_runtime_shell_readout.py`
6. `world-engine/tests/test_story_window_projection.py`
7. `world-engine/tests/test_story_runtime_shell_readout.py`
8. `ai_stack/tests/` and `world-engine/tests/` for actor-level validation/commit tests

**Tasks**

1. Extend validation to actor legality/coherence:
   responder legality, speaker legality, action legality, initiative legality, continuity compatibility.
2. Add lightweight actor-level commit summary fields:
   `primary_responder_id`, `spoken_line_count`, `action_line_count`, `initiative_summary`, `last_actor_outcome_summary`.
3. Ensure story-window/shell projection includes narration + actor lanes + degraded markers.
4. Prevent silent flattening of valid actor-level output into narrator-only fallback text.

**Acceptance criteria**

1. Valid multi-line actor response passes validation without flattening.
2. State/story endpoints expose actor-level outcome summary fields.
3. Turn N+1 can access turn N actor-level outcome context.
4. Shell readout/story window carry spoken/action lanes reliably.

### WS-4 — Agency Upgrade (Runtime Vitality)

**Goal:** improve reactivity under pressure, sparse input, and multi-actor dynamics.

**Primary file targets**

1. `ai_stack/scene_director_goc.py`
2. `ai_stack/langgraph_runtime_executor.py`
3. `ai_stack/langgraph_runtime.py`
4. `ai_stack/story_runtime_experience.py`
5. `story_runtime_core/model_registry.py` (if routing heuristics require)
6. `ai_stack/tests/test_scene_director_goc_extended.py`
7. `ai_stack/tests/` (new sparse-input and multi-actor scenarios)

**Tasks**

1. Upgrade from single responder to responder-set selection:
   primary responder, optional secondary reactor, optional interruption candidate.
2. Rebalance sparse-input behavior so one-word/evasive/silence-adjacent turns still produce meaningful drama.
3. Replace first-hit interpretation with ranked interpretation carrying primary + secondary dramatic features.
4. Add drama-aware routing inputs: pressure, actor count, escalation density, dialogue complexity.

**Acceptance criteria**

1. Tests prove multi-actor reactions occur when pressure warrants.
2. Sparse/evasive player input still yields meaningful dramatic output.
3. Runtime logs/trace expose responder sets and interpretation rank data.
4. Governance compatibility remains intact.

### WS-5 — Telemetry, Diagnostics, and Docs Truth

**Goal:** make agency degradation diagnosable and claims honest.

**Primary file targets**

1. `ai_stack/langgraph_runtime_package_output.py`
2. `ai_stack/langgraph_runtime_package_output_repro.py`
3. `ai_stack/goc_turn_seams.py`
4. `frontend/app/routes_play.py` (operator payload display path)
5. `docs/` runtime and operator documentation pages
6. `README.md` and/or relevant runtime docs index entries

**Tasks**

1. Add actor-survival telemetry per turn:
   selected responders, scene function, primary invoke/fallback path, spoken lines generated/validated/rendered/frontend-visible, degraded flag.
2. Ensure degraded/fallback markers are explicit in payloads, UI, and diagnostics.
3. Upgrade operator turn-history surfaces to include responder, validation result, render summary, fallback truth.
4. Publish agency capability matrix and align mode documentation with actual capability.

**Acceptance criteria**

1. Operators can identify where actor behavior was lost (generation, validation, projection, or frontend).
2. Fallback/mock turns cannot be mistaken for fully live turns.
3. Docs no longer overstate agency capabilities.

## Test Plan

### Unit tests

1. Structured dramatic payload parsing.
2. `spoken_lines` and `action_lines` preservation.
3. Actor-level validation legality checks.
4. Actor-level commit summary persistence.
5. Sparse-input vitality behavior.
6. Responder-set selection logic.

### Integration tests

1. Planner outputs are present at generation invoke.
2. Actor-level output survives normalize -> validate -> commit.
3. Visible output bundle includes actor lanes.
4. Degraded markers appear when fallback path is used.

### Frontend tests

1. Posted turn renders visible story content.
2. Spoken lines appear in shell transcript.
3. Websocket updates mutate visible shell content.
4. Shell is not transport-only success messaging.

### Scenario tests

1. Provocation.
2. Repair attempt.
3. Silence-adjacent/evasive input.
4. Escalation and interruption-capable scene.

## Ordered Execution Plan

1. WS-1 Surface Repair.
2. WS-2 Contract Repair.
3. WS-3 Runtime Truth Repair.
4. WS-4 Agency Upgrade.
5. WS-5 Telemetry + Docs Hardening (incremental, finalized after WS-4).

## Risks and Mitigations

1. **Partial migration mismatch**  
   Mitigation: schema version + legacy compatibility adapter.
2. **Over-verbose NPC behavior after sparse-input rebalance**  
   Mitigation: scenario tuning and mode-level density controls.
3. **Validation complexity growth**  
   Mitigation: first pass validates legality/coherence, not full simulation.
4. **Frontend churn**  
   Mitigation: ship minimal story panel first, iterate layout later.

## Post-audit scope notes

- `multi_actor_realized` and the `multi_actor_render` bundle are emitted only on the **committed + approved** primary render path in `ai_stack/goc_turn_seams.py`. Authoritative wording lives under **Multi-Actor Realization → Known limits** in `AGENCY_CAPABILITY_MATRIX.md`.

## Definition of Done

The task is complete only when:

1. players visibly receive actor speech/action in the active shell,
2. planner dramatic state reaches generation,
3. actor-level output survives validation and commit,
4. fallback/degraded behavior is explicit across runtime and UI,
5. multi-actor and sparse-input scenarios show materially stronger reactivity,
6. operator telemetry can prove where behavior survived or degraded.
