# Red / Yellow Remediation List (Residual)

This file now tracks only **remaining** blockers after the all-gates closure rerun bundle `tests/reports/evidence/all_gates_closure_20260409/`.

## Residual blockers

| ID | Source gate(s) | Blocker type | Residual blocker |
|----|----------------|--------------|------------------|
| R1 | G9B / global Level B | external/evidential | Level B evaluator independence remains insufficient (`failed_insufficient_independence`). Dual matrices + deltas are present, but evidentiary independence bar (process/authorship/score-generation separation) is not met. |
| R2 | Cross-cutting parity | environment parity caution | Closure reruns were on Python 3.13.12 while CI merge bar is Python 3.10 (`docs/testing-setup.md`). This is not a blocker for current repo-local closure truth, but should be rerun on 3.10 when strict CI-equivalence is required. |

## Cleared repo-local backlog

All previously listed repo-local red/yellow remediation items for G1–G8 and G10 were executed and resolved in this task via canonical reruns and evidence alignment:

- semantic/parity paths (G1),
- routing/policy/observation paths (G2),
- turn-record and cross-surface contract paths (G3),
- scene-direction matrix/scenario paths (G4),
- retrieval governance paths (G5),
- admin governance/security/semantic-boundary paths (G6),
- writers-room and improvement operating paths (G7/G8),
- G10 backend integrative trio revalidation.
