# MVP_Live_Runtime_Completion — MVP 1 — Experience Identity and Session Start

## Mission

Implement the God of Carnage solo experience identity and session-start contract so the live path starts only from canonical `god_of_carnage` content through the runtime profile `god_of_carnage_solo`.

This MVP makes Annette/Alain role choice mandatory before session creation, removes the synthetic `visitor` role from the live solo path, and produces the normalized runtime profile and role ownership handoff consumed by MVP 2.

## Scope

In scope:

- Runtime profile resolution for `god_of_carnage_solo`.
- Canonical content binding to `god_of_carnage`.
- Annette/Alain role selection before creating the story run.
- Rejection of missing, invalid, or non-canonical selected roles.
- Rejection of `visitor` anywhere in God of Carnage solo runtime/session surfaces.
- Source-backed capability evidence that reports implemented/missing status honestly.
- Operational gate integration for startup, tests, CI, and TOML/tooling.

Out of scope:

- Actor-lane enforcement internals, except for emitting the handoff fields consumed by MVP 2.
- LDSS generation, diagnostics, Narrative Gov, and frontend staging except as future capability placeholders marked `missing` or `not_ready`.

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

MVP 1 is the entry gate for the final target. If the session can start without selecting Annette or Alain, if `visitor` survives as a participant, or if `god_of_carnage_solo` is treated as content, later LDSS, diagnostics, and frontend proofs are invalid.

## Inputs from Previous MVP

Not applicable for this MVP because it is the first guide in the sequence.

Baseline inputs:

| Input | Source | Required Fields | Evidence Path |
|---|---|---|---|
| Existing repository state | current repo/archive | backend, world-engine, frontend, admin, ai_stack, tests, docs | implementation report source locator matrix |
| Canonical content | repository content loader | `content_module_id=god_of_carnage`, canonical character records for Annette and Alain | content loader path and tests |
| Quality audit findings | `goc_technical_5_mvp_quality_audit.md` | GUIDE-PATCH-001, 002, 007, 008, 009 | `tests/reports/MVP1_IMPLEMENTATION_REPORT.md` |

## This MVP Produces

| Output | Consumed By | Required Fields | Evidence Path |
|---|---|---|---|
| Normalized RuntimeProfile | MVP 2 | `runtime_profile_id`, `content_module_id`, `runtime_module_id`, `runtime_mode`, selectable roles, no story truth | tests/reports/MVP1_HANDOFF_RUNTIME_PROFILE.md |
| RoleSlugActorIdMap | MVP 2 | `annette -> canonical_actor_id`, `alain -> canonical_actor_id`, source content hash | tests/reports/MVP1_HANDOFF_RUNTIME_PROFILE.md |
| CreateRunResponse | MVP 2 | `human_actor_id`, `npc_actor_ids`, `actor_lanes`, `visitor_present=false` | integration test artifact |
| CapabilityEvidenceReport | MVP 4 | source anchors and implemented/missing statuses | tests/reports/MVP1_CAPABILITY_EVIDENCE.md |

## Consumed By Next MVP

MVP 2 consumes:

- normalized runtime profile
- selected player role
- role slug mapping
- human actor ID
- NPC actor IDs
- `visitor` absence proof
- source-backed capability evidence status

## Services Touched

| Service | Purpose |
|---|---|
| backend | session bootstrap route, runtime profile resolver, content binding, error payloads |
| world-engine / play-service | create-run request/response model, runtime instance bootstrap, participant ownership |
| frontend | launcher/session-start role selector only where the actual live launcher exists |
| administration-tool | read-only capability evidence display if already present; otherwise do not build MVP 4 surfaces |
| tests/tooling | unit/integration/e2e routing, CI, TOML/tooling updates |

## Files to Inspect First

- `backend/app/api/v1/game_routes.py` — session/bootstrap/create-run route; fallback search: `rg "create.*run|bootstrap|session" backend/app -n`.
- `backend/app/services/game_service.py` — backend-to-world-engine request packaging; fallback search: `rg "world.*engine|play-service|CreateRun" backend/app -n`.
- `backend/app/services/content*` or `backend/app/modules*` — canonical module loader/compiler; fallback search: `rg "god_of_carnage|content_module_id|module_id" backend world-engine -n`.
- `world-engine/app/api/http.py` — `CreateRunRequest`, `CreateRunResponse`, turn response model.
- `world-engine/app/runtime/manager.py` — `create_run()`, `_bootstrap_instance()`, runtime profile/session bootstrap.
- `world-engine/app/runtime/models.py` — `RuntimeInstance`, session state model.
- `world-engine/app/runtime/profiles*` or closest equivalent — runtime profile registry/resolver.
- `frontend/static/play_shell.js` and actual launcher route/template — role selection and create-run payload.
- `tests/` — existing runtime/session/start tests.
- `.github/workflows/*.yml`, `pyproject.toml`, service TOMLs, `docker-up.py`, `tests/run_tests.py`.

## Do Not Touch

- Do not implement LDSS output generation in this MVP.
- Do not modify production story content except to remove accidental `visitor` leakage or runtime-profile story truth.
- Do not rebuild frontend rendering beyond the role selector needed to start a valid run.
- Do not add Narrative Gov dashboards beyond honest capability evidence fields.
- Do not rename the five MVP guide files.

## Targeted Search Commands

```bash
rg "god_of_carnage_solo|visitor|selected_player_role|runtime_profile" -n backend world-engine frontend administration-tool ai_stack tests docs
rg "CreateRunRequest|CreateRunResponse|create_run|_bootstrap_instance|RuntimeInstance" -n world-engine backend tests
rg "Annette|Alain|annette|alain|annette_reille|alain_reille" -n backend world-engine ai_stack frontend tests docs
rg "docker-up|run-test|pytest|testpaths|pythonpath" -n .github pyproject.toml */pyproject.toml docker-up.py tests/run_tests.py
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
| MVP1-P01 | Runtime profile resolver | runtime profile registry/resolver, `world-engine/app/runtime/manager.py` | Resolve `god_of_carnage_solo` as profile-only object bound to `god_of_carnage`; emit structured errors. | `test_runtime_profile_resolver_success`, `test_unknown_runtime_profile_rejected` |
| MVP1-P02 | Content authority | content loader/compiler, runtime profile builder | Forbid characters, rooms, props, beats, scenes, endings, relationships, roles as story truth in profile. | `test_goc_solo_not_loadable_as_content_module`, `test_profile_contains_no_story_truth` |
| MVP1-P03 | Role selection | backend route, world-engine create-run API, frontend launcher | Require `selected_player_role`=`annette|alain` before session start. | `test_session_creation_requires_selected_player_role`, `test_valid_annette_start`, `test_valid_alain_start` |
| MVP1-P04 | Visitor removal | backend/world-engine/frontend/ai_stack tests | Sweep and reject `visitor` in participants, prompts, responders, lobby seats, frontend state. | `test_visitor_absent_from_prompts_responders_lobby` |
| MVP1-P05 | Capability evidence | report generator / diagnostics scaffold | Capability report must include real file/symbol anchors or `missing`; no static success. | `test_ldss_capability_added_to_e0_report_requires_source_anchor` |
| MVP1-P06 | Operational wiring | `docker-up.py`, `tests/run_tests.py`, workflows, TOMLs | Include new MVP 1 tests and fail on missing/skipped suites. | operational checks listed below |

## Data Contracts

### RuntimeProfile

```json
{
  "contract": "runtime_profile.v1",
  "runtime_profile_id": "god_of_carnage_solo",
  "content_module_id": "god_of_carnage",
  "runtime_module_id": "solo_story_runtime",
  "runtime_mode": "solo_story",
  "requires_selected_player_role": true,
  "selectable_player_roles": [
    {"role_slug": "annette", "canonical_actor_id": "annette_reille", "display_name": "Annette"},
    {"role_slug": "alain", "canonical_actor_id": "alain_reille", "display_name": "Alain"}
  ],
  "forbidden_story_truth_fields": ["characters", "roles", "rooms", "props", "beats", "scenes", "relationships", "endings"],
  "profile_version": "goc-solo.v1"
}
```

### RoleSlugActorIdMap

```json
{
  "contract": "role_slug_actor_id_map.v1",
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "role_slug_actor_id_map": {
    "annette": "annette_reille",
    "alain": "alain_reille"
  },
  "source": "canonical_content.characters",
  "resolved_from_content": true,
  "content_hash": "sha256:goc-content-sample"
}
```

### CreateRunRequest

```json
{
  "contract": "create_run_request.v1",
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "selected_player_role": "annette"
}
```

### CreateRunResponse

```json
{
  "contract": "create_run_response.v1",
  "run_id": "run_123",
  "story_session_id": "story_123",
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "runtime_module_id": "solo_story_runtime",
  "runtime_mode": "solo_story",
  "selected_player_role": "annette",
  "human_actor_id": "annette_reille",
  "npc_actor_ids": ["alain_reille", "veronique_houllie", "michel_houllie"],
  "actor_lanes": {
    "annette_reille": "human",
    "alain_reille": "npc",
    "veronique_houllie": "npc",
    "michel_houllie": "npc"
  },
  "visitor_present": false
}
```

### CapabilityEvidenceReport

```json
{
  "contract": "capability_evidence_report.v1",
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "capabilities": [
    {
      "capability": "role_selection",
      "status": "implemented",
      "source_anchors": ["world-engine/app/runtime/manager.py:create_run", "frontend/static/play_shell.js:startRun"],
      "tests": ["test_valid_annette_start", "test_valid_alain_start"]
    },
    {
      "capability": "live_dramatic_scene_simulator",
      "status": "missing",
      "source_anchors": [],
      "tests": []
    }
  ]
}
```

## Validation Rules

| Rule | Where Enforced | Error Code | Test Name | Diagnostic Field |
|---|---|---|---|---|
| runtime profile is required | backend create-run route and world-engine API model | `runtime_profile_required` | `test_create_run_missing_runtime_profile_returns_contract_error` | `runtime_profile.status` |
| unknown runtime profile rejected | runtime profile resolver | `runtime_profile_not_found` | `test_unknown_runtime_profile_rejected` | `runtime_profile.error_code` |
| runtime profile cannot be content | content loader and runtime profile resolver | `runtime_profile_not_content_module` | `test_goc_solo_not_loadable_as_content_module` | `content_authority.profile_only` |
| selected player role required | backend/world-engine create-run validation | `selected_player_role_required` | `test_session_creation_without_selected_player_role_fails` | `role_selection.error_code` |
| selected player role must be Annette or Alain | create-run validation after content mapping | `invalid_selected_player_role` | `test_session_creation_invalid_role_fails` | `role_selection.allowed_values` |
| selected slug must resolve to canonical character | content role map builder | `selected_player_role_not_canonical_character` | `test_role_slug_must_resolve_to_canonical_actor` | `role_selection.resolved_from_content` |
| `visitor` invalid anywhere live | backend, world-engine, frontend, ai_stack prompt/responder sweep | `invalid_visitor_runtime_reference` | `test_visitor_absent_from_prompts_responders_lobby` | `visitor_present` |
| capability report success requires anchors | evidence report writer | `capability_evidence_missing_source_anchor` | `test_ldss_capability_added_to_e0_report_requires_source_anchor` | `capability.source_anchors` |

### Wave-Hardening Validation Rules

| Rule | Where Enforced | Error Code | Test Name | Diagnostic Field |
|---|---|---|---|---|
| Source Locator Matrix contains no unresolved placeholders before patching | implementation report preflight | `source_locator_unresolved` | `test_source_locator_matrix_has_no_placeholders_before_patch` | `source_locator.status` |
| operational evidence lists exact MVP-specific suites/files/markers | operational report validator | `operational_suite_evidence_missing` | `test_operational_report_lists_mvp_specific_suites` | `operational_gate.mvp_specific_suites` |
| fixed MVP operational evidence artifact exists | operational report validator | `operational_evidence_artifact_missing` | `test_operational_evidence_artifact_exists_for_mvp` | `operational_gate.artifact_path` |


## Examples

### Valid Annette start

```json
{
  "request": {"runtime_profile_id": "god_of_carnage_solo", "selected_player_role": "annette"},
  "response": {
    "content_module_id": "god_of_carnage",
    "human_actor_id": "annette_reille",
    "npc_actor_ids": ["alain_reille", "veronique_houllie", "michel_houllie"],
    "visitor_present": false
  }
}
```

### Valid Alain start

```json
{
  "request": {"runtime_profile_id": "god_of_carnage_solo", "selected_player_role": "alain"},
  "response": {
    "content_module_id": "god_of_carnage",
    "human_actor_id": "alain_reille",
    "npc_actor_ids": ["annette_reille", "veronique_houllie", "michel_houllie"],
    "visitor_present": false
  }
}
```

### Missing selected role

```json
{
  "error": {
    "code": "selected_player_role_required",
    "message": "selected_player_role is required for runtime_profile_id=god_of_carnage_solo.",
    "allowed_values": ["annette", "alain"]
  }
}
```

### Invalid selected role and visitor rejection

```json
{
  "request": {"runtime_profile_id": "god_of_carnage_solo", "selected_player_role": "visitor"},
  "error": {
    "code": "invalid_selected_player_role",
    "received": "visitor",
    "allowed_values": ["annette", "alain"]
  }
}
```

```json
{
  "error": {
    "code": "invalid_visitor_runtime_reference",
    "message": "visitor is not a canonical God of Carnage actor and is not valid in the live solo runtime path.",
    "location": "create_run.participants"
  }
}
```

### Profile-as-content rejection

```json
{
  "request": {"content_module_id": "god_of_carnage_solo"},
  "error": {
    "code": "runtime_profile_not_content_module",
    "message": "god_of_carnage_solo is a runtime profile, not a content module. Use content_module_id=god_of_carnage."
  }
}
```

### Resolver implementation shape

```python
def resolve_runtime_profile(runtime_profile_id: str, canonical_content) -> RuntimeProfile:
    if not runtime_profile_id:
        raise RuntimeProfileError(code="runtime_profile_required", message="runtime_profile_id is required.")
    if runtime_profile_id != "god_of_carnage_solo":
        raise RuntimeProfileError(code="runtime_profile_not_found", message=f"Unknown runtime profile: {runtime_profile_id}")
    role_map = build_role_slug_actor_id_map(canonical_content)
    return RuntimeProfile(
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
        runtime_module_id="solo_story_runtime",
        runtime_mode="solo_story",
        requires_selected_player_role=True,
        selectable_player_roles=[
            {"role_slug": "annette", "canonical_actor_id": role_map["annette"], "display_name": "Annette"},
            {"role_slug": "alain", "canonical_actor_id": role_map["alain"], "display_name": "Alain"},
        ],
        profile_version="goc-solo.v1",
    )
```

## Required Tests

- `test_runtime_profile_resolver_success`
- `test_create_run_missing_runtime_profile_returns_contract_error`
- `test_unknown_runtime_profile_rejected`
- `test_goc_solo_not_loadable_as_content_module`
- `test_profile_contains_no_story_truth`
- `test_session_creation_without_selected_player_role_fails`
- `test_session_creation_invalid_role_fails`
- `test_role_slug_must_resolve_to_canonical_actor`
- `test_valid_annette_start`
- `test_valid_alain_start`
- `test_visitor_absent_from_prompts_responders_lobby`
- `test_ldss_capability_added_to_e0_report_requires_source_anchor`
- all mandatory operational checks from this guide

## Required ADRs

Required for this MVP:

- ADR-001 Experience Identity
- ADR-002 Runtime Profile Resolver
- ADR-003 Role Selection and Actor Ownership
- ADR-006 Evidence-Gated Architecture Capabilities
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
python tests/run_tests.py --suite backend engine frontend
python tests/run_tests.py --suite backend engine ai_stack
python tests/run_tests.py --suite backend engine ai_stack story_runtime_core
python tests/run_tests.py --suite backend engine ai_stack story_runtime_core gates
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
| `docker-up.py` | starts backend, frontend, admin, play-service; reports failed service and exits nonzero | command log and `test_docker_up_reports_failed_service` |
| `tests/run_tests.py` | includes MVP 1 tests in unit/integration/e2e/all suites; fails on skipped required suites | run-test log and inclusion test |
| GitHub workflows | execute MVP 1 unit/integration/e2e tests or exact equivalents | workflow file anchors |
| TOML/tooling | testpaths/pythonpath include backend, world-engine, frontend, tests needed by MVP 1 | config assertions |

## Handoff to Next MVP

MVP 1 → MVP 2:

```text
normalized runtime profile
role selection
role slug mapping
visitor removed
human_actor_id
npc_actor_ids
actor_lanes seed
source-backed evidence report
```

Required handoff artifact: `tests/reports/MVP1_HANDOFF_RUNTIME_PROFILE.md`.

## Stop Condition

Stop only when:

1. Annette and Alain runs can be created through the real live route.
2. Missing/invalid roles and `visitor` are rejected with contract errors.
3. `god_of_carnage_solo` cannot be loaded as content and contains no story truth.
4. The capability evidence report uses real anchors or honest `missing` statuses.
5. MVP 1 tests run through `tests/run_tests.py` and are included in GitHub workflows/TOML tooling.
6. Operational evidence is written with command logs and report paths.
7. Handoff artifact to MVP 2 exists.

## Claude Implementation Prompt

You are implementing MVP 1 only: Experience Identity and Session Start.

Inspect first:

```text
backend/app/api/v1/game_routes.py
backend/app/services/game_service.py
world-engine/app/api/http.py
world-engine/app/runtime/manager.py
world-engine/app/runtime/models.py
frontend/static/play_shell.js
tests/run_tests.py
docker-up.py
.github/workflows/*.yml
pyproject.toml
```

Use targeted searches from this guide when a path is absent. Fill the Source Locator Matrix before patching. Implement the Patch Map rows MVP1-P01 through MVP1-P06. Add the Data Contracts, Validation Rules, Examples, Required Tests, ADR updates, Operational Gate evidence, and the MVP 1 handoff report. Do not implement MVP 2 actor-lane validators except for the output fields required by the MVP 1 handoff. Do not implement LDSS, Narrative Gov, or the final frontend renderer. Stop when the Stop Condition passes.

## Token Discipline

Do not inspect unrelated files.
Do not restate architecture.
Do not implement later MVPs.
Do not create broad audit reports.
Do not accept field presence as behavior.
Stop when the listed stop condition passes.
