# Task 2 — Document Removal and Demotion Candidates

This list applies operational criteria from Task 2:

- omission test
- durable-truth duplication/migration test
- organizational-logic test

A document is a removal/demotion candidate from curated active surface when at least 2/3 criteria pass.

## Candidate list

| Path | Omission test | Durable-truth duplication test | Organizational-logic test | Candidate decision | Notes |
|---|---|---|---|---|---|
| `docs/superpowers/plans/*` | pass | pass (after migration) | pass | **archived** to `docs/archive/superpowers-legacy-execution-2026/plans/` (2026-04-10) | execution-control timeline docs |
| `docs/superpowers/specs/*` | pass | pass (after migration) | pass | **archived** to `docs/archive/superpowers-legacy-execution-2026/specs/` (2026-04-10) | execution-control design history |
| `docs/plans/*` | conditional pass | pass (after migration) | pass | demote unless active operator contract exists | keep only currently active operational plan pages |
| `docs/reports/*` | pass for most files | pass (after migration) | pass | demote/archive | retain only report pages with unique active runbook truth |
| `docs/MVPs/MVP_Research_Gate_And_Implementation/research_mvp_gate_closure.md` | pass | pass | pass | demote/archive | closure narrative |
| `docs/MVPs/MVP_Research_Gate_And_Implementation/research_mvp_implementation_summary.md` | pass | pass | pass | demote/archive | implementation progression summary |
| `docs/MVPs/MVP_VSL_And_GoC_Contracts/PHASE0_FREEZE_CLOSURE_NOTE_GOC.md` | pass | pass | pass | demote/archive | historical phase closure |
| `docs/reports/PATCH_NOTES_FLASK_PLAY_INTEGRATION.md` | pass | pass | pass | demote/archive | historical process note (relocated from root) |
| `docs/MVPs/MVP_Engine_And_UI/ROADMAP_MVP_ENGINE_AND_UI.md` | conditional pass | pass (after migration) | pass | demote with extracted durable policy | roadmap/process heavy |
| `docs/MVPs/MVP_MCP/ROADMAP_MVP_MCP.md` | conditional pass | pass (after migration) | pass | demote with extracted durable policy | roadmap/process heavy |
| `docs/MVPs/MVP_Repository_Surface_Truth_And_Structure_Cleanup/ROADMAP_MVP_REPOSITORY_SURFACE_TRUTH_AND_STRUCTURE_CLEANUP.md` | conditional pass | pass (after migration) | pass | demote after Task 2 extraction | planning control history |
| `docs/MVPs/MVP_Research_And_Canon_Improvement_System/ROADMAP_MVP_RESEARCH_AND_CANON_IMPROVEMENT_SYSTEM.md` | conditional pass | pass (after migration) | pass | demote/archive after extraction | process-heavy |
| `docs/MVPs/MVP_Semantic_Dramatic_Planner/ROADMAP_MVP_SEMANTIC_DRAMATIC_PLANNER.md` | conditional pass | pass (after migration) | pass | demote/archive after extraction | process-heavy |

## Non-candidates (retain in curated active docs)

- `docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md` (protected X1, still claim-audited).
- `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md`.
- `docs/architecture/runtime_authority_decision.md`.
- `docs/api/REFERENCE.md`.
- `docs/operations/RUNBOOK.md`.
- `docs/security/README.md`.

## Ambiguity handling

If a row is ambiguous between remove and demote:

1. classify all material claims;
2. execute durable-truth migration mapping;
3. verify every T0 claim destination;
4. decide remove vs demote with recorded rationale.
