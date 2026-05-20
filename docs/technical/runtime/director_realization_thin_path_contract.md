# Director realization thin path contract

**Status:** implemented (PR-A, 2026-05-19)  
**Normative ADR:** [ADR-0062](../../ADR/adr-0062-director-realization-thin-path.md)

## Purpose

Every ordinary player turn follows **Resolver → Director → Narrator/Actor-Line** without a deterministic English affordance echo or a monolithic “full pipeline” shortcut.

## Graph path (player turn)

```text
translate_player_input
  → interpret_input
  → resolve_player_action
  → director_compose_realization
  → realize_via_capabilities
  → route_model
  → invoke_model
  → proposal_normalize
  → validate_seam
  → commit_seam
  → render_visible
  → package_output
```

Meta/OOC input still branches at `interpret_input` → `meta_control_turn` → `package_output`.

Nodes **not** visited on this default player path include `retrieve_context`, `goc_resolve_canonical_content`, `director_assess_scene`, `director_select_dramatic_parameters`, all `derive_*` aspect nodes, `synthesize_context`, `assemble_model_context`, and the removed `authoritative_action_resolution` node.

## Contracts

### `realization_plan.v1`

Produced by `compose_realization_plan` in `ai_stack/director/director_realization_composer.py`.

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | `"realization_plan.v1"` | |
| `realization_owner` | `narrator` \| `actor_line` \| `narrator+actor_line` | |
| `capabilities_selected` | `string[]` | semantic capability ids |
| `outcome_disposition` | `{ outcome, reason }` | `success` \| `partial` \| `fail` |
| `language_target` | BCP-47 short code | mirrors `session_output_language` |
| `visibility_constraints` | `string[]` | optional |
| `decision_reason` | `string` | diagnostic |
| `target_location_id` | `string?` | movement extras |

### Resolver fields consumed

From `resolve_player_action` / affordance frame:

- `kanon_break`, `kanon_break_reason`
- `player_action_frame`, `affordance_resolution`
- `session_output_language`

Glück (success/partial/fail coloring) is owned by the Director in later PRs; not emitted by the Resolver in PR-A.

### Capabilities (PR-A)

| Capability | When |
|------------|------|
| `narrator.location_transition.describe` | movement + known location + `commit_action` |
| `narrator.perception.describe` | question/perception + known location/object |
| `narrator.clarification.describe` | `needs_clarification`, unknown/ambiguous target |
| `narrator.kanon_break_refusal.describe` | `kanon_break=true` |
| `actor_line.speech` | `commit_speech` / speech act |

### Observability (`observability_path_summary`)

| Field | Meaning |
|-------|---------|
| `realization_plan` | composed plan |
| `realize_via_capabilities_used_capability` | capability actually invoked |
| `realize_via_capabilities_outcome` | invoke outcome |
| `kanon_break`, `kanon_break_reason` | resolver decision |
| `director_path_mode` | `director_realization_composer` when plan present |
| `selected_capabilities` | mirrors plan capabilities |
| `nodes_executed` | must include thin-path nodes |

### Operator API

- World-Engine: `GET /api/story/sessions/{session_id}/thin-path-summary?limit=N`
- Backend proxy: `GET /api/v1/admin/world-engine/story/sessions/{session_id}/thin-path-summary`
- UI: world-engine **Narrative Systems** → panel “Thin path — Resolver → Director → Narrator”

Schema: `thin_path_summary.v1` from `StoryRuntimeManager.get_thin_path_summary`.

### Player-visible fold

When `realize_via_capabilities_used_capability` starts with `narrator.` and the turn has no NPC lines, narrator realization text is copied into the `player_input_outcome` block and redundant `narrator` scene blocks are dropped for that turn.

### Narrated actor speech

`realization_owner = narrator+actor_line` does not require two visible cards.
When prose framing and actor speech form one literary unit, the visible block may
be:

- `block_type: narrator`
- `composition_kind: narrated_actor_speech`
- `embedded_speech_spans[]` carrying the actor `actor_id`, `speech_text`, and
  speech act

The narrator owns the prose frame; the actor owns the embedded direct speech.
Downstream responder detection and voice/speaker diagnostics must inspect
`embedded_speech_spans[]` as well as ordinary `actor_line` blocks.

## Verification

```bash
# Unit / graph
python tests/run_tests.py --suite ai_stack -k "thin_path or realization_plan or compose_realization"
python tests/run_tests.py --suite engine -k thin_path_summary

# Live stack (opt-in)
WOS_THIN_PATH_LIVE_SMOKE=1 python -m pytest tests/smoke/test_thin_path_pr_a_live_smoke.py -v
```

## Follow-on work (out of PR-A scope)

- PR-A.2: `narrator.environment_interaction`, RAG, plausible inference objects.
- PR-A.3: `dramatic_irony` as Director input before realization.
- PR-B: `canonical_path_effect: hold_current_step` propagation for free actions.
- PR-C: `gathering_paused` director mode.
