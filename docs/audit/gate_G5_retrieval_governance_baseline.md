# Gate G5 Baseline: Retrieval Governance

**Repository-truth note (2026-04-10):** Long-run / reliability coverage moved from `test_goc_phase4_reliability_breadth_operator.py` to `test_goc_reliability_longrun_operator_readiness.py`.

## Gate

- Gate name: G5 Retrieval Governance
- Gate class: structural
- Audit subject: authored-vs-derived separation, governance lanes, and runtime retrieval visibility

## Repository Inspection Targets

- `ai_stack/rag.py`
- `docs/rag_retrieval_hardening.md`
- `docs/rag_retrieval_subsystem_closure.md`
- `docs/rag_task3_source_governance.md`
- `docs/rag_task4_evaluation_harness.md`
- `ai_stack/tests/test_rag.py`
- `ai_stack/tests/retrieval_eval_scenarios.py`
- `ai_stack/tests/test_goc_reliability_longrun_operator_readiness.py`

## Required Evidence

- explicit authored truth references
- explicit derived retrieval substrate references
- retrieval source-class metadata
- lane and visibility governance metadata
- runtime turn retrieval traces

## Audit Methods Used In This Baseline

- retrieval governance contract inspection
- lane/visibility static inspection
- static test surface review (no runtime execution in this block)

## Command Strategy

| command | status | basis | promotion requirement |
| --- | --- | --- | --- |
| `python -m pytest ai_stack/tests/test_rag.py ai_stack/tests/test_retrieval_governance_summary.py ai_stack/tests/test_goc_reliability_longrun_operator_readiness.py ai_stack/tests/test_goc_retrieval_heavy_scenario.py -q --tb=short` | `repo-verified` | Canonical retrieval governance/reliability/roadmap retrieval-heavy path (renamed reliability module). | Archived: `tests/reports/evidence/all_gates_closure_20260409/g5_retrieval_ai_stack.txt` |
| `cd backend && python -m pytest tests/test_goc_evidence_retrieval_governance.py -q --tb=short --no-cov` | `repo-verified` | Backend retrieval-governance evidence contract path. | Archived: `tests/reports/evidence/all_gates_closure_20260409/g5_retrieval_backend.txt` |

## Baseline Findings

1. `ai_stack/rag.py` defines explicit governance lane (`SourceEvidenceLane`) and visibility class (`SourceVisibilityClass`) models.
2. Retrieval pipeline exports source lane/visibility metadata into retrieval hits and trace summaries.
3. Policy/governance versioning (`RETRIEVAL_POLICY_VERSION`) and route posture (`retrieval_route`) are explicit in code.
4. Runtime turn-level retrieval-governance visibility was verified on canonical test paths and archived in the closure evidence bundle.

## Status Baseline

- structural_status: `green`
- closure_level_status: `level_a_capable`

Rationale: retrieval governance structures are present and canonical runtime/contract tests passed with archived transcripts.

## Evidence Quality

- evidence_quality: `high`
- justification: direct code/doc evidence plus executed canonical retrieval governance test transcripts.

## Execution Risks Carried Forward

- Keep this G5 command pair as canonical regression requirement for retrieval governance changes.
