# Inspector Workbench: Semantic Planner Projection Closure Report

## 1. Executive summary

This closure aligns the Administration Suite Inspector Workbench with the current semantic planner and dramatic-effect contracts **as read-only projections only**. Backend inspector services now pass through canonical `DramaticEffectGateOutcome` fields, isolate legacy score-style keys under `legacy_compatibility_summary`, emit a backend-computed `semantic_decision_flow` with explicit per-stage `presence`, and extend timeline, comparison, coverage, and provenance-raw projections with bounded gate/posture/support signals. Support level and evaluator class are derived **only** via `ai_stack.semantic_planner_effect_surface.support_level_for_module` and `resolve_dramatic_effect_evaluator` (no duplicate module classification in inspector code). The workbench UI renders structured planner sections, separates primary canonical gate posture from secondary legacy material, defaults Mermaid to semantic flow, and keeps full JSON under secondary disclosure. **No runtime authority, validation, or commit semantics were changed.**

## 2. Implemented files and responsibilities

| Area | File | Responsibility |
|------|------|------------------|
| Contract versions | `backend/app/contracts/inspector_turn_projection.py` | Bump all inspector projection schema constants to `*_v2`. |
| Turn projection | `backend/app/services/inspector_turn_projection_service.py` | Canonical gate payload; semantic + graph execution flows; planner `support_posture`; provenance expansion; `_projectable_state` merges planner fields from diagnostics / `graph.planner_state_projection`. |
| Auxiliary projections | `backend/app/services/inspector_projection_service.py` | Timeline/comparison/coverage/provenance-raw extended fields; candidate matrix when `graph.dramatic_review.multi_pressure_candidates` exists; visible-output fingerprint comparison; support/evaluator metadata on comparison. |
| Workbench template | `administration-tool/templates/manage/inspector_workbench.html` | Structured planner host; Mermaid mode selector; gate posture + legacy `<details>`; raw JSON secondary. |
| Workbench JS | `administration-tool/static/manage_inspector_workbench.js` | Render-only panels; semantic Mermaid from `semantic_decision_flow` only (no client inference of stage presence); graph execution toggle. |
| Styles | `administration-tool/static/manage.css` | Toolbar, planner cards, legacy block spacing. |
| Backend tests | `backend/tests/test_inspector_turn_projection.py` | v2 schema, canonical gate, semantic flow, coverage keys, provenance fields, comparison dimensions. |
| Admin tests | `administration-tool/tests/test_manage_inspector_suite.py` | DOM mount points for new structure. |
| Changelog | `CHANGELOG.md` | Short parity note under 0.4.1. |

## 3. Backend projection alignment truth

- **`gate_projection.data`**: All keys from `dramatic_effect_gate_outcome` except `_LEGACY_GATE_SUMMARY_KEYS` are passed through at top level; legacy keys are grouped under `legacy_compatibility_summary` when present.
- **`comparison_ready_fields.supported_now`**: Uses canonical gate/posture fields and `semantic_planner_support_level`; removes primary use of `dominant_rejection_category`.
- **Support posture**: `support_level_for_module(str(module_id or ""))` and `type(resolve_dramatic_effect_evaluator(...)).__name__` only.

## 4. Structured planner-panel truth

- UI renders `support_posture`, `SemanticMoveRecord`, `SocialStateRecord`, `ScenePlanRecord`, and `character_mind_records` as cards; raw `planner_state_projection.data` remains in `<details>`.

## 5. Provenance explorer truth

- Turn provenance adds `effect_rationale_codes`, `dramatic_effect_diagnostic_trace`, and `character_mind_provenance_summary` when data exists.
- Provenance-raw endpoint adds rows for rationale, trace, legacy fallback, support level, and evaluator class with explicit `source_ref` to the canonical helpers.

## 6. Semantic Mermaid truth

- Backend `semantic_decision_flow` provides `stages[]` with `id`, `label`, `presence` and sequential `edges`.
- Frontend builds the diagram **only** from that structure; it does not infer presence from missing nested planner JSON.
- **Graph execution** diagram uses `graph_execution_flow.flow_nodes` / `flow_edges` (also duplicated at `decision_trace_projection` top level for compatibility).

## 7. Timeline / coverage / comparison truth

- **Timeline**: Adds move type, scene risk, gate postures, support level, weak-signal flags, rationale codes, trace codes, etc., when present on diagnostics rows.
- **Coverage**: Distributions for fluency risk, plausibility/continuity postures, legacy fallback, weak signal, support level, merged effect/rejection rationale, legacy dominant category (secondary), and `not_supported_gate_rate`.
- **Comparison**: Adds posture deltas, optional `multi_pressure_candidates_to`, SHA-256–based visible-output fingerprints per turn pair, session support/evaluator summary; `candidate_matrix_not_emitted_in_diagnostics` remains in `unsupported_dimensions` when no candidates exist in evidence.

## 8. Non-GoC visibility truth

- `support_posture.support_note` and comparison/timeline `semantic_planner_support_level` state clearly when the module is not full GoC; planner-bound semantic stages use backend `presence: unsupported` when `support_level != full_goc`.

## 9. Exact test commands run

From repository root (`WorldOfShadows`):

```text
python -m pytest backend/tests/test_inspector_turn_projection.py -q --tb=short
```

```text
cd administration-tool
python -m pytest tests/test_manage_inspector_suite.py tests/test_routes.py -q --tb=short
```

```text
python -m pytest backend/tests/test_goc_admin_semantic_boundary.py -q --tb=short
```

**Outcome:** All commands exited **0**; **15** backend inspector tests passed; **41** administration-tool tests passed in the combined run; **6** `test_goc_admin_semantic_boundary` tests passed.

## 10. Pass/fail outcome for acceptance criteria (task checklist)

| Criterion | Result |
|-----------|--------|
| Structural: backend aligned with canonical contracts | **Pass** |
| Structured planner/gate panels (not JSON-first) | **Pass** |
| Provenance exposes rationale, trace, fallback, support | **Pass** |
| Semantic Mermaid grounded in backend presence | **Pass** |
| Timeline/coverage/comparison expanded | **Pass** |
| Honest non-GoC posture visible | **Pass** |
| No write semantics / second truth surface | **Pass** |
| Regression: read-only POST still 405 | **Pass** (existing tests) |

## 11. Explicit confirmation: no write semantics introduced

All inspector routes remain **GET**-only for projections; POST requests are rejected with **405** as covered by `test_new_inspector_projection_endpoints_are_read_only` and related tests. No new mutation endpoints or admin controls were added.

## 12. Explicit confirmation: no second truth surface introduced

The frontend does **not** classify modules, infer semantic stage presence from absent JSON, or re-score the gate. It renders backend fields and backend-computed flow structures only. Canonical turn assembly still uses `build_operator_canonical_turn_record`; inspector additions are pass-through or deterministic aggregates of evidence already in the bundle.

---

*Report generated to match the implemented tree at closure time.*
