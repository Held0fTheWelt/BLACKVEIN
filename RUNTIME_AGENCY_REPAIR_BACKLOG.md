# Runtime Agency Repair Backlog (Execution-Ready)

## Planning Assumptions

1. Source task: `/mnt/d/WorldOfShadows/RUNTIME_AGENCY_REPAIR_TASK.md`
2. Estimation scale: S (0.5-1 day), M (1-2 days), L (3-4 days), XL (5+ days)
3. Owners are role-based lanes (can be mapped to people later)
4. Work is dependency-ordered; parallelization is allowed only where dependencies permit

## Milestone A — Visibility Unblock (WS-1)

### A1 — Story Output Panel in Shell
- **Owner:** Frontend
- **Estimate:** M
- **Depends on:** None
- **Files:** `/mnt/d/WorldOfShadows/frontend/templates/session_shell.html`, `/mnt/d/WorldOfShadows/frontend/static/play_shell.js`
- **Deliverable:** Persistent runtime output panel with latest turn + short history
- **Test gate:** Frontend test confirms turn output appears in DOM

### A2 — Render POST Turn Payload as Persistent State
- **Owner:** Frontend + Frontend API Integration
- **Estimate:** M
- **Depends on:** A1
- **Files:** `/mnt/d/WorldOfShadows/frontend/app/routes_play.py`, `/mnt/d/WorldOfShadows/frontend/templates/session_shell.html`
- **Deliverable:** Turn response is rendered in-page; not only transient success/flash
- **Test gate:** Route test proves returned turn payload is visible after submit

### A3 — WebSocket Runtime Rendering
- **Owner:** Frontend
- **Estimate:** M
- **Depends on:** A1
- **Files:** `/mnt/d/WorldOfShadows/frontend/static/play_shell.js`
- **Deliverable:** WebSocket updates mutate visible runtime content
- **Test gate:** Frontend test verifies live update changes visible story panel

### A4 — Degraded/Fallback UI Banner
- **Owner:** Frontend + Runtime API Integration
- **Estimate:** S
- **Depends on:** A2
- **Files:** `/mnt/d/WorldOfShadows/frontend/templates/session_shell.html`, `/mnt/d/WorldOfShadows/frontend/static/play_shell.js`
- **Deliverable:** Explicit degraded/fallback banner in shell
- **Test gate:** Test case with degraded payload shows banner and marker text

## Milestone B — Contract Repair (WS-2)

### B1 — Canonical Actor-Level Output Schema
- **Owner:** AI Runtime
- **Estimate:** L
- **Depends on:** A2
- **Files:** `/mnt/d/WorldOfShadows/ai_stack/langchain_integration/bridges.py`, `/mnt/d/WorldOfShadows/ai_stack/langgraph_runtime_state.py`
- **Deliverable:** Structured turn schema with first-class actor lanes
- **Test gate:** Unit tests parse schema and validate required fields

### B2 — Legacy Payload Compatibility Adapter
- **Owner:** AI Runtime
- **Estimate:** M
- **Depends on:** B1
- **Files:** `/mnt/d/WorldOfShadows/ai_stack/langchain_integration/bridges.py`, `/mnt/d/WorldOfShadows/ai_stack/goc_turn_seams.py`
- **Deliverable:** Narrative-only payloads still execute during migration
- **Test gate:** Regression test for legacy payload remains green

### B3 — Dramatic Generation Packet Wiring
- **Owner:** AI Runtime
- **Estimate:** L
- **Depends on:** B1
- **Files:** `/mnt/d/WorldOfShadows/ai_stack/langgraph_runtime.py`, `/mnt/d/WorldOfShadows/ai_stack/langgraph_runtime_executor.py`, `/mnt/d/WorldOfShadows/ai_stack/langchain_integration/bridges.py`
- **Deliverable:** Planner outputs reach invoke layer in explicit packet
- **Test gate:** Snapshot/trace tests show responder/scene/pacing fields at invoke time

### B4 — Prompt Instruction Rewrite for Live Dramatic Exchange
- **Owner:** AI Runtime + Prompt Governance
- **Estimate:** M
- **Depends on:** B3
- **Files:** `/mnt/d/WorldOfShadows/ai_stack/langchain_integration/bridges.py` (and prompt source files if split)
- **Deliverable:** Actor-driven instructions for speech/action/initiative behavior
- **Test gate:** Scenario tests reduce recap-only outputs under sparse/evasive input

## Milestone C — Runtime Truth Preservation (WS-3)

### C1 — Actor-Level Validation Rules
- **Owner:** AI Runtime Validation
- **Estimate:** L
- **Depends on:** B1
- **Files:** `/mnt/d/WorldOfShadows/ai_stack/langgraph_runtime_executor.py`, `/mnt/d/WorldOfShadows/ai_stack/dramatic_effect_gate_evaluate_core.py`
- **Deliverable:** Validation checks legality/coherence without flattening actor lanes
- **Test gate:** Multi-line actor payload passes validation and remains structured

### C2 — Actor-Level Commit Summary Fields
- **Owner:** World Engine Runtime
- **Estimate:** M
- **Depends on:** C1
- **Files:** `/mnt/d/WorldOfShadows/world-engine/app/story_runtime/commit_models.py`, `/mnt/d/WorldOfShadows/world-engine/app/story_runtime/manager.py`
- **Deliverable:** Commit truth stores responder/action/initiative summary fields
- **Test gate:** State endpoint includes new actor-level summary fields

### C3 — Story Window and Shell Projection Integrity
- **Owner:** World Engine Runtime + Frontend Integration
- **Estimate:** M
- **Depends on:** C2, A3
- **Files:** `/mnt/d/WorldOfShadows/world-engine/app/story_runtime_shell_readout.py`, `/mnt/d/WorldOfShadows/world-engine/app/story_runtime/manager.py`
- **Deliverable:** Narration + spoken + action + degraded markers survive projection
- **Test gate:** Integration tests show non-empty actor lanes in story window + shell

## Milestone D — Agency Upgrade (WS-4)

### D1 — Responder-Set Selection
- **Owner:** AI Runtime Director
- **Estimate:** L
- **Depends on:** C1
- **Files:** `/mnt/d/WorldOfShadows/ai_stack/scene_director_goc.py`, `/mnt/d/WorldOfShadows/ai_stack/langgraph_runtime_executor.py`
- **Deliverable:** Primary + optional secondary/interruption responders
- **Test gate:** Tests prove multi-actor reaction on pressure-appropriate turns

### D2 — Sparse/Evasive Input Vitality Rebalance
- **Owner:** AI Runtime Director
- **Estimate:** M
- **Depends on:** D1
- **Files:** `/mnt/d/WorldOfShadows/ai_stack/scene_director_goc.py`, `/mnt/d/WorldOfShadows/ai_stack/story_runtime_experience.py`
- **Deliverable:** Short/evasive turns still produce meaningful dramatic response
- **Test gate:** Scenario tests for one-word/evasive/silence-adjacent inputs

### D3 — Ranked Semantic Interpretation
- **Owner:** AI Runtime Semantics
- **Estimate:** M
- **Depends on:** B3
- **Files:** `/mnt/d/WorldOfShadows/ai_stack/langgraph_runtime.py`, `/mnt/d/WorldOfShadows/ai_stack/langgraph_runtime_executor.py`
- **Deliverable:** Primary move plus secondary dramatic features passed downstream
- **Test gate:** Tests verify ranked interpretation appears in generation packet

### D4 — Drama-Aware Routing Inputs
- **Owner:** AI Runtime Routing
- **Estimate:** M
- **Depends on:** D1, D3
- **Files:** `/mnt/d/WorldOfShadows/story_runtime_core/model_registry.py`, `/mnt/d/WorldOfShadows/ai_stack/langgraph_runtime_executor.py`
- **Deliverable:** Route decisions include pressure/actor-count/dialogue-complexity signals
- **Test gate:** Routing tests show deterministic route variance by dramatic load

## Milestone E — Telemetry and Operator Truth (WS-5)

### E1 — Actor-Survival Telemetry Emission
- **Owner:** AI Runtime Observability
- **Estimate:** M
- **Depends on:** C3
- **Files:** `/mnt/d/WorldOfShadows/ai_stack/langgraph_runtime_package_output.py`, `/mnt/d/WorldOfShadows/ai_stack/goc_turn_seams.py`
- **Deliverable:** Per-turn survival counters from generation to frontend
- **Test gate:** Integration tests assert presence of required telemetry keys

### E2 — Explicit Degraded/Fallback Markers End-to-End
- **Owner:** AI Runtime + Frontend Integration
- **Estimate:** S
- **Depends on:** E1, A4
- **Files:** `/mnt/d/WorldOfShadows/ai_stack/langgraph_runtime_package_output_repro.py`, `/mnt/d/WorldOfShadows/frontend/app/routes_play.py`
- **Deliverable:** Fallback cannot look identical to full live turn
- **Test gate:** Degraded test path shows marker in payload and visible UI

### E3 — Operator Turn-History Surface Upgrade
- **Owner:** World Engine Runtime + Frontend
- **Estimate:** M
- **Depends on:** E1
- **Files:** `/mnt/d/WorldOfShadows/frontend/app/routes_play.py`, `/mnt/d/WorldOfShadows/frontend/templates/session_shell.html`
- **Deliverable:** Operator view includes responder, validation, render, fallback summary
- **Test gate:** Route/UI test verifies enriched operator history fields

### E4 — Capability Matrix and Docs Alignment
- **Owner:** Docs + Runtime Leads
- **Estimate:** S
- **Depends on:** D4, E2
- **Files:** `/mnt/d/WorldOfShadows/docs/` (runtime/operator pages), `/mnt/d/WorldOfShadows/README.md` (if needed)
- **Deliverable:** Published agency capability matrix aligned with true behavior
- **Test gate:** Manual documentation review checklist completed

## Suggested Sprint Packaging

1. **Sprint 1:** A1-A4, B1 (visibility + schema start)
2. **Sprint 2:** B2-B4, C1 (contract and validation baseline)
3. **Sprint 3:** C2-C3, D1-D2 (truth preservation + vitality)
4. **Sprint 4:** D3-D4, E1-E4 (sophistication + observability + docs hardening)

## Global Exit Gates

1. Player shell visibly renders spoken/action output in normal runtime path.
2. Planner packet fields are present at generation invoke.
3. Actor-level fields survive validate -> commit -> projection.
4. Fallback/degraded state is explicit in payload and UI.
5. Multi-actor and sparse-input scenarios show stronger reactivity.
6. Operator telemetry can localize where actor behavior is lost.

## Post-audit follow-up (non-blocking)

### Test proof distribution

Proof for runtime agency gates is strongest in a few targeted vertical tests (`ai_stack/tests/test_wave1_closure_actor_contract.py`, `test_wave2_actor_truth_preservation.py`, `test_wave3_multi_actor_vitality.py`, etc.). Over time, when the next implementation phase touches a path, migrate or duplicate **one** high-value assertion per area into an additional gate-adjacent module so coverage is less concentrated in a single file per concern.

Render-path and operator-vs-audit semantics are documented in `AGENCY_CAPABILITY_MATRIX.md` (Multi-Actor Realization known limits; Contract Rules — operator vs audit).
