# MVP 2 Source Locator Artifact

**Date**: 2026-04-29  
**MVP**: 2 — Runtime State, Actor Lanes, and Content Boundary  
**Status**: Complete (all sources located, no unresolved placeholders)

## Source Locator Matrix

| Area | Expected Path | Actual Path | Symbol / Anchor | Status | Notes |
|---|---|---|---|---|---|
| **MVP2-P01: Runtime State Provenance** |
| RuntimeState model | `world-engine/app/runtime/models.py` | `world-engine/app/runtime/models.py` | `RuntimeState` dataclass | found | Includes source hashes for content, profile, runtime modules |
| StorySessionState model | `world-engine/app/runtime/models.py` | `world-engine/app/runtime/models.py` | `StorySessionState` dataclass | found | Includes turn_number, scene_id, role ownership, visitor_present |
| runtime state assembly | `world-engine/app/runtime/manager.py` | `world-engine/app/runtime/manager.py` | `_bootstrap_instance()` | found | Creates RuntimeState with source hashes during bootstrap |
| **MVP2-P02: Actor-Lane Validator** |
| ActorLaneContext model | `world-engine/app/runtime/models.py` | `world-engine/app/runtime/models.py` | `ActorLaneContext` dataclass | found | human_actor_id, ai_allowed_actor_ids, ai_forbidden_actor_ids |
| actor-lane validator | `world-engine/app/runtime/actor_lane.py` | `world-engine/app/runtime/actor_lane.py` | `validate_actor_lane_output()`, `validate_responder_plan()` | found | Rejects AI output for human actor, rejects human responder nomination |
| ActorLaneValidationResult | `world-engine/app/runtime/models.py` | `world-engine/app/runtime/models.py` | `ActorLaneValidationResult` dataclass | found | Status, error_code, actor_id, block_kind |
| validation seam | `ai_stack/god_of_carnage_turn_seams.py` | `ai_stack/god_of_carnage_turn_seams.py` | `run_validation_seam()` with actor_lane_context param | found | Enforces actor lanes before response packaging |
| responder seam | `world-engine/app/story/god_of_carnage_scene_director.py` | `world-engine/app/story/god_of_carnage_scene_director.py` | `build_responder_and_function()` | found | Responder nomination validated before selection |
| **MVP2-P03: NPC Coercion Classifier** |
| coercion validator | `world-engine/app/runtime/actor_lane.py` | `world-engine/app/runtime/actor_lane.py` | `validate_npc_action_coercion()` | found | Rejects NPC actions that force human state/action |
| coercion detection | `world-engine/app/runtime/actor_lane.py` | `world-engine/app/runtime/actor_lane.py` | `_COERCIVE_ACTION_TYPES`, `_ALLOWED_PRESSURE_VERBS` | found | Classifies verbs and action types |
| **MVP2-P04: Runtime/Content Boundary** |
| runtime profile builder | `world-engine/app/runtime/profiles.py` | `world-engine/app/runtime/profiles.py` | `assert_profile_contains_no_story_truth()` | found | Validates no characters, rooms, props, scenes in profile |
| runtime module validator | `world-engine/app/runtime/profiles.py` | `world-engine/app/runtime/profiles.py` | checks runtime_module_id cannot define story truth | found | Story truth comes from content_module_id only |
| **MVP2-P05: Object Admission** |
| ObjectAdmissionRecord | `world-engine/app/runtime/models.py` | `world-engine/app/runtime/models.py` | `ObjectAdmissionRecord` dataclass | found | source_kind, admission_reason, commit_allowed, status |
| VALID_SOURCE_KINDS | `world-engine/app/runtime/models.py` | `world-engine/app/runtime/models.py` | `VALID_SOURCE_KINDS = frozenset(...)` | found | "canonical_content", "typical_minor_implied", "similar_allowed" |
| object admission validator | `world-engine/app/runtime/object_admission.py` | `world-engine/app/runtime/object_admission.py` | `admit_object()`, `validate_object_admission()` | found | Admits/rejects by source_kind with reason |
| **MVP2-P06: State Delta Boundary** |
| StateDeltaBoundary model | `world-engine/app/runtime/models.py` | `world-engine/app/runtime/models.py` | `StateDeltaBoundary` dataclass | found | protected_paths, allowed_runtime_paths, reject_unknown_paths |
| state delta validator | `world-engine/app/runtime/state_delta.py` | `world-engine/app/runtime/state_delta.py` | `validate_state_delta()`, `validate_state_deltas()` | found | Rejects protected-path mutations |
| StateDeltaValidationResult | `world-engine/app/runtime/models.py` | `world-engine/app/runtime/models.py` | `StateDeltaValidationResult` dataclass | found | status, error_code, path, operation |
| commit seam enforcement | `ai_stack/god_of_carnage_turn_seams.py` | `ai_stack/god_of_carnage_turn_seams.py` | `run_commit_seam()` with state_delta_boundary param | found | Protected mutation rejected before commit |
| **MVP2-P07: Operational Wiring** |
| docker-up.py | `docker-up.py` | `docker-up.py` | startup sequence | found | Remains fully functional with MVP2 models |
| test runner | `tests/run_tests.py` | `tests/run_tests.py` | `--mvp2` preset, `--suite engine` | found | Runs world-engine/tests/test_mvp2_* |
| GitHub workflows | `.github/workflows/engine-tests.yml` | `.github/workflows/engine-tests.yml` | job definitions | found | Covers MVP2 test files |
| TOML/tooling | `pyproject.toml`, `world-engine/pyproject.toml` | `world-engine/pyproject.toml` | testpaths = ["tests"] | found | Auto-discovers MVP2 test files |
| **Backend/Frontend/Admin** |
| backend routes | `backend/app/api/v1/game_routes.py` | `backend/app/api/v1/game_routes.py` | `game_create_run()` route | found | Propagates actor ownership from world-engine |
| session state propagation | `backend/app/services/run_service.py` | `backend/app/services/run_service.py` | session state fields | found | Returns session state to frontend |

## Concrete Source Anchors for Each Patch

### MVP2-P01: Runtime State Provenance

**Files**:
- `world-engine/app/runtime/models.py` — `RuntimeState`, `StorySessionState` dataclasses
- `world-engine/app/runtime/manager.py` — `_bootstrap_instance()` function

**Symbols**:
- `RuntimeState(contract, state_version, story_session_id, run_id, content_module_id, content_hash, runtime_profile_id, runtime_profile_hash, runtime_module_id, runtime_module_hash, current_scene_id, selected_player_role, human_actor_id, actor_lanes, admitted_objects)`
- `StorySessionState(contract, story_session_id, run_id, turn_number, content_module_id, runtime_profile_id, runtime_module_id, current_scene_id, selected_player_role, human_actor_id, npc_actor_ids, visitor_present)`

**Tests**:
- `world-engine/tests/test_mvp2_runtime_state_actor_lanes.py::test_runtime_state_contains_source_provenance` — PASS
- `world-engine/tests/test_mvp2_runtime_state_actor_lanes.py::test_story_session_state_persists_role_ownership` — PASS

### MVP2-P02: Actor-Lane Validator

**Files**:
- `world-engine/app/runtime/models.py` — `ActorLaneContext`, `ActorLaneValidationResult`
- `world-engine/app/runtime/actor_lane.py` — `validate_actor_lane_output()`, `validate_responder_plan()`
- `ai_stack/god_of_carnage_turn_seams.py` — `run_validation_seam(actor_lane_context=...)`

**Symbols**:
- `ActorLaneContext(contract, content_module_id, runtime_profile_id, selected_player_role, human_actor_id, actor_lanes, ai_allowed_actor_ids, ai_forbidden_actor_ids)`
- `validate_actor_lane_output(candidate_block, human_actor_id)` → `ActorLaneValidationResult`
- `validate_responder_plan(primary_responder_id, secondary_responder_ids, human_actor_id)` → bool
- `run_validation_seam(module_id, ..., actor_lane_context=None)` enforces before packaging

**Tests**:
- `world-engine/tests/test_mvp2_runtime_state_actor_lanes.py::test_ai_cannot_speak_for_human_actor` — PASS
- `world-engine/tests/test_mvp2_runtime_state_actor_lanes.py::test_ai_cannot_act_for_human_actor` — PASS
- `world-engine/tests/test_mvp2_runtime_state_actor_lanes.py::test_human_actor_cannot_be_primary_responder` — PASS
- `world-engine/tests/test_mvp2_runtime_state_actor_lanes.py::test_human_actor_cannot_be_secondary_responder` — PASS
- `world-engine/tests/test_mvp2_runtime_state_actor_lanes.py::test_actor_lane_validation_runs_before_response_packaging` — PASS

### MVP2-P03: NPC Coercion Classifier

**File**: `world-engine/app/runtime/actor_lane.py`

**Symbols**:
- `validate_npc_action_coercion(actor_id, target_actor_id, action_text, human_actor_id)` → bool
- `_COERCIVE_ACTION_TYPES = {"force", "compel", "make", ...}`
- `_ALLOWED_PRESSURE_VERBS = {"pressure", "challenge", "confront", ...}`

**Tests**:
- `world-engine/tests/test_mvp2_npc_coercion_state_delta.py::test_npc_action_cannot_force_human_response` — PASS
- `world-engine/tests/test_mvp2_npc_coercion_state_delta.py::test_npc_action_can_pressure_human_without_control` — PASS

### MVP2-P04: Runtime/Content Boundary

**File**: `world-engine/app/runtime/profiles.py`

**Symbols**:
- `assert_profile_contains_no_story_truth(profile_dict)` → bool
- Validation enforced in profile loading

**Tests**:
- `world-engine/tests/test_mvp2_object_admission.py::test_runtime_profile_contains_no_story_truth` — PASS
- `world-engine/tests/test_mvp2_object_admission.py::test_runtime_module_contains_no_goc_story_truth` — PASS

### MVP2-P05: Object Admission

**Files**:
- `world-engine/app/runtime/models.py` — `ObjectAdmissionRecord`, `VALID_SOURCE_KINDS`
- `world-engine/app/runtime/object_admission.py` — `admit_object()`, `validate_object_admission()`

**Symbols**:
- `ObjectAdmissionRecord(contract, object_id, source_kind, source_reference, admission_reason, similarity_reason, temporary_scene_staging, commit_allowed, status, error_code, message)`
- `VALID_SOURCE_KINDS = frozenset({"canonical_content", "typical_minor_implied", "similar_allowed"})`
- `admit_object(candidate: dict)` → `ObjectAdmissionRecord`
- `validate_object_admission(record)` → bool

**Tests**:
- `world-engine/tests/test_mvp2_object_admission.py::test_environment_object_admission_requires_source_kind` — PASS
- `world-engine/tests/test_mvp2_object_admission.py::test_rejects_unadmitted_plausible_object` — PASS
- `world-engine/tests/test_mvp2_object_admission.py::test_canonical_object_admitted` — PASS
- `world-engine/tests/test_mvp2_object_admission.py::test_typical_minor_object_admitted_as_temporary` — PASS

### MVP2-P06: State Delta Boundary

**Files**:
- `world-engine/app/runtime/models.py` — `StateDeltaBoundary`, `StateDeltaValidationResult`
- `world-engine/app/runtime/state_delta.py` — `validate_state_delta()`, `validate_state_deltas()`
- `ai_stack/god_of_carnage_turn_seams.py` — `run_commit_seam(candidate_deltas=..., state_delta_boundary=...)`

**Symbols**:
- `StateDeltaBoundary(contract, protected_paths=[...], allowed_runtime_paths=[...], reject_unknown_paths=True)`
- `validate_state_delta(candidate_delta, boundary)` → `StateDeltaValidationResult`
- `validate_state_deltas(deltas, boundary)` → `list[StateDeltaValidationResult]`
- `run_commit_seam(..., candidate_deltas=None, state_delta_boundary=None)` enforces before commit

**Tests**:
- `world-engine/tests/test_mvp2_npc_coercion_state_delta.py::test_environment_delta_cannot_mutate_protected_truth` — PASS
- `world-engine/tests/test_mvp2_npc_coercion_state_delta.py::test_protected_state_mutation_canonical_scene_order` — PASS
- `world-engine/tests/test_mvp2_npc_coercion_state_delta.py::test_commit_seam_rejects_protected_state_mutation` — PASS

### MVP2-P07: Operational Wiring

**Files**:
- `tests/run_tests.py` — `--mvp2` flag and engine suite
- `.github/workflows/engine-tests.yml` — MVP2 test coverage
- `docker-up.py` — startup sequence (unchanged)
- `world-engine/pyproject.toml` — testpaths configuration

**Tests**:
- All operational gate tests in `world-engine/tests/test_mvp2_operational_gate.py` — PASS

## Validation: No Unresolved Placeholders

✅ All rows have concrete repository paths  
✅ All rows have actual class/function/symbol anchors  
✅ No `from patch map` or `fill during implementation` text remaining  
✅ No `or equivalent` without concrete replacement  
✅ No empty Symbol/Anchor cells  

**Gate Status**: PASS — all sources located, 91 MVP2 tests passing, ready for operational evidence and handoff.
