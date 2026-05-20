# ADR-0062: Director Realization Thin Path (Resolver → Director → Narrator)

## Status

Accepted

## Date

2026-05-19

## Related ADRs

- [ADR-0034](adr-0034-player-facing-narrative-shell-contract.md) — player-facing block stream; thin-path movement folds narrator realization into `player_input_outcome`.
- [ADR-0036](adr-0036-player-session-output-language.md) — `session_output_language` drives visible realization.
- [ADR-0038](adr-0038-canonical-turn-lifecycle-single-commit-path.md) — thin path still commits through `validate_seam` → `commit_seam`.
- [ADR-0041](adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md) — capability names are semantic; LDSS full-pipeline capabilities are not invoked on the default player thin path.
- [ADR-0054](adr-0054-session-input-language-english-internal-resolution.md), [ADR-0055](adr-0055-semantic-player-input-translation-ingress.md) — translate ingress unchanged.
- [ADR-0057](adr-0057-canon-safe-player-freedom-and-affordance-inference.md) — mundane movement and perception must use model realization in `session_output_language`, not English `description` echo.

## Context

Live traces (2026-05-18/19) showed that mundane German player movement (“Gehe in die Küche”, “Ich gehe ins Bad”) produced English bleed from `scene_affordance_model.description` via a deterministic short path (`authoritative_action_resolution`) that bypassed the Director and LLM realization. Questions routed to `full_pipeline` could fail with `dramatic_irony_hidden_fact_echo` after the fact.

The product requirement is fixed: **Resolver classifies and translates; Director composes what to realize; Narrator/Actor-Line realizes in `session_output_language`.** No binary router between “short path” and “full monolithic pipeline” for ordinary player turns.

## Decision

1. **Replace the player-turn router** `_route_after_resolve_player_action` and node `authoritative_action_resolution` with a mandatory thin path:
   - `resolve_player_action` → `director_compose_realization` → `realize_via_capabilities` → `route_model` → `invoke_model` → `proposal_normalize` → `validate_seam` → `commit_seam` → `render_visible` → `package_output`.

2. **Introduce `realization_plan.v1`** composed by `ai_stack/story_runtime/director/director_realization_composer.py` (`compose_realization_plan`). PR-A (movement) uses deterministic composition; PR-A.2/3 add semantic LLM composition and richer capabilities.

3. **Capability vocabulary (semantic names, not Π-IDs):**
   - `narrator.location_transition.describe` — movement to a known location.
   - `narrator.perception.describe` — in-world answer to a perception question about a known location/object.
   - `narrator.clarification.describe` — resolver uncertain / unknown target.
   - `narrator.kanon_break_refusal.describe` — `kanon_break=true`.
   - `actor_line.speech` — player speech act.

4. **Visible text** for thin-path narrator capabilities is produced only by LLM invocation in `session_output_language` (`ThinPathRuntimeOutput` parser variant). No echo of English `description` fields from affordance YAML.

5. **Player shell fold (movement):** when the thin path realizes via `narrator.*`, the diegetic text is folded into the `player_input_outcome` card; duplicate standalone `narrator` blocks are suppressed for that turn when no NPC lines are present (`world-engine/app/story_runtime/manager/`).

6. **State propagation:** `RuntimeTurnState` and `observability_path_summary` carry `realization_plan`, `realize_via_capabilities_used_capability`, `realize_via_capabilities_outcome`, `kanon_break`, `kanon_break_reason`, `director_path_mode`.

7. **Operator diagnostics:** `GET /api/story/sessions/{session_id}/thin-path-summary` exposes per-turn thin-path evidence; world-engine UI **Narrative Systems** renders it via backend proxy `admin/world-engine/story/sessions/{id}/thin-path-summary`.

8. **LDSS / full dramatic pipeline** nodes (`retrieve_context`, `derive_*`, `synthesize_context`, `assemble_model_context`, scene director assess/select) remain in the graph for future re-entry but are **not** on the default player-turn edge list after `resolve_player_action`.

9. **`build_synthetic_generation_for_action_resolution`** remains in the repository for legacy/tests but is **not** called from the player-turn graph.

## Consequences

**Positive:**

- Mundane movement and perception questions get German (or session-language) LLM realization anchored in destination context, not English affordance fallback.
- Director is always consulted; path summaries show non-empty `capabilities_selected` and `realization_plan`.
- Operator can verify Resolver → Director → Narrator per turn without Langfuse-only archaeology.

**Negative / trade-offs:**

- Token cost per mundane movement turn increases (Director compose is deterministic in PR-A; one narrator LLM call per turn).
- LLM outage surfaces as turn failure rather than silent English template bleed (intentional transparency).
- PR-A.2/3 still required for object interaction, RAG, and moving `dramatic_irony` validation ahead of realization.

## Testing

| Layer | Command / file | Expectation |
|-------|----------------|-------------|
| Composer invariants | `ai_stack/tests/test_runtime_authority_aspects.py` | `compose_realization_plan` routes movement, perception, speech, clarification, kanon_break |
| Graph shape | `ai_stack/tests/test_langgraph_runtime.py` | thin-path nodes present; `authoritative_action_resolution` absent |
| Thin-path API | `world-engine/tests/test_thin_path_summary_api.py` | `get_thin_path_summary` + HTTP route |
| Live smoke (opt-in) | `WOS_THIN_PATH_LIVE_SMOKE=1 python -m pytest tests/smoke/test_thin_path_pr_a_live_smoke.py` | real stack; path properties + no English bleed |

Per [ADR-0039](adr-0039-gate-tests-no-hardcoded-oracle-bypass.md): assert path properties and contract fields, not fixture input strings.

## Operational evidence

- Implementation plan and step log: `RESOLVER_DIRECTOR_NARRATOR_THIN_PATH_PLAN.md` (PR-A complete 2026-05-19).
- Binding technical contract: `docs/technical/runtime/director_realization_thin_path_contract.md`.
