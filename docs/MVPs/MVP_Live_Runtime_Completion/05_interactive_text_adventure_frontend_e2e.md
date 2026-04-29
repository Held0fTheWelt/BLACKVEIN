# MVP_Live_Runtime_Completion — MVP 5 — Interactive Text-Adventure Frontend and Final E2E

## Mission

Implement the staged interactive text-adventure / dramatic chat frontend and final end-to-end proof for God of Carnage solo play.

The frontend must consume `visible_scene_output.blocks.v1`, render one DOM block per scene block, support deterministic typewriter delivery, skip/reveal controls, accessibility mode, degraded legacy fallback labeling, and final Annette/Alain E2E transcript evidence.

## Scope

In scope:

- FrontendRenderContract and FrontendBlockRenderState.
- TypewriterDeliveryConfig with deterministic test mode.
- Skip current animation and reveal all controls.
- Accessibility/reduced-motion behavior.
- LegacyFallbackPolicy that marks adapted legacy output as degraded and fails final E2E acceptance.
- Final E2EAcceptanceEvidence for Annette and Alain runs.
- P13 staged frontend proof before final P12 acceptance closure.

Out of scope:

- Changing LDSS behavior except to fix contract mismatches discovered by frontend tests.
- Changing diagnostics semantics except to consume MVP 4 fields.
- Adding new story content.

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

MVP 5 proves the final target end-to-end. The final pass requires structured scene blocks, no single blob renderer, no final legacy fallback, no `visitor`, valid Annette and Alain runs, real trace/export evidence, Narrative Gov confirmation, and operational gates.

## Inputs from Previous MVP

| Input | Source MVP | Required Fields | Evidence Path |
|---|---|---|---|
| DiagnosticsEnvelope | MVP 4 | frontend render contract, quality, trace ID, LDSS status | `tests/reports/MVP4_HANDOFF_DIAGNOSTICS_AND_TRACE.md` |
| Trace/export evidence | MVP 4 | real generated trace/export paths and matching IDs | `tests/reports/langfuse/*.json` |
| NarrativeGovSummary | MVP 4 | operator surface statuses | admin route test artifact |
| SceneTurnEnvelope.v2 | MVP 3 via MVP 4 | non-empty visible scene blocks | live turn artifact |

## This MVP Produces

| Output | Consumed By | Required Fields | Evidence Path |
|---|---|---|---|
| FrontendRenderContract | final | block contract, DOM invariant, delivery config, legacy fallback policy | frontend tests |
| FrontendBlockRenderState | final | block IDs, reveal state, timing state, accessibility state | JS unit tests |
| E2EAcceptanceEvidence | final | Annette run, Alain run, transcript, screenshots, trace links, operational evidence | `tests/reports/GOC_FINAL_E2E_ACCEPTANCE.md` |
| Final transcript artifact | final | NPC response, NPC-to-NPC dialogue, environment interaction, narrator validity, no legacy blob | `tests/reports/goc_final_e2e_transcript.json` |

## Consumed By Next MVP

MVP 5 is the final guide. Consumed by final acceptance only.

MVP 5 → final:

```text
staged frontend
final E2E evidence
operational evidence
Annette transcript
Alain transcript
Narrative Gov cross-check
trace/export cross-check
```

## Services Touched

| Service | Purpose |
|---|---|
| frontend | staged block renderer, typewriter delivery, controls, accessibility, E2E shell |
| backend | ensure proxy/bootstrap passes render contract and diagnostics unchanged if used |
| world-engine / play-service | source of final SceneTurnEnvelope and diagnostics |
| administration-tool | Narrative Gov evidence cross-check for final report |
| tests/tooling | JS unit tests, browser/E2E tests, final reports, operational wiring |

## Files to Inspect First

- `frontend/static/play_shell.js` — response renderer and runtime calls.
- `frontend/templates/*play*` or actual play shell template — transcript DOM root and controls.
- `frontend/static/*.css` — staged transcript styling and accessibility.
- `frontend/tests/*` or create equivalent — JS/DOM tests.
- `tests/e2e/*` or closest browser test suite — final Annette/Alain acceptance.
- `backend/app/api/v1/game_routes.py` and `backend/app/services/game_service.py` — if frontend calls backend proxy.
- `world-engine/app/api/http.py` — response shape consumed by frontend.
- `administration-tool/*` Narrative Gov route/template tests for final cross-check.
- `tests/run_tests.py`, `.github/workflows/*.yml`, `pyproject.toml`, service TOMLs.

## Do Not Touch

- Do not collapse blocks into a single final blob.
- Do not make CSS-only typewriter animation the only behavior; it must be deterministic in tests.
- Do not regenerate runtime output when skipping/revealing animation.
- Do not accept legacy fallback as final acceptance.
- Do not reintroduce `visitor` in UI labels, dropdowns, tests, screenshots, or fallback state.
- Do not rename the five guide files or create TXT/no-loss/v2 duplicates.

## Targeted Search Commands

```bash
rg "visible_scene_output|blocks|legacy_blob|typewriter|render" -n frontend backend world-engine tests
rg "play_shell|session_start|launcher|selected_player_role|Annette|Alain|visitor" -n frontend backend tests
rg "Playwright|selenium|browser|e2e|screenshot|transcript" -n tests frontend .github pyproject.toml
rg "Narrative Gov|narrative_gov|trace_or_export|langfuse" -n administration-tool tests/reports tests
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
| MVP5-P01 | Frontend renderer | `frontend/static/play_shell.js` or equivalent | Render one DOM element per scene block with data attributes. | `test_frontend_does_not_collapse_to_single_blob` |
| MVP5-P02 | Typewriter delivery | JS renderer/state model | Add deterministic virtual clock test mode and delivery config. | `test_typewriter_uses_virtual_clock_in_test_mode` |
| MVP5-P03 | Skip/reveal controls | JS renderer and template | Skip current block and reveal all without additional runtime call. | `test_skip_current_animation`, `test_reveal_all_without_regeneration` |
| MVP5-P04 | Accessibility | renderer/config/CSS | Reduced motion disables typewriter and preserves content order. | `test_accessibility_mode_disables_typewriter` |
| MVP5-P05 | Legacy fallback policy | renderer and diagnostics consumer | Adapt legacy output only as degraded; fail final E2E if used. | `test_frontend_legacy_blob_fallback_is_marked_degraded`, `test_frontend_legacy_fallback_not_final` |
| MVP5-P06 | Final E2E | browser tests/reports | Run Annette and Alain end-to-end with transcript, screenshots, trace links, Narrative Gov cross-check. | `test_final_annette_e2e_evidence`, `test_final_alain_e2e_evidence` |
| MVP5-P07 | Operational wiring | `tests/run_tests.py`, workflows, TOMLs | Include frontend JS, browser/E2E, and final report suites. | operational checks |

## Data Contracts

### FrontendRenderContract

```json
{
  "contract": "frontend_render_contract.v1",
  "input_contract": "visible_scene_output.blocks.v1",
  "dom_contract": "dramatic_chat_blocks.v1",
  "one_dom_element_per_block": true,
  "legacy_blob_final_allowed": false,
  "required_controls": ["skip_current", "reveal_all", "accessibility_mode"],
  "diagnostics_required": true
}
```

### FrontendBlockRenderState

```json
{
  "contract": "frontend_block_render_state.v1",
  "block_id": "turn-4-block-2",
  "block_type": "actor_line",
  "actor_id": "veronique_houllie",
  "target_actor_id": "alain_reille",
  "total_characters": 52,
  "visible_characters": 17,
  "status": "rendering",
  "delivery_mode": "typewriter",
  "skippable": true
}
```

### TypewriterDeliveryConfig

```json
{
  "contract": "typewriter_delivery_config.v1",
  "mode": "typewriter",
  "characters_per_second": 44,
  "pause_before_ms": 150,
  "pause_after_ms": 650,
  "skippable": true,
  "render_test_mode": true,
  "clock": "virtual",
  "advance_time_api": "renderer.advanceBy(ms)"
}
```

### LegacyFallbackPolicy

```json
{
  "contract": "legacy_fallback_policy.v1",
  "legacy_blob_may_be_adapted_for_debug": true,
  "legacy_blob_marks_degraded": true,
  "legacy_blob_final_e2e_allowed": false,
  "degradation_signal": "legacy_visible_output_adapter_used"
}
```

### E2EAcceptanceEvidence

```json
{
  "contract": "e2e_acceptance_evidence.v1",
  "annette_run_required": true,
  "alain_run_required": true,
  "npc_to_npc_dialogue_required": true,
  "environment_interaction_required": true,
  "narrator_inner_voice_required": true,
  "trace_or_export_required": true,
  "narrative_gov_cross_check_required": true,
  "operational_gate_required": true
}
```

## Validation Rules

| Rule | Where Enforced | Error Code | Test Name | Diagnostic Field |
|---|---|---|---|---|
| render input must match schema | frontend schema/renderer guard | `invalid_delivery_schema` | `test_invalid_delivery_schema_rejected` | `frontend_render_contract.version` |
| final output cannot be one blob | DOM tests and final E2E | `frontend_single_blob_final_output` | `test_frontend_does_not_collapse_to_single_blob` | `dom.one_element_per_block` |
| legacy fallback is degraded | renderer diagnostics consumer | `frontend_legacy_blob_fallback_not_final` | `test_frontend_legacy_blob_fallback_is_marked_degraded` | `quality.degradation_signals` |
| legacy fallback cannot pass final E2E | final E2E gate | `frontend_legacy_fallback_not_final` | `test_frontend_legacy_fallback_not_final` | `frontend_render_contract.legacy_blob_used` |
| typewriter must be testable | renderer virtual clock | `typewriter_not_deterministic` | `test_typewriter_uses_virtual_clock_in_test_mode` | `render_test_mode` |
| skip current animation does not call runtime | renderer controls | `skip_caused_runtime_regeneration` | `test_skip_current_animation` | `runtime_call_count` |
| reveal all does not call runtime | renderer controls | `reveal_all_caused_runtime_regeneration` | `test_reveal_all_without_regeneration` | `runtime_call_count` |
| accessibility disables animation | renderer config/reduced motion | `accessibility_typewriter_not_disabled` | `test_accessibility_mode_disables_typewriter` | `accessibility_mode` |
| final Annette E2E evidence required | browser E2E final report | `final_annette_e2e_missing` | `test_final_annette_e2e_evidence` | `e2e.annette_run` |
| final Alain E2E evidence required | browser E2E final report | `final_alain_e2e_missing` | `test_final_alain_e2e_evidence` | `e2e.alain_run` |

### Wave-Hardening Validation Rules

| Rule | Where Enforced | Error Code | Test Name | Diagnostic Field |
|---|---|---|---|---|
| Source Locator Matrix contains no unresolved placeholders before patching | implementation report preflight | `source_locator_unresolved` | `test_source_locator_matrix_has_no_placeholders_before_patch` | `source_locator.status` |
| operational evidence lists exact MVP-specific suites/files/markers | operational report validator | `operational_suite_evidence_missing` | `test_operational_report_lists_mvp_specific_suites` | `operational_gate.mvp_specific_suites` |
| fixed MVP operational evidence artifact exists | operational report validator | `operational_evidence_artifact_missing` | `test_operational_evidence_artifact_exists_for_mvp` | `operational_gate.artifact_path` |

| browser runner and artifact locator table is complete | implementation report preflight | `browser_artifact_locator_missing` | `test_browser_artifact_locator_complete` | `browser_artifact_locator.status` |


## Examples

### Frontend render input

```json
{
  "visible_scene_output": {
    "contract": "visible_scene_output.blocks.v1",
    "blocks": [
      {
        "id": "turn-4-block-1",
        "block_type": "narrator",
        "speaker_label": "You notice",
        "text": "You notice the pause before Alain answers.",
        "delivery": {"mode": "typewriter", "characters_per_second": 44, "pause_before_ms": 150, "pause_after_ms": 650, "skippable": true}
      },
      {
        "id": "turn-4-block-2",
        "block_type": "actor_line",
        "speaker_label": "Véronique",
        "actor_id": "veronique_houllie",
        "target_actor_id": "alain_reille",
        "text": "You keep turning this into a legal question."
      }
    ]
  },
  "diagnostics": {
    "frontend_render_contract": {"version": "dramatic_chat_blocks.v1", "scene_block_count": 2, "render_mode": "typewriter", "typewriter_enabled": true, "legacy_blob_used": false}
  }
}
```

### Rendered transcript DOM

```html
<div data-scene-block-id="turn-4-block-1" data-block-type="narrator"></div>
<div data-scene-block-id="turn-4-block-2" data-block-type="actor_line" data-actor-id="veronique_houllie" data-target-actor-id="alain_reille"></div>
```

Forbidden final DOM:

```html
<div id="visible-output">all blocks joined into one blob</div>
```

### Typewriter delivery config

```json
{
  "render_test_mode": true,
  "clock": "virtual",
  "advance_time_api": "renderer.advanceBy(ms)",
  "expected": {"initial_visible_characters": 0, "visible_after_500ms": ">0", "visible_after_reveal_all": "all"}
}
```

### Skip current animation

```json
{
  "actions": ["start rendering block 1", "skip current block"],
  "expected": {"block_1_status": "complete", "runtime_call_count": 0}
}
```

### Reveal all

```json
{
  "actions": ["start rendering block 1", "reveal all"],
  "expected": {"all_pending_blocks_visible": true, "runtime_call_count": 0}
}
```

### Accessibility mode

```json
{
  "typewriter_enabled": false,
  "all_blocks_visible_immediately": true,
  "content_order_preserved": true,
  "no_runtime_regeneration": true
}
```

### Legacy fallback degraded

```json
{
  "visible_scene_output": {
    "contract": "visible_scene_output.blocks.v1",
    "blocks": [{"block_type": "system_degraded_notice", "text": "Legacy visible output was adapted into blocks."}]
  },
  "diagnostics": {
    "frontend_render_contract": {"legacy_blob_used": true},
    "quality": {"outcome": "ok_with_degradation", "quality_class": "degraded", "degradation_signals": ["legacy_visible_output_adapter_used"]}
  }
}
```

### Final Annette E2E evidence

```json
{
  "selected_player_role": "annette",
  "human_actor_id": "annette_reille",
  "visitor_present": false,
  "npc_actor_response_present": true,
  "npc_to_npc_dialogue_present": true,
  "environment_interaction_present": true,
  "narrator_inner_voice_valid": true,
  "legacy_blob_used": false,
  "trace_or_export_path": "tests/reports/langfuse/annette_turn_trace.json"
}
```

### Final Alain E2E evidence

```json
{
  "selected_player_role": "alain",
  "human_actor_id": "alain_reille",
  "visitor_present": false,
  "npc_actor_response_present": true,
  "npc_to_npc_dialogue_present": true,
  "environment_interaction_present": true,
  "narrator_inner_voice_valid": true,
  "legacy_blob_used": false,
  "trace_or_export_path": "tests/reports/langfuse/alain_turn_trace.json"
}
```

### Final transcript artifact

```json
{
  "contract": "goc_final_e2e_transcript.v1",
  "annette_run": {
    "selected_player_role": "annette",
    "human_actor_id": "annette_reille",
    "visitor_present": false,
    "npc_actor_response_present": true,
    "npc_to_npc_dialogue_present": true,
    "environment_interaction_present": true,
    "narrator_inner_voice_valid": true,
    "legacy_blob_used": false,
    "trace_or_export_path": "tests/reports/langfuse/annette_turn_trace.json"
  },
  "alain_run": {
    "selected_player_role": "alain",
    "human_actor_id": "alain_reille",
    "visitor_present": false,
    "npc_actor_response_present": true,
    "npc_to_npc_dialogue_present": true,
    "environment_interaction_present": true,
    "narrator_inner_voice_valid": true,
    "legacy_blob_used": false,
    "trace_or_export_path": "tests/reports/langfuse/alain_turn_trace.json"
  },
  "operational_gate": {"docker_up_status": "passed", "run_test_status": "passed", "github_workflow_status": "covered", "toml_tooling_status": "covered"}
}
```


### Final artifact index

The final E2E evidence index must be written to:

```text
tests/reports/GOC_FINAL_E2E_ARTIFACT_INDEX.md
```

It must link the Annette transcript, Alain transcript, screenshots, browser logs, trace or local export files, Narrative Gov evidence, and operational evidence artifacts.

### Browser Runner and Artifact Locator Table

Before implementation, fill this table with concrete repository paths.

| Area | Actual Path / Command | Required Evidence |
|---|---|---|
| frontend renderer file | `<fill>` | function/class that renders scene blocks |
| frontend template/route | `<fill>` | route/template used by play shell |
| JS/unit test config | `<fill>` | command included in `tests/run_tests.py` |
| browser/E2E framework | `<fill>` | Playwright/Selenium/other actual command |
| browser config file | `<fill>` | config path and browser mode |
| screenshot output directory | `<fill>` | linked from final artifact index |
| transcript JSON output path | `<fill>` | linked from final artifact index |
| trace export path | `<fill>` | linked from final artifact index |
| Narrative Gov evidence path | `<fill>` | linked from final artifact index |
| operational evidence path | `<fill>` | linked from final artifact index |

Required error code:

```text
browser_artifact_locator_missing
```

Required test:

```text
test_browser_artifact_locator_complete
```

## Required Tests

- `test_invalid_delivery_schema_rejected`
- `test_frontend_does_not_collapse_to_single_blob`
- `test_frontend_legacy_blob_fallback_is_marked_degraded`
- `test_frontend_legacy_fallback_not_final`
- `test_typewriter_uses_virtual_clock_in_test_mode`
- `test_skip_current_animation`
- `test_reveal_all_without_regeneration`
- `test_accessibility_mode_disables_typewriter`
- `test_final_annette_e2e_evidence`
- `test_final_alain_e2e_evidence`
- `test_final_e2e_transcript_contains_trace_and_narrative_gov_links`
- all mandatory operational checks from this guide

## Required ADRs

Required for this MVP:

- ADR-014 Interactive Text-Adventure Frontend
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
| `tests/run_tests.py` | include frontend JS tests, browser/E2E tests, final transcript/report checks | run-test log |
| GitHub workflows | include frontend/browser suites and do not silently skip E2E | workflow anchors |
| TOML/tooling | include frontend/e2e test markers and required browser config | config assertions |
| `docker-up.py` | start all four services for final E2E | startup log and final report |
| reports | write `tests/reports/GOC_FINAL_E2E_ACCEPTANCE.md` and `tests/reports/goc_final_e2e_transcript.json` | report artifacts |

## Handoff to Next MVP

Not applicable for this MVP because it is the final guide in the five-MVP package.

Final handoff:

```text
staged frontend
final E2E evidence
operational evidence
Annette run evidence
Alain run evidence
trace/export links
Narrative Gov cross-check
```

## Stop Condition

Stop only when:

1. Frontend renders one DOM element per scene block.
2. Typewriter delivery is deterministic in tests.
3. Skip/reveal controls do not trigger runtime regeneration.
4. Accessibility mode disables animation while preserving content order.
5. Legacy fallback is marked degraded and cannot pass final E2E.
6. Annette and Alain final E2E runs prove NPC agency, NPC-to-NPC dialogue, environment interaction, narrator validity, no `visitor`, no legacy blob, trace/export evidence, and Narrative Gov cross-check.
7. P13 staged frontend proof is complete before final P12 acceptance closure.
8. Operational gate evidence is complete.

## Claude Implementation Prompt

You are implementing MVP 5 only: Interactive Text-Adventure Frontend and Final E2E.

Inspect first:

```text
frontend/static/play_shell.js
frontend/templates/*play*
frontend/static/*.css
frontend/tests/*
tests/e2e/*
backend/app/api/v1/game_routes.py
backend/app/services/game_service.py
world-engine/app/api/http.py
administration-tool/*
tests/run_tests.py
.github/workflows/*.yml
pyproject.toml
```

Fill the Source Locator Matrix. Implement Patch Map rows MVP5-P01 through MVP5-P07. Add FrontendRenderContract, FrontendBlockRenderState, TypewriterDeliveryConfig, LegacyFallbackPolicy, E2EAcceptanceEvidence, JS/DOM tests, browser E2E tests, final transcript, and operational evidence. Do not change earlier MVP contracts except to fix mismatches required by tests. Stop when the Stop Condition passes.

## Token Discipline

Do not inspect unrelated files.
Do not restate architecture.
Do not implement later MVPs.
Do not create broad audit reports.
Do not accept field presence as behavior.
Stop when the listed stop condition passes.
