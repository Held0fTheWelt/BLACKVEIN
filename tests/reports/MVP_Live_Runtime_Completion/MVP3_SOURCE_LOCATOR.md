# MVP 3 Source Locator Artifact

**Date**: 2026-04-29  
**MVP**: 3 — Live Dramatic Scene Simulator  
**Status**: Complete (all sources located, no unresolved placeholders)

## Source Locator Matrix

| Area | Expected Path | Actual Path | Symbol / Anchor | Status | Notes |
|---|---|---|---|---|---|
| **MVP3-P01: LDSS Module** |
| SceneTurnEnvelopeV2 model | `ai_stack/live_dramatic_scene_simulator.py` | `ai_stack/live_dramatic_scene_simulator.py` | `SceneTurnEnvelopeV2` dataclass | found | Contract for live turn output shape |
| SceneBlock model | `ai_stack/live_dramatic_scene_simulator.py` | `ai_stack/live_dramatic_scene_simulator.py` | `SceneBlock` dataclass | found | Typed scene units: narrator, actor_line, actor_action, environment_interaction, system_degraded_notice |
| LDSSInput contract | `ai_stack/live_dramatic_scene_simulator.py` | `ai_stack/live_dramatic_scene_simulator.py` | `LDSSInput` dataclass | found | Story session, actor lanes, admitted objects, player input |
| LDSSOutput contract | `ai_stack/live_dramatic_scene_simulator.py` | `ai_stack/live_dramatic_scene_simulator.py` | `LDSSOutput` dataclass | found | Decision count, block count, visible response flag, NPC agency plan |
| NPCAgencyPlan model | `ai_stack/live_dramatic_scene_simulator.py` | `ai_stack/live_dramatic_scene_simulator.py` | `NPCAgencyPlan` dataclass | found | Primary/secondary responders, NPC initiatives |
| run_ldss() function | `ai_stack/live_dramatic_scene_simulator.py` | `ai_stack/live_dramatic_scene_simulator.py` | `run_ldss(ldss_input)` → `LDSSOutput` | found | LDSS orchestration entry point |
| **MVP3-P02: Runtime Manager Integration** |
| LDSS invocation | `world-engine/app/story_runtime/manager.py` | `world-engine/app/story_runtime/manager.py` | `_build_ldss_scene_envelope()` function | found | Called in `_finalize_committed_turn()` after validation/commit |
| SceneTurnEnvelope response field | `world-engine/app/api/http.py` | `world-engine/app/api/http.py` | `ExecuteTurnResponse.scene_turn_envelope` | found | Final HTTP response includes envelope |
| committed state seam | `world-engine/app/story_runtime/manager.py` | `world-engine/app/story_runtime/manager.py` | `_finalize_committed_turn()` | found | LDSS runs post-commit on validated state |
| **MVP3-P03: NPC Agency Enforcement** |
| responder candidate validation | `ai_stack/live_dramatic_scene_simulator.py` | `ai_stack/live_dramatic_scene_simulator.py` | `validate_responder_candidates()` function | found | Rejects human actor and visitor from NPC responder set |
| primary responder selection | `ai_stack/live_dramatic_scene_simulator.py` | `ai_stack/live_dramatic_scene_simulator.py` | `_select_primary_responder()` function | found | Priority: veronique → alain → michel |
| NPC-to-NPC targeting | `ai_stack/live_dramatic_scene_simulator.py` | `ai_stack/live_dramatic_scene_simulator.py` | `SceneBlock.target_actor_id` field | found | Enables NPC-to-NPC dramatic exchange |
| **MVP3-P04: Narrator Voice Validation** |
| narrator block validation | `ai_stack/validators/narrator_voice_validation.py` | `ai_stack/validators/narrator_voice_validation.py` | `validate_narrator_voice()` function | found | Rejects narrator blocks that block player agency |
| passivity guard | `ai_stack/live_dramatic_scene_simulator.py` | `ai_stack/live_dramatic_scene_simulator.py` | `_check_passivity()` function | found | Detects passive NPC output (validation failure) |
| **MVP3-P05: Affordance & State Validation** |
| environment interaction model | `ai_stack/live_dramatic_scene_simulator.py` | `ai_stack/live_dramatic_scene_simulator.py` | `EnvironmentInteraction` dataclass | found | Canonical/typical/similar affordance tier |
| affordance validation | `ai_stack/validators/affordance_validation.py` | `ai_stack/validators/affordance_validation.py` | `validate_environment_interaction()` function | found | Enforces object admission and affordance tiers |
| object admission seam | `ai_stack/goc_turn_seams.py` | `ai_stack/goc_turn_seams.py` | `run_visible_render()` with object admission checks | found | Rejects unadmitted objects before LDSS |
| **MVP3-P06: Live Path Evidence & Diagnostics** |
| diagnostics scaffold | `ai_stack/live_dramatic_scene_simulator.py` | `ai_stack/live_dramatic_scene_simulator.py` | `LiveDramaticSceneSimulatorDiagnostics` dataclass | found | live_path status, input/output hashes, decision/block counts |
| evidenced_live_path status | `ai_stack/live_dramatic_scene_simulator.py` | `ai_stack/live_dramatic_scene_simulator.py` | `"evidenced_live_path"` status string in diagnostics | found | Set when LDSS runs through real turn route |
| trace scaffold | `ai_stack/live_dramatic_scene_simulator.py` | `ai_stack/live_dramatic_scene_simulator.py` | `TraceScaffold` dataclass in LDSS output | found | Span names, decision IDs, validation outcomes for MVP4 |
| **MVP3-P07: Operational Wiring** |
| docker-up.py | `docker-up.py` | `docker-up.py` | startup sequence | found | All services start; no MVP3-specific changes |
| test runner | `tests/run_tests.py` | `tests/run_tests.py` | `--mvp3` preset, suite: backend, engine, ai_stack, story_runtime_core | found | Runs all MVP3 test files |
| GitHub workflows | `.github/workflows/engine-tests.yml`, `.github/workflows/backend-tests.yml` | `.github/workflows/engine-tests.yml`, `.github/workflows/backend-tests.yml` | job definitions covering MVP3 suites | found | Covers MVP3 test files |
| TOML/tooling | `pyproject.toml`, `world-engine/pyproject.toml`, `ai_stack/pyproject.toml` | `world-engine/pyproject.toml`, `ai_stack/pyproject.toml` | testpaths = ["tests"] | found | Auto-discovers MVP3 test files |
| **Gate Tests** |
| LDSS gate tests | `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py` | `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py` | 26 gate test functions | found | Start scene, response packaging, NPC agency, narrator validation |
| integration tests | `world-engine/tests/test_mvp3_ldss_integration.py` | `world-engine/tests/test_mvp3_ldss_integration.py` | 6 integration test functions | found | Execute_turn live path through HTTP endpoint |
| **Required ADRs** |
| ADR-007 | `docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-007-minimum-agency-baseline-superseded.md` | `docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-007-minimum-agency-baseline-superseded.md` | Status: Accepted | found | Prior minimum agency superseded by LDSS gates |
| ADR-011 | `docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-011-live-dramatic-scene-simulator.md` | `docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-011-live-dramatic-scene-simulator.md` | Status: Accepted | found | LDSS contract and live-path invocation |
| ADR-012 | `docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-012-npc-free-dramatic-agency.md` | `docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-012-npc-free-dramatic-agency.md` | Status: Accepted | found | NPC autonomy, NPC-to-NPC dialogue, passivity guard |
| ADR-013 | `docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-013-narrator-inner-voice-contract.md` | `docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-013-narrator-inner-voice-contract.md` | Status: Accepted | found | Narrator as perception/orientation voice, not summary |

## Concrete Source Anchors for Each Patch

### MVP3-P01: LDSS Module

**File**: `ai_stack/live_dramatic_scene_simulator.py`

**Key Symbols**:
- `SceneTurnEnvelopeV2(contract, story_session_id, run_id, turn_number, visible_scene_output, diagnostics)`
- `SceneBlock(block_id, block_type, content, actor_id, target_actor_id, validation_status, intent_label)`
- `LDSSInput(story_session_state, actor_lane_context, admitted_objects, player_input, runtime_state)`
- `LDSSOutput(decision_count, scene_block_count, visible_actor_response_present, npc_agency_plan, visible_scene_output, diagnostics)`
- `NPCAgencyPlan(primary_responder_id, secondary_responder_ids, npc_initiatives)`
- `run_ldss(ldss_input)` → `LDSSOutput`

**Tests**:
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py::test_mvp3_gate_start_annette_live_scene_turn` — PASS
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py::test_mvp3_gate_start_alain_live_scene_turn` — PASS
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py::test_mvp3_gate_ldss_produces_non_empty_blocks` — PASS

### MVP3-P02: Runtime Manager Integration

**Files**:
- `world-engine/app/story_runtime/manager.py` — `_build_ldss_scene_envelope()`, `_finalize_committed_turn()`
- `world-engine/app/api/http.py` — `ExecuteTurnResponse` model with `scene_turn_envelope` field
- `ai_stack/goc_turn_seams.py` — LDSS context propagation

**Key Symbols**:
- `_build_ldss_scene_envelope(committed_state, runtime_state, actor_lane_context)` → `SceneTurnEnvelopeV2`
- `_finalize_committed_turn(...)` calls `_build_ldss_scene_envelope()` post-commit
- `ExecuteTurnResponse.scene_turn_envelope` — HTTP response field

**Tests**:
- `world-engine/tests/test_mvp3_ldss_integration.py::test_execute_turn_produces_scene_turn_envelope_annette` — PASS
- `world-engine/tests/test_mvp3_ldss_integration.py::test_execute_turn_produces_scene_turn_envelope_alain` — PASS
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py::test_mvp3_gate_response_packaged_from_committed_state` — PASS

### MVP3-P03: NPC Agency Enforcement

**File**: `ai_stack/live_dramatic_scene_simulator.py`

**Key Symbols**:
- `validate_responder_candidates(primary_id, secondary_ids, human_actor_id)` → bool
- `_select_primary_responder(npc_actor_ids, actor_lanes)` → actor_id (priority: veronique > alain > michel)
- `NPCAgencyPlan.secondary_responder_ids` — additional participants beyond primary
- `SceneBlock.target_actor_id` — enables NPC-to-NPC targeting

**Tests**:
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py::test_mvp3_gate_npcs_act_without_direct_address` — PASS
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py::test_mvp3_gate_multiple_npcs_can_participate` — PASS
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py::test_mvp3_gate_responder_candidates_exclude_human_and_visitor` — PASS

### MVP3-P04: Narrator Voice Validation

**Files**:
- `ai_stack/validators/narrator_voice_validation.py` — narrator validation rules
- `ai_stack/live_dramatic_scene_simulator.py` — passivity checks and narrator block filtering

**Key Symbols**:
- `validate_narrator_voice(narrator_block, player_state, human_actor_id)` → `ValidationResult`
- `_check_passivity(npc_proposals)` → bool (detects inaction/avoidance)

**Tests**:
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py::test_mvp3_gate_narrator_cannot_force_player_action` — PASS
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py::test_mvp3_gate_passivity_guard_rejects_inactive_npcs` — PASS

### MVP3-P05: Affordance & State Validation

**Files**:
- `ai_stack/validators/affordance_validation.py` — environment interaction validation
- `ai_stack/live_dramatic_scene_simulator.py` — `EnvironmentInteraction` model

**Key Symbols**:
- `EnvironmentInteraction(object_id, action_type, canonical, typical, similar_allowed)`
- `validate_environment_interaction(interaction, admitted_objects)` → bool
- Object admission enforced before LDSS block construction

**Tests**:
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py::test_mvp3_gate_environment_interaction_validates_affordances` — PASS
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py::test_mvp3_gate_unadmitted_objects_rejected` — PASS

### MVP3-P06: Live Path Evidence & Diagnostics

**File**: `ai_stack/live_dramatic_scene_simulator.py`

**Key Symbols**:
- `LiveDramaticSceneSimulatorDiagnostics(status, story_session_id, turn_number, input_hash, output_hash, decision_count, scene_block_count, legacy_blob_used)`
- `status = "evidenced_live_path"` when LDSS runs through real turn route
- `TraceScaffold(spans, decision_ids, validation_outcomes)` for MVP4 consumption
- `input_hash`, `output_hash` provide deterministic proof

**Tests**:
- `world-engine/tests/test_mvp3_ldss_integration.py::test_scene_envelope_diagnostics_evidenced_live_path` — PASS
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py::test_mvp3_gate_trace_header_preserved_on_story_turn` — PASS

### MVP3-P07: Operational Wiring

**Files**:
- `tests/run_tests.py` — `--mvp3` flag and suite configuration
- `.github/workflows/engine-tests.yml`, `.github/workflows/backend-tests.yml` — MVP3 test coverage
- `docker-up.py` — startup sequence (unchanged)
- `world-engine/pyproject.toml`, `ai_stack/pyproject.toml` — testpaths configuration

**Key Anchors**:
- `--mvp3` runs: backend, engine, ai_stack, story_runtime_core
- GitHub workflows configured to run MVP3 test files on push/PR
- Docker-up.py starts all services without MVP3-specific changes

**Tests**:
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py::test_mvp03_runner_registration_exists` — PASS
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py::test_mvp03_operational_gate_docker_up_functional` — PASS
- `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py::test_mvp03_operational_gate_github_workflows_present` — PASS

## Summary

All MVP3 source anchors are concrete, located, and testable. No placeholders remain. All ADRs are ACCEPTED. Gate and integration tests verify live-path evidence for LDSS invocation, NPC agency enforcement, narrator validation, and operational wiring.

**Status**: ✅ **COMPLETE** — Ready for operational gate verification.
