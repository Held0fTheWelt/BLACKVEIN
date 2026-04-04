# D2-next Gate Report — Improvement mutation / evaluation / recommendation suite maturity

Date: 2026-04-04

## 1. Scope completed

- Added **`comparison_package`**: tabular dimension rows (candidate vs baseline values and deltas) plus semantic rate deltas for review-oriented comparison.
- Added **`recommendation_rationale`**: explicit **drivers** tied to sandbox metrics, comparison deltas, transcript-tool repetition signals, retrieval hit paths, and a final **`retrieval_context_digest`** fingerprint derived from sorted source paths plus context text (test-proven materiality).
- Added **`evidence_strength_map`**: declarative categorization of evidence classes (metrics, baseline control, retrieval, transcript tool readback, governance bundle) without overstating numeric “confidence”.
- Extended **`create_variant`** with optional **`parent_variant_id`** / **`lineage_depth`** and persisted **`mutation_metadata`** for richer candidate lineage.
- Wired the experiment HTTP path to **rebuild** rationale after transcript suffix logic and to persist digest + driver categories on **`evidence_bundle`**.

## 2. Files changed

- `backend/app/services/improvement_service.py`
- `backend/app/api/v1/improvement_routes.py`
- `backend/tests/test_improvement_routes.py`
- `docs/reports/ai_stack_gates/D2_NEXT_GATE_REPORT.md`

## 3. What was deepened versus what already existed

- **Already existed:** Sandbox experiment with parallel baseline transcript, evaluation metrics and deltas, recommendation summary with rule thresholds, `wos.context_pack.build`, `wos.transcript.read`, `wos.review_bundle.build`, persisted `evidence_bundle` snapshots, workflow stages.
- **Deepened:** Structured comparison and **evidence-linked rationale** that a human reviewer can audit; retrieval shape binds to rationale via fingerprint; optional multi-hop variant lineage metadata.

## 4. Workflow stages that became stronger

- No new stage ids were required; **`evaluation_and_recommendation_draft`** output is now accompanied by artifacts that make the evaluation step **review-meaningful** (`comparison_package`, `recommendation_rationale`, `evidence_strength_map`).
- **`retrieval_improvement_context`** now has a **downstream fingerprint** on the stored package, not only a list of paths.

## 5. How comparison / evidence / recommendation quality improved

- **Comparison:** Dimensions are explicit per metric with candidate, baseline, and delta in one package (plus semantic deltas).
- **Evidence:** `evidence_bundle` carries `retrieval_context_fingerprint_sha256_16` and `recommendation_driver_categories` for quick governance scanning.
- **Recommendation:** Summary remains threshold-driven, but **drivers** state *why* the package leans toward revise vs promote, including transcript-tool and retrieval context when present.

## 6. Where retrieval / tool usage became more material

- **Retrieval:** Changing returned source paths and `context_text` changes the digest fingerprint (`finalize_recommendation_rationale_with_retrieval_digest`); covered by HTTP monkeypatch test across two path sets.
- **Transcript tool:** Repetition turn count continues to force the revise suffix; it now also appears as an explicit rationale driver when applicable.

## 7. What remains intentionally lightweight

- Sandbox execution is still a **simulated** transcript evaluator, not a full production story graph.
- Recommendation outcomes are still **rule-gated**, not learned ranking or autonomous promotion.
- No automatic merge to published modules.

## 8. Tests added / updated

- Extended main experiment test for `comparison_package`, `recommendation_rationale` drivers (including `retrieval_context_digest`), and `evidence_strength_map`.
- Extended retrieval materiality test to assert **different fingerprints** for different retrieval paths.
- Added `test_variant_creation_with_parent_lineage`.
- Added service-level `test_evaluate_experiment_builds_comparison_package_and_rationale` for builders and digest sensitivity to `context_text`.

## 9. Exact test commands run

```text
cd backend
python -m pytest tests/test_improvement_routes.py -v --tb=short
```

Result: **12 passed**, exit code **0** (Windows, Python 3.13.12). Project pytest config still attaches coverage by default (`backend/pyproject.toml`).

## 10. Verdict

**Pass**

## 11. Reason for verdict

- Improvement packages are **more actionable for governance** than before: comparison and rationale are structured, and retrieval/tool influence is **test-proven** on digest and drivers.
- The report does not claim autonomous maturity or production promotion authority.

## 12. Remaining risk

- Driver lists can grow with future metrics; consumers should treat them as **explanatory**, not as a stability contract without versioning.
- Empty retrieval still produces a digest over empty path sets—honest but low informational value.
