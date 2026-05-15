# God of Carnage — Structured Content & Runtime Gates

Status: implementation-facing reference (GOC-KNOWLEDGE-RUNTIME-INTEGRATION).

## Module-authoring language

- Authored module content is **English**. Runtime locale output may be German (or
  any other language) via `session_output_language` / `locale/*` data.
- The English knowledge layer lives in:
  - `content/modules/god_of_carnage/knowledge/` (machine-readable runtime contracts)
  - `content/modules/god_of_carnage/module.yaml`
  - `content/modules/god_of_carnage/{apartment_layout,apartment_objects,actor_pressure_profiles,phase_beat_policy,memory_policy}.yaml`
- Runtime-localized strings live in `content/modules/god_of_carnage/locale/`
  (e.g. `locale/scene_affordances.yaml`).

## Authority precedence

`content/modules/<module_id>/knowledge/*.yaml` and root structured YAMLs are the
canonical authored module truth. RAG retrieval supports generation but **does not**
decide hard-forbidden pass/fail.

## Files and their runtime consumers

| File | Consumer(s) | Diagnostic surface |
|---|---|---|
| `knowledge/opening_scene_sequence.yaml` | `_goc_resolve_canonical_content`, `build_opening_scene_plan_metadata`, opening prompt builder | `opening_scene_sequence_id`, `opening_event_ids`, `opening_render_policy`, `opening_event_coverage_pass`, `opening_handover_contract_pass` |
| `knowledge/hard_forbidden_rules.yaml` | `detect_hard_forbidden_runtime` (validation seam), narrator packet | `hard_forbidden_detection`, `hard_forbidden_absent`, `opening_summary_only_absent`, per-category absent scores (`opening_player_speech_absent`, `opening_npc_exposition_absent`, `meta_runtime_language_absent`, `stage_direction_labels_absent`, `source_reproduction_absent`, `player_agency_violation_absent`) |
| `knowledge/premise_and_backstory.yaml` | narrator packet, opening prompt, RAG seed | `knowledge_runtime_loaded.premise_and_backstory_loaded` |
| `knowledge/narrator_sensory_palette.yaml` | narrator packet, scene-director dramatic parameters | `narrator_sensory_palette_loaded` |
| `apartment_layout.yaml` | `EnvironmentModel`, `StorySession.environment_state`, affordance resolution, player-local context, RAG | `apartment_layout_loaded`, `environment_state`, `environment_render_context`, `environment_state_now` |
| `apartment_objects.yaml` | `EnvironmentModel`, `StorySession.environment_state`, affordance resolution, narrator packet, RAG | `apartment_objects_loaded`, `environment_state`, `environment_render_context`, `environment_state_now` |
| `actor_pressure_profiles.yaml` | scene director responder selection, narrator packet | `actor_pressure_profile_used`, `actor_pressure_profiles_loaded` |
| `direction/character_voice.yaml` | character voice profile builder, prompt packet, runtime voice validator | `character_voice_profiles`, `voice_consistency_validation`, `turn_aspect_ledger.voice_consistency` |
| `phase_beat_policy.yaml` | scene director dramatic parameters, pacing gate | `phase_policy_applied`, `phase_beat_policy_loaded` |
| `module.yaml` / `runtime_intelligence` | `ModuleRuntimePolicy.runtime_governance_policy`, runtime route/capability/projection gates | `runtime_governance_policy`, `selection_source`, `capability_selection_valid`, `visible_projection_contract_pass`, `committed_result` |
| `memory_policy.yaml` | `ModuleRuntimePolicy.memory_policy`, hierarchical memory write/project contracts | `hierarchical_memory`, `memory_policy_applied`, `memory_write_from_committed_turn`, `memory_context_bounded`, `hierarchical_memory_contract_pass` |

## Hard-forbidden detection policy

The validation seam consumes `hard_forbidden_detection.reject_on` /
`recover_on` from `knowledge/hard_forbidden_rules.yaml`. Detection keys that
appear under `reject_on` block commit. Keys that appear under `recover_on`
trigger bounded recovery before commit. Hard-forbidden violations must not
silently commit as healthy. See `ai_stack/goc_knowledge_runtime_gates.py` /
`ai_stack/goc_turn_seams.py` for the wiring.

## Opening realization gate

Turn 0 (`turn_input_class == "opening"`) is validated against
`opening_scene_sequence.narrative_events`:

- `opening_event_coverage_pass = 1.0` requires every authored event id covered.
- `opening_handover_contract_pass = 1.0` requires `handover_to_scene_phase`
  matches the authored `phase_1` handover.
- `opening_summary_only_absent = 1.0` rejects summary-only openings via
  `narration_mode.min_visible_blocks`.
- Selected player character must not speak during opening (detection key
  `forced_player_speech` ⇒ reject).

## RAG indexing

`backend/app/content/compiler/compiler.py:_build_retrieval_seed` emits one
`RetrievalChunk` per structured-knowledge surface with metadata:

```
{
  "source_path": "content/modules/god_of_carnage/...",
  "content_kind": "opening_scene_sequence" | "hard_forbidden_rules" | ...,
  "authority": "module_canonical",
  "use_for": [...downstream consumers...],
  "module_id": "god_of_carnage",
  "language": "en",
  "runtime_locale_available": bool
}
```

RAG retrieval **does not override** deterministic contracts; it supports
generation only.

## Runtime intelligence policy

`module.yaml` supplies the module-specific `runtime_intelligence` policy that is
loaded into the generic `ModuleRuntimePolicy.runtime_governance_policy`. This is
content/configuration, not runtime-core branching. Runtime code consumes generic
policy keys such as:

- `action_resolution_short_path`: whether deterministic action-resolution
  routes may bypass later graph stages for allowed input kinds / semantic verbs.
- `visible_projection`: whether required visible origin metadata is mandatory
  and whether projection failures recover or hard-fail.
- `capability_gate`: what happens when required capabilities are missing or
  forbidden capabilities are realized.
- `continuity.hooks`: named compatibility hooks that may run after canonical
  commit without moving module-specific conditions into generic algorithms.

Module-specific actor names, room aliases, phase names, beat ids, and sample
prose stay in content files. Generic runtime validators read the policy and
ledger fields; they must not hardcode God of Carnage literals.

## Environment state / Pi15

The Pi15 environmental-story slice is implemented as bounded canonical state,
not as free-form narrator memory. `apartment_layout.yaml` and
`apartment_objects.yaml` are normalized into `EnvironmentModel`; session start
initializes `StorySession.environment_state` with current room, actor
locations, prop states, visible rooms, salient object ids, and recent
environment events.

Runtime consumers use the same state through the turn:

- Action resolution derives player-local context from `environment_state`.
- The LangGraph generation packet receives a compact environment context.
- The commit seam mutates environment state only after an approved committed
  action, such as a movement or admitted object interaction.
- Render support carries `environment_render_context.v1` and the shell projects
  `environment_state_now`.

ADR-0039 applies to this surface: tests derive rooms and objects from canonical
policy/content and assert schema/state relationships. Generated narration is not
the primary oracle for environment truth.

## Character voice policy

`direction/character_voice.yaml` is the canonical source for GoC voice guidance:
formal role, worldview, speech patterns, baseline tone, escalation arc, and the
global `voice_consistency` policy. Runtime compiles this into bounded
`CharacterVoiceProfileRecord` values and passes a compact profile set into the
LangGraph generation context.

Runtime enforcement is deliberately split:

- `maintain_consistency` and `pitfalls_to_avoid` guide generation and operator
  diagnostics.
- `forbidden_language_markers` is machine-readable policy. When a generated
  `spoken_lines` row contains one of those declared markers, validation records
  `voice_consistency_validation.v1`, marks the `voice_consistency` aspect as
  failed, and rejects through `runtime_voice_consistency_v1` before commit.
- `semantic_classification` is machine-readable policy for the deterministic
  profile classifier. It compares each spoken line against every active
  canonical profile across profile dimensions (worldview, register,
  syntax/rhythm, rhetorical strategy, and phase alignment), then emits profile
  rankings, runner-up confidence, dimension winners, ambiguity/mixed-signature
  evidence, and structured findings. `schema_plus_semantic` records
  high-confidence cross-actor voice confusion as a warning; `strict_rule_engine`
  rejects it through `runtime_voice_consistency_v2` before commit.

ADR-0039 applies here with extra force: `dialogue_examples` are authoring
examples, not correctness oracles. They must not be copied into tests as the
primary pass/fail signal, and runtime profile serialization omits them.

## Hierarchical memory policy

`memory_policy.yaml` is module content, not runtime-core logic. It enables the
generic hierarchical memory layer for bounded session-local tiers:

- `turn`
- `session`
- `actor`
- `module`

The `long_term` tier remains disabled for this module. Runtime writes require a
canonical committed turn, recoverable/rejected turns do not create memory truth,
and projected memory context must exclude raw prompts, secrets, full RAG
payloads, and raw player input.

## Observability

`environment` may be `staging` (no longer hardcoded `live`). MCP discovery
(`tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_query_traces`)
accepts an `environment` argument. Backend root traces (`backend.turn.execute`)
and world-engine spans (`world-engine.turn.execute`, `world-engine.session.create`)
are filterable by environment, trace_origin, and canonical_player_flow.
