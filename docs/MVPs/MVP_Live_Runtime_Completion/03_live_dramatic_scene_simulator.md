# MVP_Live_Runtime_Completion — MVP 3 — Live Dramatic Scene Simulator

## Mission

Implement the live dramatic scene simulator (LDSS) as a non-optional live-path component that emits structured staged scene blocks for God of Carnage solo play.

LDSS must produce visible NPC dramatic behavior, NPC-to-NPC communication, valid environment interaction, and narrator inner-perception blocks while respecting MVP 2 actor lanes, object admission, and state-delta boundaries.

## Scope

In scope:

- `SceneTurnEnvelope.v2` as final live turn output shape.
- `SceneBlock` for narrator, actor line, actor action, environment interaction, and system degraded notice.
- `LDSSInput` and `LDSSOutput` contracts.
- `NPCAgencyPlan` with non-passive NPC decisions.
- EnvironmentInteraction with canonical, typical, and `similar_allowed` affordance validation.
- NarratorVoiceValidation and PassivityValidation.
- Live-path proof from HTTP turn route through runtime manager, LangGraph/AI seam, LDSS, validation, commit, and response packaging.

Out of scope:

- Langfuse/Narrative Gov final UI; MVP 3 emits trace scaffold consumed by MVP 4.
- Final frontend typewriter UX; MVP 3 emits renderable blocks consumed by MVP 5.

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

## Consumed By Next MVP

MVP 4 consumes LDSS live path, scene blocks, simulator diagnostics scaffold, trace scaffold, validation outcomes, passivity status, and degradation signals.

## Services Touched

| Service | Purpose |
|---|---|
| world-engine / play-service | real turn route and commit path integration |
| ai_stack | LDSS generation/seam, NPC agency plan, validation packaging |
| backend | pass-through of final SceneTurnEnvelope response if backend proxies play-service |
| tests/tooling | unit, integration, and live-route tests |

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
| MVP3-P02 | Live-path integration | HTTP turn -> runtime manager -> ai_stack seam -> LDSS -> validators -> commit -> response | Prove actual turn route invokes LDSS; no fake route. | `test_live_turn_route_invokes_ldss` |
| MVP3-P03 | NPC agency | `NPCAgencyPlan`, responder plan seam | Require visible NPC actor response and allow NPC-to-NPC dialogue. | `test_npc_to_npc_dialogue_present`, `test_no_visible_actor_response_triggers_retry_or_degradation` |
| MVP3-P04 | Environment affordances | affordance validator, object admission consumer | Validate canonical/typical/similar and reject hallucinated objects. | `test_similar_allowed_requires_similarity_reason`, `test_rejects_unadmitted_plausible_object` |
| MVP3-P05 | Narrator contract | narrator validator | Narrator is inner perception/orientation only; reject recap/forced state/hidden intent. | narrator tests |
| MVP3-P06 | Final response guard | response packager | Reject no blocks, legacy-only output, narrator-only passive output. | `test_scene_blocks_required_for_final_response`, `test_legacy_only_output_fails_final_response` |
| MVP3-P07 | Operational wiring | `tests/run_tests.py`, workflows, TOMLs | Include unit/integration/live-route LDSS suites. | operational checks |

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

### NPCAgencyPlan

```json
{
  "contract": "npc_agency_plan.v1",
  "turn_number": 4,
  "primary_responder_id": "veronique_houllie",
  "secondary_responder_ids": ["alain_reille"],
  "npc_initiatives": [
    {
      "actor_id": "veronique_houllie",
      "intent": "challenge_alain_deflection",
      "allowed_block_types": ["actor_line"],
      "target_actor_id": "alain_reille",
      "passivity_risk": "low"
    },
    {
      "actor_id": "alain_reille",
      "intent": "evade_by_phone_attention",
      "allowed_block_types": ["actor_action"],
      "target_actor_id": null,
      "passivity_risk": "low"
    }
  ]
}
```

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
- `test_narrator_rejects_dialogue_recap`
- `test_narrator_modal_language_does_not_force_player_state`
- `test_narrator_cannot_reveal_hidden_npc_intent`
- all mandatory operational checks from this guide

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
