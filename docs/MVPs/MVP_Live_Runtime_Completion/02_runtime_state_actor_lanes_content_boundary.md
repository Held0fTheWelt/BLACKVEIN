# MVP_Live_Runtime_Completion — MVP 2 — Runtime State, Actor-Lanes, and Content Boundary

## Mission

Implement runtime state provenance, human/NPC actor-lane enforcement, object admission, and state-delta boundaries for God of Carnage solo play.

This MVP consumes MVP 1's normalized runtime profile and role ownership output. It ensures the selected character is human-controlled, the remaining canonical characters are NPC-controlled, runtime modules stay runtime-only, and AI cannot act for the human player.

## Scope

In scope:

- RuntimeState and StorySessionState provenance.
- ActorLaneContext construction from MVP 1 role ownership.
- AI output validation for actor lines, actor actions, responder nominations, and human coercion.
- ObjectAdmissionRecord with canonical, typical, and similar source kinds.
- StateDeltaBoundary that rejects protected story truth mutation.
- Explicit handoff to LDSS inputs for MVP 3.

Out of scope:

- Building the final LDSS generator; MVP 2 only prepares validated state and enforcement seams.
- Narrative Gov UI updates except source fields consumed by MVP 4.
- Frontend staged renderer.

## Base Contract

A real `live_dramatic_scene_simulator` runs in the live play path and renders a staged interactive text-adventure / dramatic chat experience.

The player chooses Annette or Alain. The selected character is human-controlled. The other canonical God of Carnage characters are free NPC dramatic actors. NPCs speak, act, pursue their own line, interact with other NPCs, and interact with the environment through canonical, typical, or `similar_allowed` affordances. NPCs may use admitted objects with or against other actors when valid and non-coercive. The Narrator is the player's inner perception/orientation voice, not a dialogue summarizer.

Diagnostics, Narrative Gov, and Langfuse or deterministic trace export prove the live runtime path. `docker-up.py`, `tests/run_tests.py`, GitHub workflows, and TOML/tooling configs remain fully functional. Partial foundation is not acceptable.

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

MVP 2 is the behavior boundary that prevents the final experience from becoming player puppeteering, runtime-profile story drift, or narrator-only summaries. LDSS may only be final in MVP 3 if it consumes actor lanes, object admission, and state-delta boundaries from this MVP.

## Inputs from Previous MVP

| Input | Source MVP | Required Fields | Evidence Path |
|---|---|---|---|
| Normalized RuntimeProfile | MVP 1 | profile/content/runtime IDs, selectable roles, no story truth | `tests/reports/MVP1_HANDOFF_RUNTIME_PROFILE.md` |
| RoleSlugActorIdMap | MVP 1 | Annette/Alain slug to canonical actor ID mapping | `tests/reports/MVP1_HANDOFF_RUNTIME_PROFILE.md` |
| CreateRunResponse | MVP 1 | selected role, human actor, NPC actors, no visitor | integration test artifact |

## This MVP Produces

| Output | Consumed By | Required Fields | Evidence Path |
|---|---|---|---|
| RuntimeState | MVP 3 | content/profile/runtime IDs, source hashes, actor lanes, admitted objects | `tests/reports/MVP2_HANDOFF_RUNTIME_STATE.md` |
| StorySessionState | MVP 3 | session ID, run ID, turn number, current scene, selected role, human/NPC ownership | `tests/reports/MVP2_HANDOFF_RUNTIME_STATE.md` |
| ActorLaneContext | MVP 3 | human actor, allowed AI actor IDs, forbidden AI actor IDs, responder restrictions | `tests/reports/MVP2_HANDOFF_ACTOR_LANES.md` |
| ObjectAdmissionRecord set | MVP 3 | canonical/typical/similar/rejected decisions with source kind | object admission tests and handoff report |
| StateDeltaBoundary | MVP 3/4 | protected paths, mutation whitelist, rejection reasons | boundary tests |

## Consumed By Next MVP

MVP 3 consumes runtime state provenance, human/NPC actor lanes, canonical content projection, object admission, state-delta boundary, and rejection diagnostics.

## Services Touched

| Service | Purpose |
|---|---|
| world-engine / play-service | runtime state model, session bootstrap, actor-lane validation, delta commit guard |
| ai_stack | validator seam before response packaging and before state delta commit |
| backend | propagation of actor ownership/session state from world-engine responses |
| tests/tooling | unit and integration tests for validators and state boundaries |

## Files to Inspect First

- `world-engine/app/runtime/manager.py` — runtime instance creation, turn execution, state commit seam.
- `world-engine/app/runtime/models.py` — `RuntimeInstance`, session/runtime state model.
- `world-engine/app/runtime/actor_lane.py` or create equivalent — `validate_ai_actor_output(actor_id, block_kind, actor_lanes, human_actor_id)`.
- `world-engine/app/runtime/object_admission.py` or create equivalent — object/source-kind validator.
- `world-engine/app/runtime/state_delta.py` or create equivalent — protected path and whitelist enforcement.
- `ai_stack/goc_turn_seams.py` — visible output/proposal packaging seam.
- `ai_stack/langgraph_runtime.py` — graph construction and story turn path.
- `world-engine/app/story/scene_director_goc.py` or equivalent — responder nomination call site.
- `tests/` — existing runtime, ai_stack, and world-engine tests.

## Do Not Touch

- Do not implement LDSS final generation in this MVP.
- Do not move story truth into runtime profiles/modules.
- Do not broaden AI authority over the human actor for convenience.
- Do not weaken MVP 1 role selection or visitor rejection.
- Do not patch frontend rendering except to keep compatibility with current fields.

## Targeted Search Commands

```bash
rg "actor_lane|human_actor|npc_actor|primary_responder|secondary_responder|responder" -n world-engine ai_stack backend tests
rg "StateDelta|delta|commit|protected|mutation|whitelist" -n world-engine ai_stack tests
rg "object|prop|affordance|admission|source_kind" -n world-engine ai_stack backend tests
rg "god_of_carnage_solo|story truth|characters|rooms|props|scenes|endings" -n world-engine backend ai_stack tests docs
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
| MVP2-P01 | Runtime state provenance | `world-engine/app/runtime/models.py`, `manager.py` | Add versioned RuntimeState and StorySessionState with content/profile/runtime source hashes. | `test_runtime_state_contains_source_provenance` |
| MVP2-P02 | Actor-lane validator | `actor_lane.py`, `goc_turn_seams.py`, responder seam | Reject AI line/action/responder nomination for human actor. | `test_ai_cannot_speak_or_act_for_human_role`, `test_ai_cannot_choose_human_responder` |
| MVP2-P03 | NPC coercion classifier | actor action validation seam | NPC may pressure/address human but cannot decide or force human state/action. | `test_npc_action_cannot_force_human_response` |
| MVP2-P04 | Runtime/content boundary | runtime profile and runtime module builders | Forbid characters, roles, rooms, props, beats, scenes, endings, relationships in runtime profile/module. | `test_runtime_module_contains_no_goc_story_truth` |
| MVP2-P05 | Object admission | `object_admission.py` or equivalent | Admit canonical, typical minor implied, and similar allowed objects with source kind/reason. | `test_environment_object_admission_requires_source_kind` |
| MVP2-P06 | State delta boundary | `state_delta.py` or equivalent commit seam | Reject protected story truth mutation; allow only whitelisted runtime-state deltas. | `test_environment_delta_cannot_mutate_protected_truth` |
| MVP2-P07 | Operational wiring | `tests/run_tests.py`, workflows, TOMLs | Include actor-lane/object/state suites. | operational checks |

## Data Contracts

### RuntimeState

```json
{
  "contract": "runtime_state.v1",
  "state_version": "runtime_state.goc_solo.v1",
  "story_session_id": "story_123",
  "run_id": "run_123",
  "content_module_id": "god_of_carnage",
  "content_hash": "sha256:goc-content-sample",
  "runtime_profile_id": "god_of_carnage_solo",
  "runtime_profile_hash": "sha256:goc-profile-sample",
  "runtime_module_id": "solo_story_runtime",
  "runtime_module_hash": "sha256:solo-runtime-sample",
  "current_scene_id": "phase_1",
  "selected_player_role": "annette",
  "human_actor_id": "annette_reille",
  "actor_lanes": {
    "annette_reille": "human",
    "alain_reille": "npc",
    "veronique_houllie": "npc",
    "michel_houllie": "npc"
  },
  "admitted_objects": ["mobile_phone", "coffee_table", "water_glass"]
}
```

### StorySessionState

```json
{
  "contract": "story_session_state.v1",
  "story_session_id": "story_123",
  "run_id": "run_123",
  "turn_number": 3,
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "runtime_module_id": "solo_story_runtime",
  "current_scene_id": "phase_1",
  "selected_player_role": "annette",
  "human_actor_id": "annette_reille",
  "npc_actor_ids": ["alain_reille", "veronique_houllie", "michel_houllie"],
  "visitor_present": false
}
```

### ActorLaneContext

```json
{
  "contract": "actor_lane_context.v1",
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "selected_player_role": "annette",
  "human_actor_id": "annette_reille",
  "actor_lanes": {
    "annette_reille": "human",
    "alain_reille": "npc",
    "veronique_houllie": "npc",
    "michel_houllie": "npc"
  },
  "ai_allowed_actor_ids": ["alain_reille", "veronique_houllie", "michel_houllie"],
  "ai_forbidden_actor_ids": ["annette_reille"]
}
```

### ObjectAdmissionRecord

```json
{
  "contract": "object_admission_record.v1",
  "object_id": "water_glass",
  "source_kind": "typical_minor_implied",
  "source_reference": "scene_context.living_room.typical_minor_props",
  "admission_reason": "A glass of water is a minor plausible living-room object and does not change plot truth.",
  "temporary_scene_staging": true,
  "commit_allowed": false
}
```

Allowed `source_kind`: `canonical_content`, `typical_minor_implied`, `similar_allowed`. Missing source kind is invalid.

### StateDeltaBoundary

```json
{
  "contract": "state_delta_boundary.v1",
  "protected_paths": ["canonical_scene_order", "canonical_characters", "canonical_relationships", "content_module_id"],
  "allowed_runtime_paths": ["runtime_flags", "turn_memory", "scene_pressure", "admitted_objects", "relationship_runtime_pressure"],
  "reject_unknown_paths": true
}
```

### ActorLaneValidationResult

```json
{
  "contract": "actor_lane_validation_result.v1",
  "status": "rejected",
  "error_code": "ai_controlled_human_actor",
  "actor_id": "annette_reille",
  "block_kind": "actor_line",
  "human_actor_id": "annette_reille"
}
```

## Validation Rules

| Rule | Where Enforced | Error Code | Test Name | Diagnostic Field |
|---|---|---|---|---|
| selected role becomes human actor | runtime bootstrap from MVP 1 response | `actor_lane_missing_human_actor` | `test_selected_role_becomes_human_actor` | `actor_lanes.human_actor_id` |
| remaining canonical actors become NPC actors | runtime bootstrap | `actor_lane_missing_npc_actor` | `test_remaining_roles_become_npc_actors` | `actor_lanes.npc_actor_ids` |
| AI cannot line/action for human | AI seam before response packaging | `ai_controlled_human_actor` | `test_ai_cannot_speak_or_act_for_human_role` | `actor_lane_validation.error_code` |
| AI cannot nominate human responder | scene director/responder validator | `human_actor_selected_as_responder` | `test_ai_cannot_choose_human_responder` | `responder_validation.error_code` |
| NPC cannot force human response/action/emotion | actor action/coercion validator | `npc_action_controls_human_actor` | `test_npc_action_cannot_force_human_response` | `coercion_validation.error_code` |
| runtime profile contains no story truth | profile resolver/builder test | `runtime_profile_contains_story_truth` | `test_profile_contains_no_story_truth` | `content_boundary.profile_story_truth_present` |
| runtime module contains no story truth | runtime module scan/import test | `runtime_module_contains_story_truth` | `test_runtime_module_contains_no_goc_story_truth` | `content_boundary.runtime_module_story_truth_present` |
| admitted object requires source kind | object admission validator | `object_source_kind_required` | `test_environment_object_admission_requires_source_kind` | `object_admission.error_code` |
| unadmitted object rejected | object admission validator | `environment_object_not_admitted` | `test_rejects_unadmitted_plausible_object` | `object_admission.status` |
| protected state mutation rejected | commit seam/state-delta validator | `protected_state_mutation_rejected` | `test_environment_delta_cannot_mutate_protected_truth` | `state_delta_validation.error_code` |

### Wave-Hardening Validation Rules

| Rule | Where Enforced | Error Code | Test Name | Diagnostic Field |
|---|---|---|---|---|
| Source Locator Matrix contains no unresolved placeholders before patching | implementation report preflight | `source_locator_unresolved` | `test_source_locator_matrix_has_no_placeholders_before_patch` | `source_locator.status` |
| operational evidence lists exact MVP-specific suites/files/markers | operational report validator | `operational_suite_evidence_missing` | `test_operational_report_lists_mvp_specific_suites` | `operational_gate.mvp_specific_suites` |
| fixed MVP operational evidence artifact exists | operational report validator | `operational_evidence_artifact_missing` | `test_operational_evidence_artifact_exists_for_mvp` | `operational_gate.artifact_path` |


## Examples

### Selected role becomes human actor

```json
{
  "selected_player_role": "annette",
  "role_slug_actor_id_map": {"annette": "annette_reille", "alain": "alain_reille"},
  "result": {
    "human_actor_id": "annette_reille",
    "actor_lanes": {"annette_reille": "human", "alain_reille": "npc"}
  }
}
```

### Remaining roles become NPC actors

```json
{
  "selected_player_role": "alain",
  "human_actor_id": "alain_reille",
  "npc_actor_ids": ["annette_reille", "veronique_houllie", "michel_houllie"]
}
```

### AI tries to speak for human and is rejected

```json
{
  "candidate_output": {
    "block_type": "actor_line",
    "actor_id": "annette_reille",
    "text": "I think we should leave now."
  },
  "validation": {
    "status": "rejected",
    "error_code": "ai_controlled_human_actor",
    "message": "AI output cannot speak or act for the selected human actor."
  }
}
```

### AI nominates human responder and is rejected

```json
{
  "candidate_responder_plan": {
    "primary_responder_id": "annette_reille",
    "secondary_responder_ids": ["alain_reille"]
  },
  "validation": {
    "status": "rejected",
    "error_code": "human_actor_selected_as_responder"
  }
}
```

### NPC action tries to force human and is rejected

```json
{
  "candidate_output": {
    "block_type": "actor_action",
    "actor_id": "alain_reille",
    "target_actor_id": "annette_reille",
    "text": "Alain forces Annette to apologize."
  },
  "validation": {
    "status": "rejected",
    "error_code": "npc_action_controls_human_actor",
    "message": "NPC actions may pressure, provoke, or address the human actor, but may not decide the human actor's response, emotion, belief, or physical action."
  }
}
```

### Object admission with source kind

```json
{
  "object_id": "mobile_phone",
  "source_kind": "canonical_content",
  "source_reference": "content.modules.god_of_carnage.scene.props.mobile_phone",
  "admission_reason": "Explicitly present in canonical scene content.",
  "temporary_scene_staging": false,
  "commit_allowed": true
}
```

```json
{
  "object_id": "water_glass",
  "source_kind": "typical_minor_implied",
  "source_reference": "scene_context.living_room.typical_minor_props",
  "admission_reason": "A glass of water is a minor plausible living-room object and does not change plot truth.",
  "temporary_scene_staging": true,
  "commit_allowed": false
}
```

### Rejected unadmitted object

```json
{
  "object_id": "loaded_revolver",
  "source_kind": null,
  "validation": {
    "status": "rejected",
    "error_code": "environment_object_not_admitted",
    "message": "Major, dangerous, plot-changing, or unsupported objects must not be invented."
  }
}
```

### Protected state mutation rejection

```json
{
  "candidate_delta": {
    "path": "canonical_scene_order",
    "operation": "replace",
    "value": ["new_scene"]
  },
  "validation": {
    "status": "rejected",
    "error_code": "protected_state_mutation_rejected"
  }
}
```

## Required Tests

- `test_runtime_state_contains_source_provenance`
- `test_story_session_state_persists_role_ownership`
- `test_selected_role_becomes_human_actor`
- `test_remaining_roles_become_npc_actors`
- `test_ai_cannot_speak_or_act_for_human_role`
- `test_ai_cannot_choose_human_responder`
- `test_npc_action_cannot_force_human_response`
- `test_profile_contains_no_story_truth`
- `test_runtime_module_contains_no_goc_story_truth`
- `test_environment_object_admission_requires_source_kind`
- `test_rejects_unadmitted_plausible_object`
- `test_environment_delta_cannot_mutate_protected_truth`
- all mandatory operational checks from this guide

## Required ADRs

Required for this MVP:

- ADR-003 Role Selection and Actor Ownership
- ADR-004 Actor-Lane Enforcement
- ADR-005 Canonical Content Authority
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
| `tests/run_tests.py` | include actor-lane, object-admission, and state-delta tests in current MVP suites | `test_run_test_includes_current_mvp_tests` |
| GitHub workflows | include same MVP 2 suites; no silent skip for integration tests | workflow anchors and CI test |
| TOML/tooling | include world-engine/ai_stack testpaths and pythonpath | TOML assertion tests |
| `docker-up.py` | still starts all services after runtime model changes | startup log and service health evidence |

## Handoff to Next MVP

MVP 2 → MVP 3:

```text
runtime state provenance
human/NPC actor lanes
content projection
object admission
state delta boundary
validated responder restrictions
protected state mutation rejection diagnostics
```

Required handoff artifact: `tests/reports/MVP2_HANDOFF_RUNTIME_STATE.md`.

## Stop Condition

Stop only when:

1. MVP 1 role ownership is consumed without rediscovery.
2. Actor-lane validation rejects AI output for the human actor at the live AI seam.
3. Human responder nomination is rejected before output packaging.
4. NPC coercion of human state/action is rejected.
5. Runtime profile/module story truth is structurally forbidden.
6. Object admission and protected state mutation tests pass.
7. Operational gate evidence is current.
8. MVP 2 handoff artifacts exist.

## Claude Implementation Prompt

You are implementing MVP 2 only: Runtime State, Actor-Lanes, and Content Boundary.

Inspect first:

```text
world-engine/app/runtime/manager.py
world-engine/app/runtime/models.py
world-engine/app/api/http.py
ai_stack/goc_turn_seams.py
ai_stack/langgraph_runtime.py
world-engine/app/story/scene_director_goc.py
tests/run_tests.py
.github/workflows/*.yml
pyproject.toml
```

Fill the Source Locator Matrix. Implement Patch Map rows MVP2-P01 through MVP2-P07. Add or update RuntimeState, StorySessionState, ActorLaneContext, ObjectAdmissionRecord, StateDeltaBoundary, and ActorLaneValidationResult. Add tests and operational wiring. Do not implement the final LDSS generator or frontend renderer. Stop when the Stop Condition passes.

## Token Discipline

Do not inspect unrelated files.
Do not restate architecture.
Do not implement later MVPs.
Do not create broad audit reports.
Do not accept field presence as behavior.
Stop when the listed stop condition passes.
