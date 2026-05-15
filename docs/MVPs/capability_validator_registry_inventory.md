# ADR-0041 Semantic Validator Registry Inventory

Last updated: 2026-05-15

Local governance inventory only. `proof_level=local_only`, `live_or_staging_evidence=false`.
This document does not promote Capability Matrix status or claim live/staging proof.

Canonical machine-readable rows: `ai_stack/capability_validator_registry.py::VALIDATOR_REGISTRY_INVENTORY`.

## Summary

| Status | Local validators | Observer diagnostics | Judges |
|--------|------------------|----------------------|--------|
| `implemented_callable` | 9 | 1 (sensory) | 0 |
| `implemented_but_needs_adapter` | 2 | 2 | 0 |
| `planned_only` | 1 | 0 | 0 |
| `observer_only` (planned) | 0 | 2 | 0 |
| `judge_only` | 0 | 0 | all `{capability}_judge` IDs |

Default runtime dispatch remains `dry_run`. The default semantic registry is **empty**.
Opt-in adapters: `build_semantic_validator_registry(include_available_adapters=True)`.

## Local validator contracts

| validator_id | capability | current_status | source | adapter_needed | safe_for_plan_enforced | blocking |
|--------------|------------|----------------|--------|----------------|------------------------|----------|
| narrator_authority_contract | narrator_authority | implemented_callable | `narrator_authority_validation::evaluate_narrator_authority_contract` | yes | yes | blocking |
| scene_energy_contract | scene_energy | implemented_callable | `scene_energy_engine::validate_scene_energy_realization` | yes | yes | blocking |
| environment_state_contract | environment_state | implemented_callable | `environment_state_contracts::evaluate_environment_state_contract` | yes | yes | blocking |
| information_disclosure_contract | information_disclosure | implemented_callable | `information_disclosure_engine::validate_information_disclosure_realization` | yes | yes | blocking |
| voice_consistency_contract | voice_consistency | implemented_callable | `character_voice_validation::validate_voice_consistency` | yes | yes | blocking |
| npc_agency_contract | npc_agency | implemented_callable | `npc_agency_realization::validate_npc_initiative_realization` | yes | yes | blocking |
| player_intent_contract | player_intent_inference | implemented_callable | `player_turn_validator_evaluation::evaluate_player_intent_contract` | yes | yes | blocking |
| action_resolution_contract | action_resolution | implemented_callable | `player_turn_validator_evaluation::evaluate_action_resolution_contract` | yes | yes | blocking |
| consequence_cascade_contract | consequence_cascade | implemented_but_needs_adapter | `consequence_cascade_contracts::validate_consequence_cascade_record` | yes | no | blocking |
| forecast_contract | long_horizon_forecast | planned_only | `runtime_aspect_ledger` branching_forecast projection | yes | no | blocking |
| silence_negative_space_contract | silence_negative_space | implemented_but_needs_adapter | `silence_negative_space_contract::build_silence_negative_space_decision` | yes | no | blocking |
| dramatic_irony_contract | dramatic_irony | implemented_callable | `dramatic_irony_runtime::validate_dramatic_irony_realization` | yes | yes | blocking |

## Observer diagnostics

| validator_id | capability | current_status | source | adapter_needed | safe_for_plan_enforced | blocking |
|--------------|------------|----------------|--------|----------------|------------------------|----------|
| thematic_tracking_diagnostic | thematic_tracking | observer_only | `narrative_aspect_contracts::validate_narrative_aspects` | yes | no | non_blocking |
| callback_web_diagnostic | callback_web | observer_only | `callback_web_contracts::validate_callback_web_record` | yes | no | non_blocking |
| sensory_context_diagnostic | sensory_context | observer_only | `sensory_context_engine::validate_sensory_context_realization` | yes | yes (non_blocking) | non_blocking |

## Judges (disabled for ADR-0041 dispatch)

All IDs matching `{semantic_capability}_judge` from `capability_validator_plan.JUDGE_VALIDATORS`:

- **current_status:** `judge_only`
- **safe_for_local_plan_enforced:** false
- **must not register** in `build_default_semantic_validator_registry()` or `build_available_semantic_validator_registry()`
- LLM-as-a-Judge execution remains a future governed pass

## Registry builder policy

1. `build_default_semantic_validator_registry()` returns `{}`.
2. `build_available_semantic_validator_registry()` registers only rows with `safe_for_local_plan_enforced=true` and a thin adapter in code.
3. Missing context or unregistered IDs return `available=false`, `passed=false` — never success.
4. No dynamic import by string; no Pi / Π active runtime keys.

## Player-turn enforced registry

`build_player_turn_enforced_semantic_validator_registry()` exposes the normal player-turn enforced set:

- `player_intent_contract`
- `action_resolution_contract`
- `information_disclosure_contract`
- `voice_consistency_contract`
- `scene_energy_contract`

## NPC conflict-turn enforced registry

`build_npc_conflict_enforced_semantic_validator_registry()` exposes the NPC conflict-turn enforced set (selector: `npc_turn` + `npc_decision_required`):

- `npc_agency_contract`
- `voice_consistency_contract`
- `scene_energy_contract`
- `information_disclosure_contract`

## Turn-class coverage (local-only)

Canonical enforced validator IDs per turn class: `TURN_CLASS_ENFORCED_VALIDATORS` and
`get_turn_class_enforced_validators()` in `ai_stack/capability_validator_registry.py`.
Coverage vs an opt-in registry map: `get_registry_coverage_for_turn_class()` /
`assert_turn_class_registry_coverage()` (no validator execution; no production dispatch).

A **world-engine test harness** (`build_adr0041_validator_dispatch_harness_report`) can build the same
dispatch projection shape with opt-in plan-enforced execution when tests pass an explicit registry map and
`harness_allow_plan_enforced_local_dispatch=True`. Ledger normalization (`normalize_runtime_aspect_ledger`)
does not call this harness; default runtime intelligence projection stays dry-run.

| Turn class | Enforced validators (local-only complete when all IDs are in the opt-in registry) |
|------------|-----------------------------------------------------------------------------------|
| `opening_scene` | `narrator_authority_contract`, `scene_energy_contract`, `environment_state_contract`, `information_disclosure_contract`, `voice_consistency_contract` |
| `normal_player_turn` | `player_intent_contract`, `action_resolution_contract`, `information_disclosure_contract`, `voice_consistency_contract`, `scene_energy_contract` |
| `npc_conflict_turn` | `npc_agency_contract`, `voice_consistency_contract`, `scene_energy_contract`, `information_disclosure_contract` |

**Observer diagnostics** (non-blocking in execution plans; not production-gated as enforced validators):
`environment_state_diagnostic`, `thematic_tracking_diagnostic`, `callback_web_diagnostic`,
`sensory_context_diagnostic`. Optional situational observers (e.g. dramatic irony when
`knowledge_gap_present`) are not part of this fixed enforced/diagnostic table.

Default registry remains `{}`. Plan-enforced dispatch remains opt-in.

## ADR-0041 production orchestration readiness

See **ADR-0041 Production Orchestration Readiness** in
[`capability_selection_runtime_design.md`](capability_selection_runtime_design.md)
(audit 2026-05-15): runtime validation flow map, safe insertion anchors, Options A–C,
world-engine pytest cwd convention (`cd world-engine`), and confirmation that the
canonical executed-validator field name is **`actually_executed`** (there is no
`actually_detected` symbol in this repository).

## Pending integration

- Production world-engine / langgraph orchestration (not wired to plan_enforced)
- Consequence cascade, forecast, silence adapters
- Observer diagnostics in plan_enforced (remain non-blocking; not in opening enforced set)
- Commit/readiness gate coupling
- Live/staging proof
