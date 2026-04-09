# Area 2 — Task 3 operator comparison closure gates (G-T3)

**Binding interpretation (minimal):**

- **Operator-grade comparison:** Runtime, Writers-Room, and Improvement expose the same `compact_operator_comparison` grammar (`grammar_version` + mandatory key set). Bounded surfaces use explicit `null` substructures where Runtime-only data does not exist — never implicit omission of grammar keys.
- **Compact truth:** `operator_audit.area2_operator_truth.compact_operator_comparison` is the structured, cross-surface comparison object. It is derived only from facts already present in traces, orchestration summaries, and explicit registry/bootstrap counts.
- **Directly readable:** The primary operational story (surface, authority, posture, route health, selected vs executed rollup, policy/execution posture, no-eligible meaning token, primary concern, stage outcome briefs) is visible on that object without walking `audit_timeline` or raw per-stage `routing_evidence`.
- **Deep evidence:** Full `routing_evidence`, `audit_timeline`, and traces remain for debugging; they are not required for first-pass interpretation when compact comparison is present.
- **Policy vs execution comparison:** `policy_execution_comparison.posture` and `per_stage` rows summarize alignment and deviation flags already on `routing_evidence` (no invented mismatch claims).
- **Unacceptable reconstruction burden:** Operators should not need to merge scattered top-level fields or deep traces to answer “what happened” for Area 2 routing posture; `compact_operator_comparison` carries the comparison-oriented rollup.
- **Canonical comparison dimensions:** The eight gates below (model, readability, policy/execution, cross-surface, primary concern, no deep-reconstruction dependency, documentation truth, authority safety).

**Authority (unchanged):** [`backend/app/runtime/area2_routing_authority.py`](../../backend/app/runtime/area2_routing_authority.py). **Grammar version (code):** `AREA2_OPERATOR_COMPARISON_GRAMMAR_VERSION` in [`backend/app/runtime/area2_operator_truth.py`](../../backend/app/runtime/area2_operator_truth.py) (currently `area2_operator_comparison_v1`).

**Related:** G-CONV / G-FINAL gates — [`area2_convergence_gates.md`](./area2_convergence_gates.md), [`area2_final_closure_gates.md`](./area2_final_closure_gates.md). **Closure report:** [`area2_operator_comparison_closure_report.md`](./area2_operator_comparison_closure_report.md).

| Gate ID | Pass condition | Failure meaning | Test proof |
|--------|----------------|-----------------|------------|
| **G-T3-01** | `compact_operator_comparison` exists on Runtime, Writers-Room, and Improvement with the same mandatory key set and `grammar_version == area2_operator_comparison_v1`. | Comparison grammar missing, divergent, or version drift. | `backend/tests/runtime/test_area2_task3_closure_gates.py::test_g_t3_01_compact_truth_model_gate` |
| **G-T3-02** | The main operator story fields are readable from `compact_operator_comparison` plus `audit_summary` alone (surface, route posture labels, policy/execution posture, primary concern path). | Operators still depend on timeline/deep traces for the primary story. | `test_g_t3_02_direct_readability_gate` |
| **G-T3-03** | `policy_execution_comparison.posture` reflects alignment/deviation derived from real `policy_execution_aligned` / `execution_deviation` facts (aligned / misaligned / mixed / unknown / not_applicable). | Policy vs execution not summarized honestly from evidence. | `test_g_t3_03_policy_execution_comparison_gate` |
| **G-T3-04** | Cross-surface payloads share the same comparison grammar; Runtime-only ranking path fields appear under `runtime_path_summary` with explicit nulls on bounded surfaces. | Accidental asymmetry or hidden Runtime-only shape. | `test_g_t3_04_cross_surface_comparison_gate` |
| **G-T3-05** | `primary_operational_concern` in `compact_operator_comparison` matches `audit_summary.primary_concern_code`. | Primary concern not visible or inconsistent in compact view. | `test_g_t3_05_primary_concern_visibility_gate` |
| **G-T3-06** | First-pass interpretation does not require `audit_timeline`, trace lists, or `routing_evidence` reconstruction; deep blocks remain available separately. | Compact path still forces deep reconstruction. | `test_g_t3_06_no_deep_reconstruction_dependency_gate` |
| **G-T3-07** | Architecture docs list every G-T3 id and describe the implemented grammar; closure report matches enforced behavior. | Documentation drift from code truth. | `test_g_t3_07_documentation_truth_gate` |
| **G-T3-08** | `area2_operator_truth.py` does not import or directly call `route_model`; comparison fields remain derivation-only from caller-supplied evidence (coverage validation stays in inventory helpers). | Accidental routing-policy coupling or new authoritative semantics in the truth module. | `test_g_t3_08_authority_semantic_safety_gate` |
