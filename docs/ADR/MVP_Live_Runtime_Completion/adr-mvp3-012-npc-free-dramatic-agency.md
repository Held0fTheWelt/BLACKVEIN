# ADR-MVP3-012: NPC Free Dramatic Agency

**Status**: Accepted
**MVP**: 3 — Live Dramatic Scene Simulator
**Date**: 2026-04-26

## Context

MVP2 established that NPCs are AI-controlled actors and the human actor is protected from AI control. MVP3 must go further: NPCs must have genuine free dramatic agency — the ability to initiate, address each other, react without being prompted, and pursue their own dramatic line within the scene.

A passive NPC that only responds when directly addressed violates the live dramatic scene simulator contract. NPCs must be assertive, autonomous dramatic agents.

## Decision

1. **NPCAgencyPlan** is the initiative contract. LDSS emits an `NPCAgencyPlan` per turn with `primary_responder_id`, `secondary_responder_ids`, and `npc_initiatives` (per-NPC intent, allowed block types, and target actor).

2. **Primary NPC initiative**: The primary responder speaks or acts first. Selection priority: `veronique` → `alain` → `michel` (Véronique is the most dramatically assertive in God of Carnage).

3. **Secondary NPC initiative**: The secondary NPC reacts to the primary NPC or to the scene state. This is NPC-to-NPC interaction — the human actor is not required as a bridge.

4. **No direct address required**: NPCs may speak or act without being addressed by name in the player's input. Player input is dramatic context, not a command prompt.

5. **Responder candidate exclusion**: Human actor and `visitor` are never in the responder candidate set. `validate_responder_candidates()` enforces this.

6. **Multiple NPC participation**: More than one NPC may participate in a single turn (primary + secondary). `NPCAgencyPlan.secondary_responder_ids` lists additional participants.

7. **NPC-to-NPC `target_actor_id`**: A block may target another NPC as its `target_actor_id`. This proves NPC-to-NPC dramatic exchange without human actor mediation.

## Affected Services/Files

- `ai_stack/live_dramatic_scene_simulator.py` — `NPCAgencyPlan`, `NPCInitiative`, `validate_responder_candidates()`, `_select_primary_responder()`, `build_deterministic_ldss_output()`
- `ai_stack/contracts/npc_agency_contracts.py` — shared runtime contract normalization for the current `npc_agency_simulation.v1` surface, durable closure constants, human/visitor exclusion, and the internal `npc_agency_plan.v1` adapter.
- `ai_stack/story_runtime/npc_agency/npc_agency_planner.py` — deterministic independent NPC roster planner for `npc_agency_simulation.v1`, including candidate scoring, carry-forward pressure, and NPC-to-NPC target graph projection.
- `ai_stack/story_runtime/npc_agency/npc_agency_long_horizon.py` — deterministic `npc_long_horizon_state.v1`, `npc_intention_thread.v1`, `npc_private_plan.v1`, and `npc_plan_conflict_resolution.v1` builders.
- `ai_stack/story_runtime/npc_agency/npc_agency_claim_readiness.py` — evidence gate for bounded, live-staging-ready, and full long-horizon claim states.
- `ai_stack/story_runtime/npc_agency/npc_agency_realization.py` — shared realization, validation, and durable closure helpers for `npc_initiative_realization_v1`, `npc_initiative_validation_v1`, and `npc_agency_closure.v1`.
- `ai_stack/story_runtime/runtime_aspect_ledger.py` — `npc_agency` runtime aspect projection for candidate, planned, realized, missing, carry-forward, closure, and scoring evidence.
- `ai_stack/story_runtime/story_runtime_playability.py` — recoverable rewrite feedback for missing required NPC initiative without allowing degraded commit to hide it.
- `ai_stack/langgraph/langgraph_runtime_executor.py` — model-visible current NPC agency simulation projection, bounded initiative directives, validation-aspect wiring, and self-correction trigger surface.
- `ai_stack/telemetry/actor_survival_telemetry.py` — vitality telemetry projection of candidate, planned, realized, missing, required, and carry-forward NPC initiatives.
- `ai_stack/story_runtime/narrative_runtime_agent.py` — ruhepunkt pressure analysis reads the v1 `npc_initiatives` contract.
- `world-engine/app/story_runtime/commit_models.py` — persists `npc_agency_simulation`, long-horizon state, private plans, conflict resolution, `npc_agency_closure`, and unresolved carry-forward rows in committed planner truth.
- `world-engine/app/story_runtime/manager.py` — rehydrates carry-forward planner truth and emits Langfuse NPC agency spans and deterministic scores.
- `backend/app/services/story_runtime/operator_turn_history_service.py` — exposes operator-facing NPC agency breakdowns from telemetry, aspect ledger, and committed closure truth.
- `tools/mcp_server/tools_registry_handlers_langfuse_verify.py` — exposes NPC agency deterministic scores and matrix columns through MCP Langfuse verification.
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py` — `test_mvp3_gate_npcs_act_without_direct_address`, `test_mvp3_gate_multiple_npcs_can_participate`, `test_mvp3_gate_responder_candidates_exclude_human_and_visitor`
- `ai_stack/tests/test_npc_agency_planner.py` — current simulation, independent roster planning, durable carry-forward, and closure coverage.
- `ai_stack/tests/test_npc_agency_contracts.py` — adapter normalization, required realization, NPC-to-NPC target, and human/visitor exclusion coverage for current contract surfaces.
- `ai_stack/tests/test_narrative_runtime_agent.py` — coverage that `NarrativeRuntimeAgent` consumes v1 `npc_initiatives`.

## Current Implementation Status (Pi7 Long-Horizon Runtime Slice)

As of the 2026-05-15 Pi7 long-horizon runtime slice, this ADR has an implementation-ready deterministic long-horizon path, but not a full live-staging closure claim. The current primary contract is `npc_agency_simulation.v1`; `npc_agency_plan.v1` remains an internal adapter surface for existing realization helpers and compatibility, not the promoted proof target.

Implemented now:

- `npc_agency_simulation.v1` is emitted as the primary LangGraph dramatic packet surface with `contract_status = implemented_runtime_simulation`, `not_full_multi_agent_simulation = false`, and `independent_planning_used = true`.
- The planner derives the candidate NPC roster from actor-lane context, selected responders, mind records, and unresolved prior closure truth rather than relying only on directly selected responders.
- Independent NPC intent proposals include stable actor ids, requirement scopes, target actors, source evidence, and a deterministic interaction graph.
- `npc_long_horizon_state.v1` carries per-NPC actor states and active intention threads from committed planner truth into later turns.
- `npc_private_plan.v1` records per-NPC private plan rows derived from the current simulation and long-horizon state.
- `npc_plan_conflict_resolution.v1` selects the visible private plans for the current turn and records withheld private plan ids without exposing hidden intent prose.
- Human actor aliases and `visitor` are excluded from planned NPC initiative actors.
- `npc_initiative_realization_v1` records planned, realized, missing, required, event-only, and multi-NPC realization fields.
- `npc_initiative_validation_v1` can reject or degrade missing required NPC initiative, selected private-plan realization gaps, private-plan visibility violations, and forbidden actor participation.
- `npc_agency_closure.v1` persists unresolved required NPC initiatives, carried private plan ids, and carried intention thread ids into committed planner truth and rehydrates them into the next turn.
- Missing required NPC initiative is surfaced through the `npc_agency` runtime aspect and becomes recoverable self-correction feedback; it is not silently accepted as a degraded commit.
- Langfuse/runtime aspect scoring now records NPC agency planning, independent planning, long-horizon state presence, private-plan resolution, private-plan visibility, required realization, multi-NPC realization, carry-forward closure, and forbidden-actor absence.
- Operator turn history and MCP Langfuse verification expose candidate, planned, realized, missing, carry-forward, long-horizon, private-plan, and claim-readiness NPC agency fields.
- `NarrativeRuntimeAgent` reads `npc_initiatives` so ruhepunkt pressure is aligned with the v1 contract.

Still not claimed:

- Unbounded per-NPC agent processes or an LLM swarm.
- Full staging proof across live provider traces, operator workflows, MCP export, and player-facing replay.
- A capability-matrix claim that Π7 is fully implemented before `npc_agency_claim_readiness.v1` allows the full long-horizon claim.

## Consequences

- NPCs are autonomous dramatic agents, not prompted responders
- Human actor is never in the responder candidate set
- `visitor` is never in the responder candidate set
- Multi-NPC turns are valid and expected when 2+ NPCs are in the session
- Responder selection is traceable in `diagnostics.npc_agency`

## Diagrams

**`NPCAgencySimulation`** derives the NPC roster, picks required initiatives, allows **NPC→NPC** pressure edges, carries unresolved initiatives forward, and never nominates the **human** (or `visitor`) as responder.

```mermaid
flowchart TB
  SIM[NPCAgencySimulation] --> ROSTER[candidate_actor_ids]
  SIM --> PROPOSALS[npc_intent_proposals]
  PROPOSALS --> GRAPH[npc_interaction_graph]
  PROPOSALS --> LONG[npc_long_horizon_state]
  LONG --> PRIVATE[npc_private_plan]
  PRIVATE --> RESOLVE[npc_plan_conflict_resolution]
  RESOLVE --> CLOSURE[npc_agency_closure]
  CLOSURE --> NEXT[Next-turn planner truth]
```

## Alternatives Considered

- Single-NPC-per-turn restriction: rejected — limits dramatic richness and prevents NPC-to-NPC exchanges
- Human actor as implicit responder: rejected — violates actor lane enforcement (ADR-MVP2-004)

## Validation Evidence

- `test_mvp3_gate_npcs_act_without_direct_address` — PASS
- `test_mvp3_gate_multiple_npcs_can_participate` — PASS
- `test_mvp3_gate_responder_candidates_exclude_human_and_visitor` — PASS
- `test_mvp3_gate_human_actor_not_generated_as_speaker` — PASS
- `test_mvp3_gate_human_actor_not_generated_as_actor` — PASS
- `pytest ai_stack/tests/test_npc_agency_long_horizon_claim_readiness.py ai_stack/tests/test_npc_agency_planner.py ai_stack/tests/test_npc_agency_contracts.py -q --tb=short` — PASS (18 passed, local Pi7 long-horizon contracts)
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows pytest world-engine/tests/test_planner_truth_and_runtime_surfaces.py world-engine/tests/test_story_runtime_narrative_threads.py::test_prior_planner_truth_passed_to_graph_from_committed_truth -q --tb=short` — PASS (8 passed, committed planner-truth and rehydration slice)
- `pytest ai_stack/tests/test_runtime_aspect_ledger.py -q --tb=short` — PASS (3 passed, runtime aspect projection)
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows pytest world-engine/tests/test_trace_middleware.py::test_langfuse_emits_runtime_aspect_spans_and_reasoned_scores -q --tb=short` — PASS (1 passed, Langfuse deterministic scoring)
- `PYTHONPATH=/mnt/d/WorldOfShadows pytest tools/mcp_server/tests/test_langfuse_verify_tools.py -q` — PASS (29 passed, MCP Langfuse verify)
- `PYTHONPATH=/mnt/d/WorldOfShadows/backend:/mnt/d/WorldOfShadows pytest backend/tests/services/test_operator_turn_history_service.py -q --tb=short` — PASS (4 passed, operator turn-history surface)
- `pytest tests/gates/test_table_b_anti_hardcoding_gate.py -q` — PASS (ADR-0039 guard for non-example-shaped tests)

## Related ADRs

- ADR-MVP2-004 (Actor Lane Enforcement)
- ADR-MVP3-007 (Minimum Agency Baseline Superseded)
- ADR-MVP3-011 (Live Dramatic Scene Simulator Contract)
