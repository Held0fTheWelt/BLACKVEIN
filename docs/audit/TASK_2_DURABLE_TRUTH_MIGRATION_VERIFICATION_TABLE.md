# Task 2 — Durable-Truth Migration Verification Table

Verification status definitions:

- `pending`: destination exists but migration not fully checked.
- `verified`: destination anchor exists and preserves claim intent.
- `blocked`: unresolved contradiction or missing destination anchor.

| Migration ID | Original document path | Original section/anchor | Original claim locator | Destination document path | Destination section/anchor | Migration status | Verification status | Verified by | Notes |
|---|---|---|---|---|---|---|---|---|---|
| DTM-001 | `docs/ROADMAP_MVP_REPOSITORY_SURFACE_TRUTH_AND_STRUCTURE_CLEANUP.md` | docs-surface governance sections | DTM-001 | `docs/audit/TASK_2_CURATED_DOCS_SURFACE_MAP.md` | scope lock + curated surface | completed | verified | task2-exec | migrated into tracked audit control doc |
| DTM-002 | `docs/ROADMAP_MVP_REPOSITORY_SURFACE_TRUTH_AND_STRUCTURE_CLEANUP.md` | audience taxonomy directives | DTM-002 | `docs/audit/TASK_2_AUDIENCE_TAXONOMY_MAP.md` | target roots + placement rules | completed | verified | task2-exec | audience taxonomy preserved |
| DTM-003 | `docs/ROADMAP_MVP_RESEARCH_AND_CANON_IMPROVEMENT_SYSTEM.md` | claim truth handling | DTM-003 | `docs/audit/TASK_2_CLAIM_AUDIT_TABLE.md` | claim classification/action sections | completed | verified | task2-exec | action classes recorded |
| DTM-004 | `docs/research_mvp_gate_closure.md` | closure durable outcomes | DTM-004 | `docs/audit/TASK_2_CLAIM_AUDIT_TABLE.md` | C003-C006 rows | completed | verified | task2-exec | mapped to evidence-needed rows |
| DTM-005 | `docs/research_mvp_implementation_summary.md` | operational implications | DTM-005 | `docs/audit/TASK_2_FINAL_DOCUMENTATION_CLEANUP_REPORT.md` | execution boundary + outcomes | completed | verified | task2-exec | documented without history-first framing |
| DTM-006 | `docs/reports/PATCH_NOTES_FLASK_PLAY_INTEGRATION.md` | integration assumptions | DTM-006 | `docs/dev/README.md` | implementation-boundary references | completed | verified | task2-exec | relocated from repo root; no longer sole anchor |
| DTM-007 | `docs/reports/AI_STACK_FULL_RELEASE_CLOSURE.md` | release governance lessons | DTM-007 | `docs/admin/README.md` | release governance references | completed | verified | task2-exec | governance references centralized |
| DTM-008 | `docs/reports/TESTING_REPORT.md` | test policy durable points | DTM-008 | `docs/dev/README.md`, `docs/admin/README.md` | testing/release split references | completed | verified | task2-exec | dual-audience split reflected |

## Hard gate statement

Removal or demotion from curated active docs is blocked unless each relevant migration row above is `verified`.
