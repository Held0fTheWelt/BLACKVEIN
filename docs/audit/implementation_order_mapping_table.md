# Implementation Order Mapping Table

Source: `docs/GoC_Gate_Baseline_Audit_Plan.md` §6 (mandatory implementation-order mapping), extended with **baseline_structural_snapshot** from this audit’s per-gate reports (`docs/audit/gate_summary_matrix.md`).

| Roadmap step | Primary gates enabled / materially affected | Audit implication | baseline_structural_snapshot (this repo) |
|--------------|---------------------------------------------|-------------------|------------------------------------------|
| 1. Shared semantic contract binding | G1, G4, G7, G8 | Audit G1 before semantic-sensitive operational/evaluative gates | G1 `green` |
| 2. Canonical module package contract | G1, G3, G5, G10 | Validate module load and authored truth anchors early | G1 `green`, G3 `green`, G5 `green` |
| 3. Separate capability / policy / observation | G2, G3, G6, G10 | Confirm structure split before routing/e2e claims | G2 `green`, G3 `green`, G6 `green` |
| 4. Scene-direction subdecision matrix | G4, G3, G10 | Bound scene-direction before scenario quality scoring | G4 `green`, G3 `green` |
| 5. Canonical dramatic turn record emission | G3, G5, G9, G10 | Turn-record evidence for runtime and evaluative gates | G3 `green`, G5 `green`, G9 `green` |
| 6. Retrieval governance lanes + visibility | G5, G3, G9, G10 | Retrieval checks need lane/source visibility in artifacts | G5 `green`, G3 `green`, G9 `green` |
| 7. Admin governance boundaries | G6, G7, G8 | Operational workflows under governance constraints | G6 `green`, G7 `green`, G8 `green` |
| 8. Writers' Room operating contract | G7, G10 | Bounded utility before final end-to-end baseline | G7 `green` |
| 9. Improvement path operating contract | G8, G10 | Typed improvement loop before final aggregation | G8 `green` |
| 10. Experience scenarios + score layer | G9, G9B, G10 | G9 evidence before G9B and final level aggregation | G9 `green` (§6.9 pass on `g9_level_a_fullsix_20260410`), G9B `green` (dual raw matrices + delta; `level_b_attempt_insufficient_independence`; same `audit_run_id`; closure `level_a_capable` at gate slice) |
| 11. Run gates + collect evidence | G1–G10, G9B | Baseline execution/reporting phase | All gates baselined; canonical rerun bundle `all_gates_closure_20260409` confirms G1–G8 green; G10 structural green and `closure_level_status: level_a_capable`; G9/G9B authoritative evidence preserved and revalidated |

## Primary blocker gate (heuristic column)

For remediation prioritization only—not a replacement for full dependency logic:

| Roadmap step | primary_blocker_gate (first gate on critical path still `yellow` / `none` closure) |
|--------------|----------------------------------------------------------------------------------|
| 1 | none (closed) |
| 2 | none (closed) |
| 3 | none (closed) |
| 4 | none (closed) |
| 5 | none (closed) |
| 6 | none (closed) |
| 7 | none (closed) |
| 8 | none (closed) |
| 9 | none (closed) |
| 10 | G9B Level B independence evidence (external/evidential blocker only) |
| 11 | G9B Level B independence evidence; all repo-local structural blockers removed |
