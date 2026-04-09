# Area 2 — Operator comparison and readability closure report (Task 3)

**Status: PASS** — Area 2 Closure Task 3 (operator comparison and readability) is closed when this document matches the enforced tests listed below.

## Binding interpretation (Task 3 comparison / readability)

- **Operator-grade comparison:** Runtime, Writers-Room, and Improvement share `operator_audit.area2_operator_truth.compact_operator_comparison` with the same mandatory key set and `grammar_version` **`area2_operator_comparison_v1`**. Bounded surfaces use explicit `null` values in `runtime_path_summary` and `legacy_roll_up` where Runtime-only data does not apply — never implicit omission of grammar keys.
- **Compact truth:** The `compact_operator_comparison` object is the primary cross-surface comparison payload. It is built only from caller-supplied traces, orchestration summaries, registry counts, and bootstrap flags (no invented operator facts).
- **Directly readable:** Surface, authority, startup profile, operational posture, `route_status`, unified `selected_vs_executed`, `policy_execution_comparison.posture`, `no_eligible_operator_meaning`, `primary_operational_concern`, `stage_outcome_briefs`, and `runtime_path_summary` are visible without walking `audit_timeline` or raw `routing_evidence`.
- **Deep evidence:** `audit_timeline`, full traces, and `routing_evidence` remain for debugging; they are secondary for first-pass reading.
- **Policy vs execution:** `policy_execution_comparison` summarizes existing `policy_execution_aligned` and `execution_deviation` only.
- **Routing semantics:** **`route_model` semantics and precedence, `StoryAIAdapter`, guard/commit/reject authority, and authoritative runtime mutation rules are unchanged.** This task adds structured derivation and documentation only.

## Gate results (G-T3-01 … G-T3-08)

| Gate | Result | Proof |
|------|--------|--------|
| **G-T3-01** Compact truth model | PASS | `test_g_t3_01_compact_truth_model_gate` — mandatory `compact_operator_comparison` keys + `grammar_version` on Runtime, Writers-Room, Improvement |
| **G-T3-02** Direct readability | PASS | `test_g_t3_02_direct_readability_gate` — story from `compact_operator_comparison` + `audit_summary` only |
| **G-T3-03** Policy/execution comparison | PASS | `test_g_t3_03_policy_execution_comparison_gate` — posture from alignment / deviation flags |
| **G-T3-04** Cross-surface comparison | PASS | `test_g_t3_04_cross_surface_comparison_gate` — same grammar; bounded explicit null `runtime_path_summary` |
| **G-T3-05** Primary concern visibility | PASS | `test_g_t3_05_primary_concern_visibility_gate` — matches `audit_summary.primary_concern_code` |
| **G-T3-06** No deep-reconstruction dependency | PASS | `test_g_t3_06_no_deep_reconstruction_dependency_gate` — first-pass view + deep blocks still present |
| **G-T3-07** Documentation truth | PASS | `test_g_t3_07_documentation_truth_gate` — this file, gate doc, stratification, contract reference G-T3 and `compact_operator_comparison` |
| **G-T3-08** Authority/semantic safety | PASS | `test_g_t3_08_authority_semantic_safety_gate` — no direct `route_model` import/call in `area2_operator_truth.py` |

## Compact truth model summary

- **Module:** [`backend/app/runtime/area2_operator_truth.py`](../../backend/app/runtime/area2_operator_truth.py)
- **Grammar:** `AREA2_OPERATOR_COMPARISON_GRAMMAR_VERSION` = `area2_operator_comparison_v1`
- **Mandatory object:** `area2_operator_truth.compact_operator_comparison` with keys: `grammar_version`, `surface`, `authority_source`, `startup_profile`, `operational_state`, `route_status`, `primary_operational_concern`, `no_eligible_operator_meaning`, `policy_execution_comparison`, `selected_vs_executed` (always `per_stage` + `legacy_roll_up`), `stage_outcome_briefs`, `runtime_path_summary` (ranking keys; explicit nulls off Runtime)

## Policy/execution comparison summary

- **`policy_execution_comparison.posture`:** `aligned` | `misaligned` | `mixed` | `unknown` | `not_applicable`, derived deterministically from per-stage `policy_execution_aligned` and non-empty `execution_deviation` in existing `routing_evidence`.
- **`per_stage`:** `stage_key`, `policy_execution_aligned`, `has_execution_deviation` (boolean).

## Cross-surface comparison summary

- **Same grammar** on `runtime`, `writers_room`, and `improvement`.
- **Explicit asymmetry:** `runtime_path_summary` carries orchestration ranking fields on Runtime; on bounded HTTP surfaces every key is present with value `null`.

## Primary-concern visibility summary

- **`compact_operator_comparison.primary_operational_concern`** mirrors `area2_operator_truth.primary_operational_concern` and **`audit_summary.primary_concern_code`** (same derivation as `operator_audit`).

## Tests run and results

```text
python -m pytest tests/runtime/test_area2_task3_closure_gates.py
python -m pytest tests/runtime/test_cross_surface_operator_audit_contract.py
python -m pytest tests/runtime/test_area2_convergence_gates.py
python -m pytest tests/runtime/test_area2_final_closure_gates.py
python -m pytest tests/runtime/test_area2_task2_closure_gates.py
```

(Execute from `backend/`; all must pass for closure.)

## Changed files

- `backend/app/runtime/area2_operator_truth.py` — `compact_operator_comparison` builder, grammar constants, unified selection rollup for comparison
- `backend/tests/runtime/test_area2_convergence_gates.py` — `AREA2_TRUTH_KEYS` + `assert_area2_truth_shape` extended
- `backend/tests/runtime/test_area2_task3_closure_gates.py` — G-T3-01 … G-T3-08
- `docs/architecture/area2_task3_closure_gates.md` — gate table + binding interpretation
- `docs/architecture/area2_operator_comparison_closure_report.md` — this report
- `docs/architecture/llm_slm_role_stratification.md` — Task 3 operator comparison reference
- `docs/architecture/ai_story_contract.md` — Task 3 operator comparison reference

## Residual risks

- **Orchestration variance:** If a future Runtime path omits ranking keys from `runtime_orchestration_summary`, `runtime_path_summary` may be all nulls while keys remain present; operators should treat null slots as “no ranking signal on this run,” not as a grammar bug.
- **Third-party consumers:** Any client that assumed `area2_operator_truth` had a fixed key set before `compact_operator_comparison` must accept the new mandatory key (additive for JSON parsers that allow unknown keys was already false if they validated strictly).

## Explicit statement

**`route_model` routing semantics and precedence, `StoryAIAdapter`, guard/commit/reject semantics, and authoritative runtime mutation rules were not changed by this closure task.**
