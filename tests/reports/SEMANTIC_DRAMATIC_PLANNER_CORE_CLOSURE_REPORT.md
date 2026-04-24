# Semantic Dramatic Planner Core Closure Report

## 1. Executive summary

This work completes **integrated closure of roadmap phases 0–4** for the God of Carnage (GoC) vertical slice inside the **existing** `RuntimeTurnState` LangGraph (`ai_stack/langgraph_runtime.py`). The runtime adds canonical planner contracts, deterministic semantic move interpretation, explicit social-state projection, CharacterMind records with provenance, and a **planner-canonical** `ScenePlanRecord` that consolidates scene function, responder, pacing, and silence for downstream use. **Validation, commit, and visible-output seams are unchanged in authority**: the planner remains advisory until those seams run. **No second runtime graph** and **no Phase 5 or Phase 6** dramatic-effect gate or generalization closure were implemented.

## 2. Implemented files and responsibilities

| Area | Files |
|------|--------|
| Contracts | `ai_stack/semantic_move_contract.py`, `ai_stack/character_mind_contract.py`, `ai_stack/social_state_contract.py`, `ai_stack/scene_plan_contract.py` |
| Semantic move | `ai_stack/semantic_move_interpretation_goc.py` — normalization, `interpreted_input` signals, synset features, explicit priority rules; **not** a wrapper over legacy keyword output |
| Social state | `ai_stack/social_state_goc.py` — derives `SocialStateRecord` from continuity, threads, thread summary, scene assessment |
| Character mind | `ai_stack/character_mind_goc.py` — YAML-backed tactical labels with `authored` / `authored_derived` / `fallback_default` provenance |
| Director / scene selection | `ai_stack/scene_director_goc.py` — `semantic_move_to_scene_candidates()` drives primary scene-function candidates; `_legacy_keyword_scene_candidates()` only when `semantic_move_record` is absent |
| Graph integration | `ai_stack/langgraph_runtime.py` — `director_assess_scene` sets `semantic_move_record` + `social_state_record`; `director_select_dramatic_parameters` builds responder/function from semantic path, `character_mind_records`, `scene_plan_record` |
| Operator / diagnostics | `ai_stack/langgraph_runtime.py` `_package_output` → `graph_diagnostics.planner_state_projection`; `ai_stack/goc_turn_seams.py` `build_operator_canonical_turn_record` exposes the same fields |

## 3. SemanticMove implementation truth

- **Inputs**: `player_input`, `interpreted_input`, `interpreted_move`, `prior_continuity_classes`.
- **Mechanism**: Unicode NFC normalization, bounded **synonym sets** (e.g. accusation includes “responsible”, “accountable”, “that is on you”, not only “blame”), structured **feature_snapshot**, **ordered priority rules** (e.g. `competing_repair_and_reveal` before single repair when both repair and reveal signals fire).
- **Output**: `SemanticMoveRecord` with `interpretation_trace` step IDs — inspectable, deterministic for fixed inputs on the GoC path.

## 4. CharacterMind provenance and canonicalization truth

- Sourced from `goc_yaml_slice` (`character_voice`, `characters`) and `guidance_phase_key_for_scene_id`.
- **Provenance** per field: `authored` for explicit YAML; `authored_derived` with `derivation_key` for role→tactical mapping; `fallback_default` only when needed.
- **No** unconstrained LLM fill of psychology.

## 5. SocialState implementation truth

- `SocialStateRecord` aggregates prior continuity classes, scene pressure string, thread count, presence of thread pressure summary, guidance phase, and a bounded **responder asymmetry** code.
- **Derived only** — not a competing world-truth store.

## 6. Scene planner migration truth

- **Same graph nodes**: `director_assess_scene` → `director_select_dramatic_parameters` → … → `validate_seam` → `commit_seam` → `render_visible`.
- **ScenePlanRecord** is the **canonical planner-facing selection surface** for `selected_scene_function`, `selected_responder_set`, `pacing_mode`, `silence_brevity_decision`, `selection_source`, and fingerprints; legacy keyword path is **only** used when `semantic_move_record` is missing (`legacy_fallback`).

## 7. Graph integration truth

- Single `StateGraph(RuntimeTurnState)`; new fields are plain serializable dicts on `RuntimeTurnState`.
- `multi_pressure_resolution.selection_source` records `semantic_pipeline_v1` vs `legacy_fallback`.

## 8. Regression posture and golden-case coverage

- Existing GoC phase scenarios (e.g. multi-pressure repair+reveal) preserved via **semantic** `competing_repair_and_reveal` producing both `repair_or_stabilize` and `reveal_surface` candidates so tie-break still yields `reveal_surface` where required.
- New tests: `test_semantic_planner_contracts.py`, `test_semantic_move_interpretation_goc.py`, `test_character_mind_goc.py`, `test_social_state_goc.py`, `test_semantic_planner_graph_authority.py`, `test_semantic_planner_golden_cases.py`.

## 9. Test commands run

```text
python -m pytest ai_stack/tests -q --tb=line
```

**Result (2026-04-09):** `196 passed`.

## 10. Pass/fail vs acceptance criteria

| Criterion | Status |
|-----------|--------|
| Serializable contracts for four record types | Pass |
| CharacterMind provenance implemented and inspectable | Pass |
| Single LangGraph truth surface | Pass |
| Validation / commit / visible-output authority unchanged | Pass |
| No second planner graph or sidecar | Pass |
| Director path upgraded with bounded semantic planning | Pass |
| SemanticMove not keyword-only (synsets + priority + `interpretation_trace`) | Pass |
| SocialState planner-facing, derived | Pass |
| ScenePlanRecord planner-canonical within graph | Pass |
| Diagnostics derived, non-sovereign | Pass |

## 11. No second runtime truth surface

Confirmed: planner state is stored on the same `RuntimeTurnState` and mirrored in `graph_diagnostics.planner_state_projection` and operator records as **read projections** only. Committed narrative truth remains behind `commit_seam` / `committed_result`.

## 12. Validation, commit, visible-output seams intact

Confirmed: `run_validation_seam` and `run_commit_seam` / `run_visible_render` are still invoked from the same graph nodes; `validate_seam` and `commit_seam` remain in `nodes_executed`.

## 13. Phases 5 and 6 not implemented

Confirmed: no dramatic-effect gate closure (Phase 5) and no controlled generalization closure (Phase 6) beyond what is strictly required for phases 0–4.

## 14. Explicit non-goals (this task)

- Phase 5 dramatic-effect gate closure.
- Phase 6 controlled generalization.
- Second planner architecture or planner-side committed truth.
- Free-form model-authored character psychology.
