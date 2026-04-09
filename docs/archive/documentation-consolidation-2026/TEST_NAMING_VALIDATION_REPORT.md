# Test naming validation report (2026 consolidation)

## Summary of changes (this pass + carried-forward renames)

### Files renamed (carried forward from program start)

- Backend Area 2 style filenames → `test_runtime_*` / `test_improvement_model_routing_*` (see `TEST_RENAME_AND_NORMALIZATION_MAP.md`).
- `tests/goc_gates/` → `tests/experience_scoring_cli/`.
- AI stack `test_goc_phase{1,2,3,4,5}_*.py` → descriptive `test_goc_*` basenames (see map).
- MCP server `test_mcp_m{1,2}_gates.py` → descriptive names (see map).

### Internal test names normalized (this pass)

- `test_runtime_validation_commands_orchestration.py`: all `test_g_t4_*` → `test_full_validation_*`.
- `test_runtime_operator_comparison_cross_surface.py`: all `test_g_t3_*` → `test_operator_comparison_*`.
- `test_cross_surface_operator_audit_contract.py`: `test_g_conv_08_*` → descriptive operator-truth names.
- `test_runtime_model_ranking_synthesis_contracts.py`: all `test_g_canon_rank_*` → `test_runtime_ranking_*`.
- `test_goc_multi_turn_experience_quality.py`: S5 anchor `test_phase3_run_c_*` → `test_experience_multiturn_primary_failure_fallback_and_degraded_explained`.

### Splits / merges

- **No split** performed in this pass.
- **Merge**: historical dual workstream suites are represented as two readable owning modules (operational vs startup) plus composed proofs; no separate merge commit in this slice.

### Documentation / CI references

Updated so machine-checked strings match code:

- `docs/testing-setup.md` (dual + Task 4 command lines, G10 trio, G9 bundle paths, experience CLI path).
- `docs/archive/architecture-legacy/area2_dual_workstream_closure_report.md`
- `docs/archive/architecture-legacy/area2_validation_hardening_closure_report.md`
- `docs/archive/architecture-legacy/area2_task4_closure_gates.md`
- `docs/archive/architecture-legacy/area2_runtime_ranking_closure_report.md`
- `docs/technical/ai/llm-slm-role-stratification.md`, `docs/technical/architecture/ai_story_contract.md`
- `docs/audit/gate_G9_experience_acceptance_baseline.md`
- `.github/workflows/backend-tests.yml`
- `scripts/g9_level_a_evidence_capture.py`
- `outgoing/**/scenario_goc_roadmap_s5_primary_failure_fallback.json` (pytest anchor metadata)

## Targeted validation commands (executed)

From `backend/` (Windows-friendly):

```bash
python -m pytest tests/runtime/test_runtime_validation_commands_orchestration.py::test_full_validation_documented_pytest_command_matches_code tests/runtime/test_runtime_validation_commands_orchestration.py::test_full_validation_docs_reference_task4_gates_and_commands tests/runtime/test_runtime_routing_registry_composed_proofs.py::test_registry_routing_documentation_lists_task2_gate_ids tests/runtime/test_runtime_operator_comparison_cross_surface.py::test_operator_comparison_docs_list_task3_gate_ids tests/runtime/test_runtime_model_ranking_synthesis_contracts.py::test_runtime_ranking_documentation_lists_canonical_gate_ids -q --tb=short --no-cov
```

**Result:** 5 passed (local run, 2026-04-10).

Repository root (with `PYTHONPATH` = repo root):

```bash
python -m pytest ai_stack/tests/test_goc_multi_turn_experience_quality.py::test_experience_multiturn_primary_failure_fallback_and_degraded_explained --collect-only -q
```

**Result:** 1 test collected.

### Canonical string parity (code vs `docs/testing-setup.md`)

```bash
cd backend
python -c "from pathlib import Path; from app.runtime.area2_validation_commands import area2_task4_full_closure_pytest_invocation, area2_dual_closure_pytest_invocation; inv=area2_task4_full_closure_pytest_invocation(); d=area2_dual_closure_pytest_invocation(); t=Path('../docs/testing-setup.md').read_text(encoding='utf-8'); assert inv in t and d in t"
```

**Result:** assertion OK.

## Naming residue checks (machine)

Run from repository root. These are **screening** greps; failures require human classification (domain term vs historical encoding).

### 1) Legacy Area 2 test **filenames** (should be empty)

```bash
rg -n "test_area2_" backend/tests --glob "*.py"
```

### 2) Historical “closure gates” test **filenames** (should be empty)

```bash
rg -n "closure_gates" backend/tests --glob "*.py"
```

### 3) Task / workstream tokens in **test filenames** (should be empty)

```bash
rg -n "task[0-9]|workstream" backend/tests --glob "*test_*.py" -i
```

### 4) Phase-prefixed **test function** names under `ai_stack/tests` (expected: residual until deferred pass)

```bash
rg -n "def test_phase[0-9]" ai_stack/tests --glob "*.py"
```

**Justified exceptions / deferrals:**

- Remaining `test_phase4_*` and `test_phase5_*` in `test_goc_reliability_longrun_operator_readiness.py` and `test_goc_mvp_breadth_playability_regression.py`: **deferred** to avoid a wide audit-doc churn in one slice; tracked in `TEST_NAMING_READABILITY_INVENTORY.md`.
- `test_phase3_*` siblings in `test_goc_multi_turn_experience_quality.py` (other than the renamed S5 anchor): **deferred** for the same reason.

### 5) Domain vocabulary that **matches** grep but is not historical encoding

The following are **expected** hits and not automatically violations:

- JSON / operator audit field names: `area2_operator_truth`, `area2_validation_commands`, markdown filenames like `area2_task4_closure_gates.md` referenced in tests.
- Docstrings that cite **traceability** gate labels such as `G-T4-01` where the **function name** is already descriptive.

Document intentional hits when triaging grep output.

## Blockers

None. Deferred items are **scope choices**, not unknown behavior.

## Stale artifact warning

Built static site copies under `site/` may still show old pytest nodes until MkDocs is regenerated; **authoritative** sources are the tracked `docs/*.md` and test files.
