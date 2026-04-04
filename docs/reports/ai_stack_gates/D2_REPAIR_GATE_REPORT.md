# D2 Repair Gate Report — Improvement Mutation and Evaluation Loop

Date: 2026-04-04

## 1. Scope completed

- Deepened variant model to include concrete mutation plans.
- Added baseline transcript execution alongside candidate sandbox execution.
- Added baseline-vs-candidate comparison deltas to evaluation output.
- Added evidence bundle payload in recommendation packages with lineage and artifact references.
- Updated route-level tests to verify lineage, comparison, and evidence-backed recommendation outputs.

## 2. Files changed

- `backend/app/services/improvement_service.py`
- `backend/tests/test_improvement_routes.py`
- `docs/architecture/improvement_loop_in_world_of_shadows.md`
- `docs/reports/ai_stack_gates/D2_REPAIR_GATE_REPORT.md`

## 3. What is truly wired

- Candidate creation now stores mutation intent (`mutation_plan`) and lineage depth.
- Sandbox execution now records both candidate transcript and baseline transcript in the same experiment payload.
- Evaluation computes:
  - candidate metrics,
  - baseline metrics,
  - explicit deltas.
- Recommendation package now includes:
  - lineage context,
  - mutation plan,
  - comparison evidence bundle.
- Improvement route still integrates capability retrieval/tool usage and returns capability audit records.

## 4. What remains incomplete

- Simulation remains deterministic and local; no external runtime sandbox cluster.
- Mutation generation is still policy/template-driven, not autonomous code mutation.
- No automated approval/publish path is introduced (intentionally governance-gated).

## 5. Tests added/updated

- Updated `backend/tests/test_improvement_routes.py`:
  - verifies mutation plan and lineage depth are present at variant creation,
  - verifies recommendation payload contains baseline metrics and comparison deltas,
  - verifies evidence bundle mirrors comparison payload and remains reviewable.
- Regression-tested Writers-Room workflow routes.

## 6. Exact test commands run

```powershell
python -m pytest "backend/tests/test_improvement_routes.py"
```

```powershell
python -m pytest "backend/tests/test_writers_room_routes.py"
```

## 7. Pass / Partial / Fail

Pass

## 8. Reason for the verdict

- Variants are now meaningful mutation carriers with explicit lineage data.
- Baseline and candidate are compared with attached evidence, not reported in isolation.
- Controlled sandbox execution and evaluation remain in the active route path and are test-covered.
- Recommendations are now explicitly evidence-backed and governance-reviewable.

## 9. Risks introduced or remaining

- Comparison fidelity is bounded by deterministic simulation realism.
- Mutation plans are structured but still rely on authored guidance templates.
- Local JSON persistence remains sufficient for controlled workflows but not distributed operations.
