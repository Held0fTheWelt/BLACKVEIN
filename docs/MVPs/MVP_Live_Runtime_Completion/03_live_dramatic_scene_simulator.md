# MVP_Live_Runtime_Completion — MVP 3 — Live Dramatic Scene Simulator

## Mission

Implement the live dramatic scene simulator (LDSS) and the narrative runtime agent as non-optional live-path components that together produce a continuous, interactive dramatic experience for God of Carnage solo play.

LDSS generates NPC behavior, agency plans, and scene blocks. NarrativeRuntimeAgent streams continuous narrator prose, fills silence based on motivation pressure, and validates that narrative output does not block player agency. Together they respect MVP 2 actor lanes, object admission, and state-delta boundaries while creating a runtime environment where narrator, NPCs, and player act together (not sequentially).

## Scope

In scope:

- **LDSS Module**: `LDSSInput` and `LDSSOutput` contracts; `NPCAgencyPlan` with non-passive NPC decisions.
- **Narrative Runtime Agent**: `NarrativeRuntimeAgent` that streams continuous narrator blocks based on `RuntimeState` and `NPCAgencyPlan`; motivation-aware silence-filling; input-blocking while streaming.
- **Event-based Runtime Environment**: Story runtime loop where narrator, NPCs, and player act asynchronously (not turn-sequential); player input can arrive at any time; narrator fills gaps based on NPC motivation pressure.
- `SceneTurnEnvelope.v2` as final live turn output shape (now includes narrative streaming metadata).
- `SceneBlock` for narrator, actor line, actor action, environment interaction, and system degraded notice.
- EnvironmentInteraction with canonical, typical, and `similar_allowed` affordance validation.
- NarratorVoiceValidation and PassivityValidation (narrator cannot block player agency).
- Live-path proof from HTTP turn route through Story Runtime Manager, LDSS, NarrativeRuntimeAgent, validation, commit, and response packaging.
- Optional Langfuse instrumentation (infrastructure; UI deferred to MVP 4).

Out of scope:

- Langfuse/Narrative Gov final UI; MVP 3 emits trace scaffold consumed by MVP 4.
- Final frontend typewriter UX; MVP 3 emits renderable blocks and streaming metadata consumed by MVP 5.
- Admin UI for Langfuse Tracing Toggle (deferred to MVP 4).

## Base Contract

A real `live_dramatic_scene_simulator` runs in the live play path and renders a continuous, interactive dramatic experience where narrator, NPCs, and player act together.

**Runtime Model (Event-based, not turn-sequential):**
- Story Runtime Manager orchestrates LDSS (generates NPC behavior) and NarrativeRuntimeAgent (streams narrator prose).
- Narrator streams continuously, filling silence with perception/orientation based on NPC motivation pressure (dramatic signature, narrative threads, pressure summary from `RuntimeState`).
- NPCs act autonomously (per `NPCAgencyPlan`). NPC-to-NPC interaction does not require human actor mediation.
- Player input can arrive at any time. When narrator is streaming, input is queued. When narrator reaches motivation-based ruhepunkt (no further NPC initiatives planned), input is processed → next turn.
- Narrator must not block player agency: cannot force player state, predict player choice, or reveal hidden NPC intent.

**Dramatic Elements:**
- The player chooses Annette or Alain (human-controlled). The other canonical God of Carnage characters (Alain, Véronique, Michel) are free NPC dramatic actors.
- NPCs speak, act, pursue their own line, interact with each other, and interact with the environment through canonical, typical, or `similar_allowed` affordances. NPCs may use admitted objects with or against other actors when valid and non-coercive.
- The Narrator is the player's inner perception/orientation voice, filling gaps between actor agency. Not a dialogue summarizer.

**Proof of Live Path:**
Diagnostics, Narrative Gov, optional Langfuse tracing (enabled/disabled via MVP 4 admin toggle), and deterministic trace export prove the live runtime path. `docker-up.py`, `tests/run_tests.py`, GitHub workflows, and TOML/tooling configs remain fully functional. Partial foundation is not acceptable.

### Global Prohibitions

- Do not reintroduce `visitor` as a story actor, runtime participant, prompt role, responder, lobby seat, frontend role, or fallback alias.
- Do not convert `god_of_carnage_solo` into a content module.
- Do not place canonical God of Carnage story truth in a runtime profile or runtime module.
- Do not allow AI output to speak, act, emote, decide, or physically move for the selected human actor.
- Do not accept legacy blob output as canonical final output.
- Do not accept mock-only Langfuse or hand-written trace JSON as final proof.
- Do not accept field presence as behavior.
- Do not close the MVP if `docker-up.py`, `tests/run_tests.py`, GitHub workflows, or TOML/tooling are broken.
- Do not implement later MVPs except for explicit scaffolds and handoff contracts named in this guide.

## Final Target Dependency

MVP 3 is the final behavior core. LDSS is non-optional and final. A narrator-only output, a single legacy blob, an empty `evidenced_live_path` status, or passive NPCs is not acceptable.

## Inputs from Previous MVP

| Input | Source MVP | Required Fields | Evidence Path |
|---|---|---|---|
| RuntimeState | MVP 2 | source hashes, scene state, actor lanes, admitted objects | `tests/reports/MVP2_HANDOFF_RUNTIME_STATE.md` |
| StorySessionState | MVP 2 | turn number, selected role, human/NPC actor IDs | `tests/reports/MVP2_HANDOFF_RUNTIME_STATE.md` |
| ActorLaneContext | MVP 2 | AI allowed/forbidden actor IDs | `tests/reports/MVP2_HANDOFF_ACTOR_LANES.md` |
| ObjectAdmissionRecord set | MVP 2 | canonical/typical/similar admission status | object admission tests |
| StateDeltaBoundary | MVP 2 | protected paths and whitelist | state-delta tests |

## This MVP Produces

| Output | Consumed By | Required Fields | Evidence Path |
|---|---|---|---|
| SceneTurnEnvelope.v2 | MVP 4/5 | non-empty visible_scene_output.blocks, actor lanes, diagnostics scaffold | integration test artifact |
| LDSS live-path evidence | MVP 4 | real turn entrypoint, input hash, output hash, decision count, block count | `tests/reports/MVP3_LDSS_LIVE_PATH_EVIDENCE.md` |
| Trace scaffold | MVP 4 | span names, decision IDs, validation outcomes | trace scaffold artifact |
| Frontend render contract scaffold | MVP 5 | block IDs, block types, delivery hints | response fixture |

## Deferred Admin Surfaces

The following infrastructure decisions are **locked**, but **operator UI is deferred to MVP 4**:

### Object Admission Override Admin Surface (from MVP 2)
- **Decision Source**: ADR-MVP2-015 (Canonical, Typical, and Similar Environment Affordances)
- **Infrastructure Present**: `admit_object()` validator and `ObjectAdmissionRecord` tier enforcement (all tests PASS)
- **Admin UI Deferred**: Operator interface to override admission tier (e.g., canonical→temporary) not implemented in MVP 3
- **Will be implemented in MVP 4** alongside Narrative Gov operator surfaces

### State Delta Boundary Override Admin Surface (from MVP 2)
- **Decision Source**: ADR-MVP2-003 (NPC Coercion), ADR-MVP2-016 (Operational Gates)
- **Infrastructure Present**: `validate_state_delta()` enforces protected paths with audit intent (all tests PASS)
- **Admin UI Deferred**: Operator interface for breakglass unlocking of protected paths not implemented in MVP 3
- **Will be implemented in MVP 4** alongside Narrative Gov operator surfaces

### Langfuse Tracing Toggle Admin Surface (new in MVP 3)
- **Decision Source**: Event-based Runtime Architecture — Tracing must be optional (default JSON scaffold, optional live Langfuse)
- **Infrastructure Present**: NarrativeRuntimeAgent accepts `enable_langfuse_tracing` config parameter; can emit traces or JSON scaffold
- **Default**: JSON scaffold (Trace metadata without live Langfuse SDK calls)
- **Enabled**: Live Langfuse spans during LDSS + NarrativeRuntimeAgent execution
- **Configuration**: Environment variable (`ENABLE_LANGFUSE_TRACING`) or runtime config
- **Admin UI Deferred**: Administration-tool switch to enable/disable live Langfuse tracing per session (MVP 4)
- **Will be implemented in MVP 4** alongside Narrative Gov admin surfaces

**Why deferred?**
- MVP 3 focuses on live LDSS + NarrativeRuntimeAgent behavior proof; Langfuse integration is observability fine-tuning
- MVP 4 consolidates all operator surfaces (Narrative Gov health + Object Admission + State Delta overrides + Langfuse toggle) in administration-tool
- All validator functions and infrastructure exist; only UI implementation is deferred

**Handoff reference**: `tests/reports/MVP_Live_Runtime_Completion/GOC_MVP2_HANDOFF_TO_MVP3.md` documents deferred admin UIs with implementation checklist for MVP 4.

## Consumed By Next MVP

MVP 4 consumes LDSS live path, scene blocks, simulator diagnostics scaffold, trace scaffold, validation outcomes, passivity status, and degradation signals. MVP 4 also implements the deferred Object Admission and State Delta Boundary admin override surfaces.

## Services Touched

| Service | Purpose |
|---|---|
| world-engine / play-service | Story Runtime Manager orchestrates LDSS + NarrativeRuntimeAgent; HTTP turn route integration; input-blocking/queuing logic; commit path |
| ai_stack | LDSS module (NPC behavior, NPCAgencyPlan); NarrativeRuntimeAgent module (narrator streaming, motivation-aware ruhepunkt, narrative validation) |
| backend | pass-through of final SceneTurnEnvelope response if backend proxies play-service |
| tests/tooling | unit, integration, and live-route tests for LDSS and NarrativeRuntimeAgent |

## Files to Inspect First

- `world-engine/app/api/http.py` — HTTP turn route, request/response models.
- `world-engine/app/runtime/manager.py` — story turn execution and commit seam.
- `ai_stack/langgraph_runtime.py` — graph construction and story turn path.
- `ai_stack/goc_turn_seams.py` — `run_visible_render()`, proposal packaging, passivity guard seam.
- `ai_stack/live_dramatic_scene_simulator.py` or create equivalent — LDSS implementation.
- `ai_stack/validators/narrator*` or create equivalent — NarratorVoiceValidation.
- `ai_stack/validators/affordance*` or create equivalent — affordance validation.
- `world-engine/app/runtime/actor_lane.py`, `object_admission.py`, `state_delta.py` — MVP 2 validators to consume.
- `tests/` — live turn integration tests.

## Do Not Touch

- Do not loosen MVP 2 actor-lane enforcement.
- Do not create a parallel fake turn path to prove LDSS.
- Do not set `evidenced_live_path` from unit-only construction, mocks, fixtures, or report text.
- Do not implement final Narrative Gov UI or frontend typewriter renderer.
- Do not accept legacy output as final.

## Targeted Search Commands

```bash
rg "story.turn.execute|turn.execute|execute_turn|run_visible_render|package_output|commit" -n world-engine ai_stack backend tests
rg "live_dramatic_scene_simulator|LDSS|SceneTurnEnvelope|visible_scene_output|SceneBlock" -n world-engine ai_stack tests docs
rg "narrator|inner voice|dialogue summary|passivity|no_visible_actor_response" -n ai_stack world-engine tests docs
rg "affordance|similar_allowed|canonical|typical|environment_interaction" -n ai_stack world-engine tests docs
```

### Source Locator Matrix

Before patching, fill this matrix in the implementation report. Do not continue until each relevant row has a concrete repository path or is marked `not_present` with the closest equivalent.

| Area | Expected Path | Actual Path | Symbol / Anchor | Status |
|---|---|---|---|---|
| backend route | from patch map | fill during implementation | route or blueprint | found/not_present |
| backend service | from patch map | fill during implementation | service function/class | found/not_present |
| backend content loader/compiler | from patch map | fill during implementation | content load/compile symbol | found/not_present |
| world-engine API | from patch map | fill during implementation | request/response model | found/not_present |
| world-engine runtime manager | from patch map | fill during implementation | `create_run`, `_bootstrap_instance`, or equivalent | found/not_present |
| world-engine story runtime | from patch map | fill during implementation | turn execution seam | found/not_present |
| ai_stack graph/seam | from patch map | fill during implementation | graph node / seam function | found/not_present |
| ai_stack validator | from patch map | fill during implementation | validator function | found/not_present |
| frontend route/template/static | from patch map | fill during implementation | route/template/JS renderer | found/not_present |
| administration-tool route/template/static | from patch map | fill during implementation | Narrative Gov route/template/static | found/not_present |
| tests | from patch map | fill during implementation | test module | found/not_present |
| reports | `tests/reports/` | fill during implementation | report artifact | found/not_present |
| ADRs | `docs/ADR/` | fill during implementation | ADR filename | found/not_present |
| docker-up.py | `docker-up.py` | fill during implementation | entrypoint | found/not_present |
| tests/run_tests.py | `tests/run_tests.py` | fill during implementation | suite registry | found/not_present |
| GitHub workflows | `.github/workflows/*.yml` | fill during implementation | job/matrix | found/not_present |
| TOML/tooling | `pyproject.toml` and service TOMLs | fill during implementation | testpaths/markers/pythonpath | found/not_present |

If a listed file is absent, locate the closest existing equivalent and record the replacement before patching.
### Source Locator Stop Gate

Do not begin code changes while the Source Locator Matrix contains unresolved placeholders.

The implementation report must fail the MVP gate if any relevant row still contains:

- `from patch map`
- `fill during implementation`
- `or equivalent` without a concrete replacement
- `not_present` without a closest existing replacement
- an empty `Symbol / Anchor` cell

Required validation:

```text
test_source_locator_matrix_has_no_placeholders_before_patch
```

Required error code:

```text
source_locator_unresolved
```

The final implementation report must include the completed matrix with actual repository paths and concrete symbols before any patch summary.

### Required Source Locator Artifact

Before any code patching, write the completed source locator matrix to:

```text
tests/reports/MVP_Live_Runtime_Completion/MVP<NUMBER>_SOURCE_LOCATOR.md
```

The artifact must include:

- every relevant expected path
- actual repository path
- actual class/function/symbol/anchor
- closest equivalent when the expected path differs
- `not_present` only when no equivalent exists
- reason why a missing source does not block the MVP
- tests that prove each source anchor is used

The MVP gate fails if this artifact is missing or contains unresolved placeholders.

Required error code:

```text
source_locator_artifact_missing
```

Required test:

```text
test_source_locator_artifact_exists_for_mvp
```
 MVP 1 may run as a locator-first pass, but no production patch may start while this gate is unresolved.


## Patch Map

| Patch ID | Area | Files / Symbols | Required Change | Tests |
|---|---|---|---|---|
| MVP3-P01 | LDSS module | `ai_stack/live_dramatic_scene_simulator.py` or equivalent | Implement LDSS input -> output with non-empty blocks and decision records. | `test_ldss_generates_scene_turn_envelope_v2` |
| MVP3-P02 | Live-path integration | HTTP turn -> Story Runtime Manager -> LDSS -> NarrativeRuntimeAgent -> validators -> commit -> response | Prove actual turn route invokes LDSS and NarrativeRuntimeAgent; no fake route. | `test_live_turn_route_invokes_ldss_and_narrative_agent` |
| MVP3-P03 | NPC agency | `NPCAgencyPlan`, responder plan seam | Require visible NPC actor response and allow NPC-to-NPC dialogue. | `test_npc_to_npc_dialogue_present`, `test_no_visible_actor_response_triggers_retry_or_degradation` |
| MVP3-P04 | Environment affordances | affordance validator, object admission consumer | Validate canonical/typical/similar and reject hallucinated objects. | `test_similar_allowed_requires_similarity_reason`, `test_rejects_unadmitted_plausible_object` |
| MVP3-P05 | Narrator contract | narrator validator | Narrator is inner perception/orientation only; reject recap/forced state/hidden intent. | narrator tests |
| MVP3-P06 | Final response guard | response packager | Reject no blocks, legacy-only output, narrator-only passive output. | `test_scene_blocks_required_for_final_response`, `test_legacy_only_output_fails_final_response` |
| MVP3-P07 | Narrative Runtime Agent | `ai_stack/narrative_runtime_agent.py` | Implement event-based streaming narrator that fills silence based on NPC motivation pressure (dramatic signature, narrative threads, pressure); input-blocking while streaming; motivation-aware ruhepunkt detection. | `test_narrative_agent_streams_continuously`, `test_narrative_agent_respects_motivation_pressure`, `test_narrative_agent_blocks_input_while_streaming`, `test_narrative_agent_signals_ruhepunkt_when_no_npc_initiatives` |
| MVP3-P08 | Story Runtime Manager orchestration | `world-engine/app/story_runtime/manager.py` | Orchestrate: LDSS → NarrativeRuntimeAgent; manage input-queue; signal ruhepunkt detection → process queued input. | `test_story_runtime_manager_orchestrates_ldss_and_narrative_agent`, `test_input_blocking_while_narrative_agent_streams` |
| MVP3-P09 | Operational wiring | `tests/run_tests.py`, workflows, TOMLs | Include unit/integration/live-route LDSS and NarrativeRuntimeAgent suites. | operational checks |

## Data Contracts

### SceneTurnEnvelope.v2

```json
{
  "contract": "scene_turn_envelope.v2",
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "runtime_module_id": "solo_story_runtime",
  "selected_player_role": "annette",
  "human_actor_id": "annette_reille",
  "npc_actor_ids": ["alain_reille", "veronique_houllie", "michel_houllie"],
  "visible_scene_output": {"contract": "visible_scene_output.blocks.v1", "blocks": []},
  "diagnostics": {"live_dramatic_scene_simulator": {"status": "evidenced_live_path"}}
}
```

### SceneBlock

```json
{
  "id": "turn-4-block-2",
  "block_type": "actor_line",
  "speaker_label": "Véronique",
  "actor_id": "veronique_houllie",
  "target_actor_id": "alain_reille",
  "text": "You keep turning this into a legal question. It is not a legal question.",
  "delivery": {"mode": "typewriter", "characters_per_second": 44, "pause_before_ms": 150, "pause_after_ms": 650, "skippable": true}
}
```

Valid block types: `narrator`, `actor_line`, `actor_action`, `environment_interaction`, `system_degraded_notice`.

### LDSSInput

```json
{
  "contract": "ldss_input.v1",
  "story_session_state": {"story_session_id": "story_123", "turn_number": 4, "current_scene_id": "phase_1"},
  "actor_lane_context": {
    "human_actor_id": "annette_reille",
    "ai_allowed_actor_ids": ["alain_reille", "veronique_houllie", "michel_houllie"],
    "ai_forbidden_actor_ids": ["annette_reille"]
  },
  "admitted_objects": [
    {"object_id": "mobile_phone", "source_kind": "canonical_content"},
    {"object_id": "water_glass", "source_kind": "typical_minor_implied"}
  ],
  "player_input": "Alain, are you even listening to us?"
}
```

### LDSSOutput

```json
{
  "contract": "ldss_output.v1",
  "decision_count": 3,
  "npc_agency_plan_count": 2,
  "visible_actor_response_present": true,
  "scene_block_count": 4,
  "visible_scene_output": {"contract": "visible_scene_output.blocks.v1", "blocks": ["see examples"]}
}
```

### NPCAgencySimulation

```json
{
  "contract": "npc_agency_simulation.v1",
  "schema_version": "npc_agency_simulation.v1",
  "contract_status": "implemented_runtime_simulation",
  "implementation_status": "implemented_runtime_simulation",
  "not_full_multi_agent_simulation": false,
  "independent_planning_used": true,
  "planner_scope": "independent_multi_npc_agency",
  "turn_number": 4,
  "candidate_actor_ids": ["veronique_vallon", "michel_longstreet"],
  "ordered_actor_ids": ["veronique_vallon", "michel_longstreet"],
  "required_actor_ids": ["veronique_vallon", "michel_longstreet"],
  "carry_forward_actor_ids": [],
  "npc_intent_proposals": [
    {
      "actor_id": "veronique_vallon",
      "role": "primary_responder",
      "intent": "claim_primary_response",
      "allowed_block_types": ["actor_line", "actor_action"],
      "allowed_output_lanes": ["spoken_lines", "action_lines", "initiative_events"],
      "target_actor_id": null,
      "required": true,
      "requirement_scope": "primary_required",
      "resolved": false
    },
    {
      "actor_id": "michel_longstreet",
      "role": "secondary_reactor",
      "intent": "react_to_primary_or_scene_pressure",
      "allowed_block_types": ["actor_line", "actor_action"],
      "allowed_output_lanes": ["spoken_lines", "action_lines", "initiative_events"],
      "target_actor_id": "veronique_vallon",
      "required": true,
      "requirement_scope": "one_secondary_minimum",
      "resolved": false
    }
  ],
  "npc_interaction_graph": {
    "nodes": [{"actor_id": "veronique_vallon"}, {"actor_id": "michel_longstreet"}],
    "edges": [{"source_actor_id": "michel_longstreet", "target_actor_id": "veronique_vallon", "edge_type": "initiative_pressure"}]
  },
  "conflict_resolution": {
    "policy": "carry_forward_then_director_priority_then_roster_order",
    "minimum_secondary_initiatives_required": 1
  }
}
```

Current Pi7 runtime support treats `npc_agency_simulation.v1` as the primary NPC agency surface. `ai_stack/npc_agency_planner.py` builds an independent bounded roster plan from actor-lane, responder, mind, and carry-forward evidence; `ai_stack/npc_agency_realization.py` records planned/realized/missing required NPC initiative and builds `npc_agency_closure.v1`; committed planner truth carries unresolved required initiatives into the next turn; Langfuse/operator/MCP surfaces score planned vs. realized NPC initiative. The older `npc_agency_plan.v1` shape may still appear as an internal adapter, but it is not the current proof target.

### EnvironmentInteraction

```json
{
  "contract": "environment_interaction.v1",
  "actor_id": "michel_houllie",
  "object_id": "coffee_table",
  "affordance_tier": "canonical",
  "action": "move_book_aside",
  "text": "Michel shifts the coffee table book aside, clearing a space that makes the silence more visible."
}
```

### AffordanceValidation

```json
{
  "contract": "affordance_validation.v1",
  "status": "approved",
  "object_id": "mobile_phone",
  "affordance_tier": "similar_allowed",
  "base_affordance": "hold",
  "canonical_similarity_reason": "A phone that can be held or checked can plausibly be turned face down without creating new story truth."
}
```

### NarratorVoiceValidation

```json
{
  "contract": "narrator_voice_validation.v1",
  "status": "approved",
  "allowed_voice": "inner_perception_orientation",
  "rejected_modes": ["dialogue_summary", "forced_player_state", "hidden_npc_intent"]
}
```

### PassivityValidation

```json
{
  "contract": "passivity_validation.v1",
  "visible_actor_response_required": true,
  "visible_actor_response_present": true,
  "minimum_scene_block_count": 2,
  "narrator_only_allowed": false,
  "status": "passed"
}
```

### NarrativeRuntimeAgentInput

```json
{
  "contract": "narrative_runtime_agent_input.v1",
  "runtime_state": {"story_session_id": "story_123", "turn_number": 4, "current_scene_id": "phase_1", "dramatic_signature": {...}, "narrative_threads": [...], "thread_pressure_summary": "escalating"},
  "npc_agency_simulation": {"schema_version": "npc_agency_simulation.v1", "candidate_actor_ids": ["veronique_houllie", "alain_reille"], "npc_intent_proposals": [...]},
  "ldss_output": {"visible_scene_output": {...}, "decision_count": 3, "scene_block_count": 4},
  "enable_langfuse_tracing": false,
  "player_input_queued": false,
  "narrative_context": {"prior_silence_duration_ms": 1200, "last_npc_action": "veronique_speaks", "player_emotional_cue": "questioning"}
}
```

### NarrativeRuntimeAgentOutput (Streaming)

Each stream event is one of:

```json
{
  "contract": "narrative_runtime_agent_event.v1",
  "event_type": "narrator_block",
  "narrator_block": {
    "id": "turn-4-block-1",
    "block_type": "narrator",
    "text": "You notice the pause before Alain answers; it feels less like uncertainty than calculation.",
    "delivery": {"mode": "typewriter", "characters_per_second": 44, "pause_before_ms": 150, "pause_after_ms": 650, "skippable": true}
  },
  "decision_id": "d-narrator-perception-1"
}
```

or

```json
{
  "contract": "narrative_runtime_agent_event.v1",
  "event_type": "ruhepunkt_signal",
  "ruhepunkt_reached": true,
  "remaining_npc_initiatives": 0,
  "can_accept_input": true,
  "narrative_context": {"blocks_streamed": 3, "total_duration_ms": 4200, "silence_filled": true, "motivation_pressure_addressed": "escalating"}
}
```

### NarrativeRuntimeAgentConfig

```json
{
  "contract": "narrative_runtime_agent_config.v1",
  "enable_langfuse_tracing": false,
  "narrator_style": "inner_perception_orientation",
  "silence_filling_enabled": true,
  "motivation_awareness_enabled": true,
  "max_silence_duration_ms": 8000,
  "ruhepunkt_strategy": "motivation_based"
}
```

## Validation Rules

| Rule | Where Enforced | Error Code | Test Name | Diagnostic Field |
|---|---|---|---|---|
| final output requires scene blocks | LDSS output validator and response packager | `scene_blocks_required` | `test_scene_blocks_required_for_final_response` | `frontend_render_contract.scene_block_count` |
| legacy output cannot be final | response packager | `legacy_output_not_final_contract` | `test_legacy_only_output_fails_final_response` | `frontend_render_contract.legacy_blob_used` |
| LDSS must be live-path evidenced | HTTP turn integration and diagnostics | `ldss_not_evidenced_live_path` | `test_live_dramatic_scene_simulator_not_partial` | `live_dramatic_scene_simulator.status` |
| visible NPC actor response required | passivity guard | `no_visible_actor_response` | `test_no_visible_actor_response_triggers_retry_or_degradation` | `npc_agency.visible_actor_response_present` |
| similar allowed requires reason | affordance validator | `similar_allowed_requires_similarity_reason` | `test_similar_allowed_requires_similarity_reason` | `affordance_validation.canonical_similarity_reason` |
| hallucinated object rejected | object admission/affordance validator | `environment_object_not_admitted` | `test_rejects_unadmitted_plausible_object` | `object_admission.status` |
| protected state mutation rejected | state delta boundary commit seam | `protected_state_mutation_rejected` | `test_environment_delta_cannot_mutate_protected_truth` | `state_delta_validation.error_code` |
| narrator cannot summarize dialogue | narrator validator | `narrator_dialogue_summary_rejected` | `test_narrator_rejects_dialogue_recap` | `narrator_validation.error_code` |
| narrator cannot force player state | narrator validator | `narrator_forces_player_state` | `test_narrator_modal_language_does_not_force_player_state` | `narrator_validation.error_code` |
| narrator cannot reveal hidden intent | narrator validator | `narrator_reveals_hidden_intent` | `test_narrator_cannot_reveal_hidden_npc_intent` | `narrator_validation.error_code` |
| narrative agent must stream while NPC initiatives pending | narrative runtime agent | `narrative_agent_must_stream_npc_initiatives` | `test_narrative_agent_continues_while_npc_initiatives_pending` | `narrative_agent.streaming_active` |
| narrative agent must signal ruhepunkt when no NPC initiatives | narrative runtime agent | `ruhepunkt_signal_required` | `test_narrative_agent_signals_ruhepunkt_when_initiatives_exhausted` | `narrative_agent_event.ruhepunkt_reached` |
| input must be blocked while narrative agent streams | story runtime manager | `input_blocked_during_narrative_streaming` | `test_input_blocked_while_narrative_agent_streams` | `story_runtime.input_queue_status` |
| narrative agent must not force player state or emotion | narrative runtime agent | `narrator_forces_player_state` | `test_narrative_agent_does_not_force_player_state` | `narrative_agent.validation_outcome` |

### Wave-Hardening Validation Rules

| Rule | Where Enforced | Error Code | Test Name | Diagnostic Field |
|---|---|---|---|---|
| Source Locator Matrix contains no unresolved placeholders before patching | implementation report preflight | `source_locator_unresolved` | `test_source_locator_matrix_has_no_placeholders_before_patch` | `source_locator.status` |
| operational evidence lists exact MVP-specific suites/files/markers | operational report validator | `operational_suite_evidence_missing` | `test_operational_report_lists_mvp_specific_suites` | `operational_gate.mvp_specific_suites` |
| fixed MVP operational evidence artifact exists | operational report validator | `operational_evidence_artifact_missing` | `test_operational_evidence_artifact_exists_for_mvp` | `operational_gate.artifact_path` |


## Examples

### Valid SceneTurnEnvelope.v2 with blocks

```json
{
  "contract": "scene_turn_envelope.v2",
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "runtime_module_id": "solo_story_runtime",
  "selected_player_role": "annette",
  "human_actor_id": "annette_reille",
  "npc_actor_ids": ["alain_reille", "veronique_houllie", "michel_houllie"],
  "visible_scene_output": {
    "contract": "visible_scene_output.blocks.v1",
    "blocks": [
      {
        "id": "turn-4-block-1",
        "block_type": "narrator",
        "speaker_label": "You notice",
        "actor_id": null,
        "target_actor_id": null,
        "text": "You notice the pause before Alain answers; it feels less like uncertainty than calculation.",
        "delivery": {"mode": "typewriter", "characters_per_second": 44, "pause_before_ms": 150, "pause_after_ms": 650, "skippable": true}
      },
      {
        "id": "turn-4-block-2",
        "block_type": "actor_line",
        "speaker_label": "Véronique",
        "actor_id": "veronique_houllie",
        "target_actor_id": "alain_reille",
        "text": "You keep turning this into a legal question. It is not a legal question.",
        "delivery": {"mode": "typewriter", "characters_per_second": 44, "pause_before_ms": 150, "pause_after_ms": 650, "skippable": true}
      },
      {
        "id": "turn-4-block-3",
        "block_type": "actor_action",
        "speaker_label": "Alain",
        "actor_id": "alain_reille",
        "target_actor_id": null,
        "text": "Alain glances at his phone but does not pick it up yet.",
        "delivery": {"mode": "typewriter", "characters_per_second": 44, "pause_before_ms": 150, "pause_after_ms": 650, "skippable": true}
      },
      {
        "id": "turn-4-block-4",
        "block_type": "environment_interaction",
        "speaker_label": "Michel",
        "actor_id": "michel_houllie",
        "target_actor_id": null,
        "object_id": "coffee_table",
        "affordance_tier": "canonical",
        "text": "Michel shifts the coffee table book aside, clearing a space that makes the silence more visible.",
        "delivery": {"mode": "typewriter", "characters_per_second": 44, "pause_before_ms": 150, "pause_after_ms": 650, "skippable": true}
      }
    ]
  },
  "diagnostics": {
    "live_dramatic_scene_simulator": {
      "status": "evidenced_live_path",
      "invoked": true,
      "entrypoint": "story.turn.execute",
      "decision_count": 3,
      "output_contract": "visible_scene_output.blocks.v1"
    }
  }
}
```

### Canonical affordance

```json
{"object_id": "mobile_phone", "actor_id": "alain_reille", "affordance_tier": "canonical", "action": "glance_at", "validation": {"status": "approved"}}
```

### Typical affordance

```json
{"object_id": "water_glass", "actor_id": "michel_houllie", "affordance_tier": "typical", "action": "set_down", "validation": {"status": "approved", "temporary_scene_staging": true, "commit_allowed": false}}
```

### Similar allowed affordance

```json
{"object_id": "mobile_phone", "actor_id": "alain_reille", "affordance_tier": "similar_allowed", "base_affordance": "hold", "action": "turn_screen_face_down", "canonical_similarity_reason": "A phone that can be held or checked can plausibly be turned face down without creating new story truth.", "validation": {"status": "approved"}}
```

### Rejected hallucinated object

```json
{"object_id": "knife", "actor_id": "veronique_houllie", "action": "place_on_table", "validation": {"status": "rejected", "error_code": "environment_object_not_admitted"}}
```

### Valid narrator inner voice

```json
{"block_type": "narrator", "text": "You notice Alain's answer arrives a beat too quickly, as if he has been waiting for a way out.", "validation": {"status": "approved"}}
```

### Invalid narrator dialogue summary

```json
{"block_type": "narrator", "text": "Véronique and Alain argue about responsibility while Michel becomes uncomfortable.", "validation": {"status": "rejected", "error_code": "narrator_dialogue_summary_rejected"}}
```

### Invalid forced player state

```json
{"block_type": "narrator", "text": "You decide that Alain is right and feel ashamed.", "validation": {"status": "rejected", "error_code": "narrator_forces_player_state"}}
```

### Passivity/degradation

```json
{
  "candidate_output": {"visible_scene_output": {"blocks": [{"block_type": "narrator", "text": "The room is tense."}]}},
  "validation": {
    "status": "rejected_or_retry",
    "error_code": "no_visible_actor_response",
    "required_behavior": "At least one visible NPC actor_line, actor_action, or environment_interaction must occur unless the turn is explicitly terminal."
  }
}
```

### LDSS live-path evidence requirement

```json
{
  "ldss_invoked_by_real_turn_route": true,
  "turn_entrypoint": "story.turn.execute",
  "story_session_id": "story_123",
  "turn_number": 4,
  "input_hash": "sha256:ldss-input-123",
  "output_hash": "sha256:ldss-output-123",
  "decision_count": 3,
  "scene_block_count": 4,
  "visible_actor_response_present": true,
  "legacy_blob_used": false
}
```

## Required Tests

**LDSS Tests:**
- `test_ldss_generates_scene_turn_envelope_v2`
- `test_live_turn_route_invokes_ldss`
- `test_live_dramatic_scene_simulator_not_partial`
- `test_scene_blocks_required_for_final_response`
- `test_legacy_only_output_fails_final_response`
- `test_npc_to_npc_dialogue_present`
- `test_no_visible_actor_response_triggers_retry_or_degradation`
- `test_similar_allowed_requires_similarity_reason`
- `test_rejects_unadmitted_plausible_object`
- `test_environment_delta_cannot_mutate_protected_truth`

**Narrator Validation Tests:**
- `test_narrator_rejects_dialogue_recap`
- `test_narrator_modal_language_does_not_force_player_state`
- `test_narrator_cannot_reveal_hidden_npc_intent`

**Narrative Runtime Agent Tests:**
- `test_narrative_agent_streams_continuously`
- `test_narrative_agent_respects_motivation_pressure`
- `test_narrative_agent_fills_silence_based_on_npc_pressure`
- `test_narrative_agent_blocks_input_while_streaming`
- `test_narrative_agent_signals_ruhepunkt_when_no_npc_initiatives`
- `test_narrative_agent_continues_while_npc_initiatives_pending`
- `test_narrative_agent_does_not_force_player_state`

**Story Runtime Manager Orchestration Tests:**
- `test_story_runtime_manager_orchestrates_ldss_and_narrative_agent`
- `test_input_blocked_while_narrative_agent_streams`
- `test_input_queue_processed_after_ruhepunkt_signal`

**Langfuse Optional Instrumentation Tests:**
- `test_narrative_agent_accepts_enable_langfuse_tracing_config`
- `test_narrative_agent_emits_trace_scaffold_by_default`
- `test_narrative_agent_emits_langfuse_spans_when_enabled`

**All mandatory operational checks from this guide**

## Required ADRs

Required for this MVP:

- ADR-007 Minimum Agency Baseline / Superseded Relation
- ADR-011 Live Dramatic Scene Simulator
- ADR-012 NPC Free Dramatic Agency
- ADR-013 Narrator Inner Voice Contract
- ADR-015 Canonical, Typical, and Similar Environment Affordances
- ADR-016 Operational Test and Startup Gates

Complete package ADR map:

No major architectural or behavior-changing repair is complete unless the matching ADR exists under `docs/ADR/` and matches the implemented repository state.

| ADR | Required By | Purpose |
|---|---|---|
| ADR-001 Experience Identity | MVP 1 | `god_of_carnage` content, `god_of_carnage_solo` runtime profile, no visitor. |
| ADR-002 Runtime Profile Resolver | MVP 1 | Resolver behavior, error codes, profile/content separation. |
| ADR-003 Role Selection and Actor Ownership | MVP 1/2 | Annette/Alain selection, human actor ownership, NPC assignment. |
| ADR-004 Actor-Lane Enforcement | MVP 2 | AI cannot speak/act for human actor. |
| ADR-005 Canonical Content Authority | MVP 2 | Runtime profile/module cannot own story truth. |
| ADR-006 Evidence-Gated Architecture Capabilities | MVP 1/4 | Capability reports must be source-backed. |
| ADR-007 Minimum Agency Baseline / Superseded Relation | MVP 3 | Prior minimum agency is superseded by LDSS behavior gates. |
| ADR-008 Diagnostics and Degradation Semantics | MVP 4 | Normal/degraded/failed semantics and fallback visibility. |
| ADR-009 Langfuse and Traceable Decisions | MVP 4 | Real trace/export requirements and decision IDs. |
| ADR-010 Narrative Gov Operator Truth Surface | MVP 4 | Operator-facing health panels and source truth. |
| ADR-011 Live Dramatic Scene Simulator | MVP 3 | LDSS contract and live-path invocation. |
| ADR-012 NPC Free Dramatic Agency | MVP 3 | NPC autonomy, NPC-to-NPC dialogue, passivity guard. |
| ADR-013 Narrator Inner Voice Contract | MVP 3 | Narrator as perception/orientation voice, not summary/puppeteer. |
| ADR-014 Interactive Text-Adventure Frontend | MVP 5 | Structured staged block renderer and typewriter delivery. |
| ADR-015 Canonical, Typical, and Similar Environment Affordances | MVP 2/3 | Object admission and affordance tiers. |
| ADR-016 Operational Test and Startup Gates | all | `docker-up.py`, `tests/run_tests.py`, GitHub, TOML/tooling hard gates. |

Each ADR must include status, context, decision, affected services/files, consequences, alternatives considered, validation evidence, related audit finding IDs, tests proving the decision, and operational gate impact.

## Mandatory Operational Gate

The operational gate is mandatory for this MVP and cannot be deferred.

Required command evidence:

```text
python docker-up.py
python tests/run_tests.py --unit
python tests/run_tests.py --integration
python tests/run_tests.py --e2e
python tests/run_tests.py --all
```

If the repository uses different command names, document the exact equivalent and why it is equivalent.

Required operational checks:

```text
test_docker_up_script_exists_or_equivalent_documented
test_docker_up_reports_failed_service
test_run_test_lists_required_suites
test_run_test_includes_current_mvp_tests
test_run_test_fails_on_failed_suite
test_github_workflows_include_current_mvp_tests
test_github_workflows_do_not_silently_skip_e2e
test_toml_testpaths_include_current_mvp_tests
test_toml_pythonpath_supports_services
```
### MVP-Specific Suite Evidence

The operational report must list the exact test files, markers, or suites added for this MVP.

Required format:

```text
MVP-specific test coverage:
- unit test files:
- integration test files:
- e2e/browser test files:
- pytest markers or runner suite names:
- tests/run_tests.py suite entries:
- GitHub workflow jobs:
- TOML testpaths/markers:
```

The gate fails when the report only says `unit`, `integration`, `e2e`, or `all` without naming the concrete MVP tests.

Required error code:

```text
operational_suite_evidence_missing
```

Required test:

```text
test_operational_report_lists_mvp_specific_suites
```


### Required Operational Evidence Artifact

Write the final operational evidence for this MVP to:

```text
tests/reports/MVP_Live_Runtime_Completion/MVP<NUMBER>_OPERATIONAL_EVIDENCE.md
```

The artifact must include:

- exact `docker-up.py` command and result
- exact `tests/run_tests.py` commands and result
- unit/integration/e2e/browser suite names
- concrete test files added or modified
- pytest markers or runner suite names
- GitHub workflow files and job names
- TOML/tooling files checked
- skipped suites, if any, and why they do not satisfy the gate
- failure output for any failed command
- final PASS/FAIL verdict

The MVP gate fails if this artifact is missing.

Required error code:

```text
operational_evidence_artifact_missing
```

Required test:

```text
test_operational_evidence_artifact_exists_for_mvp
```

Presence-only checks fail the gate. The implementation report must include:

```text
Operational Gate:
- docker-up.py status:
- tests/run_tests.py status:
- GitHub workflows status:
- TOML/tooling status:
- commands run:
- skipped suites with reason:
- failing suites:
- report paths:
```

Required operational evidence artifact schema:

```json
{
  "contract": "operational_evidence_note.v1",
  "mvp": "<mvp-number>",
  "docker_up": {
    "command": "python docker-up.py",
    "status": "passed|failed|not_available",
    "required_services_checked": ["backend", "frontend", "administration-tool", "play-service"],
    "failed_services": [],
    "evidence_path": "tests/reports/<mvp>/docker-up.log"
  },
  "run_test": {
    "commands": ["python tests/run_tests.py --all"],
    "status": "passed|failed",
    "included_suites": ["unit", "integration", "e2e"],
    "skipped_required_suites": [],
    "evidence_path": "tests/reports/<mvp>/run-test.log"
  },
  "github_workflows": {
    "status": "covered|missing|drift",
    "workflow_files": [".github/workflows/tests.yml"],
    "covered_suites": ["unit", "integration", "e2e"],
    "missing_suites": []
  },
  "toml_tooling": {
    "status": "covered|missing|invalid",
    "files_checked": ["pyproject.toml", "backend/pyproject.toml", "world-engine/pyproject.toml"],
    "testpaths_include_current_mvp": true,
    "pythonpath_valid": true
  }
}
```

## Operational Patch Map

| Area | Required Patch | Proof |
|---|---|---|
| `tests/run_tests.py` | include LDSS unit, validator, and real turn integration tests | run-test inclusion log |
| GitHub workflows | run LDSS live-path tests; no unit-only acceptance | workflow job anchors |
| TOML/tooling | include ai_stack/world-engine LDSS paths and markers | TOML assertion tests |
| `docker-up.py` | still starts all services after LDSS integration | service health logs |

## Handoff to Next MVP

MVP 3 → MVP 4:

```text
LDSS live path
scene blocks
simulator diagnostics scaffold
trace scaffold
passivity validation status
degradation signal scaffold
```

Required handoff artifact: `tests/reports/MVP3_LDSS_LIVE_PATH_EVIDENCE.md`.

## Stop Condition

Stop only when:

1. Real turn route invokes LDSS.
2. `SceneTurnEnvelope.v2` with non-empty blocks is returned.
3. At least one visible NPC actor response is present unless terminal.
4. NPC-to-NPC dialogue and valid environment interaction are covered by tests.
5. Narrator invalid modes are rejected.
6. `evidenced_live_path` is supported by real session/run/turn IDs, hashes, counts, and trace scaffold.
7. Legacy-only output fails final response validation.
8. Operational gate and handoff artifacts exist.

## Claude Implementation Prompt

You are implementing MVP 3 only: Live Dramatic Scene Simulator.

Inspect first:

```text
world-engine/app/api/http.py
world-engine/app/runtime/manager.py
ai_stack/langgraph_runtime.py
ai_stack/goc_turn_seams.py
ai_stack/live_dramatic_scene_simulator.py
world-engine/app/runtime/actor_lane.py
world-engine/app/runtime/object_admission.py
world-engine/app/runtime/state_delta.py
tests/run_tests.py
.github/workflows/*.yml
pyproject.toml
```

Fill the Source Locator Matrix. Implement Patch Map rows MVP3-P01 through MVP3-P07. Use MVP 2 validators; do not bypass them. Add SceneTurnEnvelope.v2, SceneBlock, LDSSInput, LDSSOutput, NPCAgencyPlan, EnvironmentInteraction, AffordanceValidation, NarratorVoiceValidation, and PassivityValidation. Add unit and real turn-route tests. Do not implement final Narrative Gov UI or frontend typewriter renderer. Stop when the Stop Condition passes.

## Token Discipline

Do not inspect unrelated files.
Do not restate architecture.
Do not implement later MVPs.
Do not create broad audit reports.
Do not accept field presence as behavior.
Stop when the listed stop condition passes.
