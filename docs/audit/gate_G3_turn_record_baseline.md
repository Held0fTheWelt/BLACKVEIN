# Gate G3 Baseline: Canonical Dramatic Turn Record

**Repository-truth note (2026-04-10):** The canonical pytest target for G3-style runtime graph seams was renamed from `test_goc_phase1_runtime_gate.py` to `test_goc_runtime_graph_seams_and_diagnostics.py`. Archived transcripts under `tests/reports/evidence/all_gates_closure_20260409/` still reflect the historical filename.

## Gate

- Gate name: G3 Canonical Dramatic Turn Record
- Gate class: structural
- Audit subject: single canonical per-turn record, required sections/fields, and projection discipline

## Repository Inspection Targets

- `docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md`
- `ai_stack/goc_turn_seams.py`
- `ai_stack/runtime_turn_contracts.py`
- `ai_stack/langgraph_runtime.py`
- `backend/app/services/ai_stack_evidence_service.py`
- `ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py`

## Required Evidence

- canonical turn-record contract
- emitted runtime records containing required groups and fields
- proof compact/expanded views are projections from one canonical source
- tests over emitted record semantics

## Audit Methods Used In This Baseline

- contract inspection
- runtime packaging/projection static inspection
- static test-surface review (no runtime execution in this block)

## Command Strategy

| command | status | basis | promotion requirement |
| --- | --- | --- | --- |
| `python -m pytest ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py -q --tb=short` | `repo-verified` | Canonical runtime turn-record / graph-seam path in `ai_stack/tests/` (renamed module). | Archived: `tests/reports/evidence/all_gates_closure_20260409/g3_turn_record_ai_stack.txt` (historical filename in transcript) |
| `cd backend && python -m pytest tests/runtime/test_cross_surface_operator_audit_contract.py -q --tb=short --no-cov` | `repo-verified` | Cross-surface operator-audit contract continuity for emitted turn records. | Archived: `tests/reports/evidence/all_gates_closure_20260409/g3_cross_surface_contract_backend.txt` |

## Baseline Findings

1. A canonical turn-record contract document exists and is explicitly referenced by runtime seam code.
2. Runtime state and packaging in `ai_stack/langgraph_runtime.py` include session/turn/routing/retrieval/validation/graph diagnostics fields.
3. `ai_stack/goc_turn_seams.py` provides operator-canonical projection helpers and references canonical contract sections.
4. `ai_stack/runtime_turn_contracts.py` defines stable runtime constants and the executed test surfaces confirm canonical turn record coverage for the audited paths.
5. Runtime trace-backed checks were executed in this closure run; no field-group contradiction was found on canonical paths.

## Status Baseline

- structural_status: `green`
- closure_level_status: `level_a_capable`

Rationale: canonical contract/projection architecture is present and canonical runtime + cross-surface contract paths passed with archived evidence.

## Evidence Quality

- evidence_quality: `high`
- justification: direct contract/implementation evidence plus executed turn-record test transcripts in `all_gates_closure_20260409`.

## Execution Risks Carried Forward

- Continue enforcing this two-command G3 verification pair for future turn-record schema changes.
