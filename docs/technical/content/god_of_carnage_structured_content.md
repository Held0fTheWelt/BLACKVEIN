# God of Carnage — Structured Content & Runtime Gates

Status: implementation-facing reference (GOC-KNOWLEDGE-RUNTIME-INTEGRATION).

## Module-authoring language

- Authored module content is **English**. Runtime locale output may be German (or
  any other language) via `session_output_language` / `locale/*` data.
- The English knowledge layer lives in:
  - `content/modules/god_of_carnage/knowledge/` (machine-readable runtime contracts)
  - `content/modules/god_of_carnage/{apartment_layout,apartment_objects,actor_pressure_profiles,phase_beat_policy}.yaml`
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
| `apartment_layout.yaml` | affordance resolution, player-local context, RAG | `apartment_layout_loaded` |
| `apartment_objects.yaml` | affordance resolution, narrator packet, RAG | `apartment_objects_loaded` |
| `actor_pressure_profiles.yaml` | scene director responder selection, narrator packet | `actor_pressure_profile_used`, `actor_pressure_profiles_loaded` |
| `phase_beat_policy.yaml` | scene director dramatic parameters, pacing gate | `phase_policy_applied`, `phase_beat_policy_loaded` |

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

## Observability

`environment` may be `staging` (no longer hardcoded `live`). MCP discovery
(`tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_query_traces`)
accepts an `environment` argument. Backend root traces (`backend.turn.execute`)
and world-engine spans (`world-engine.turn.execute`, `world-engine.session.create`)
are filterable by environment, trace_origin, and canonical_player_flow.
