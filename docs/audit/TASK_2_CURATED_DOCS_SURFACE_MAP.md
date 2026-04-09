# Task 2 — Curated Active Documentation Surface Map

## Scope lock

- Surface source: tracked Markdown files from `git ls-files -- "*.md"`.
- Governing baselines: `docs/audit/TASK_1A_REPOSITORY_BASELINE.md`, `docs/audit/TASK_1B_CROSS_STACK_COHESION_BASELINE.md`, `docs/audit/TASK_1B_DOWNSTREAM_CHECKLISTS.md`.
- Excluded from truth authority: gitignored/local helper trees unless a tracked doc depends on them.

## Curated active documentation surface (retain in active audience navigation)

### Dev-facing core

- `README.md` (entrypoint, must be narrowed to role-safe claims).
- `docs/api/README.md`
- `docs/api/REFERENCE.md`
- `docs/architecture/README.md`
- `docs/architecture/runtime_authority_decision.md`
- `docs/CANONICAL_TURN_CONTRACT_GOC.md` (protected X1 handling applies)
- `docs/VERTICAL_SLICE_CONTRACT_GOC.md`
- `docs/development/README.md`
- `docs/development/LocalDevelopment.md`
- `docs/testing/README.md`
- `docs/testing/TEST_EXECUTION_PROFILES.md`
- `docs/testing/QUALITY_GATES.md`
- `docs/testing/RELEASE_GATE_POLICY.md`
- `docs/database/README.md`
- `backend/README.md`
- `world-engine/README.md`
- `frontend/README.md`
- `tools/mcp_server/README.md` (dev tooling docs; not audience-neutral end-user docs)

### Admin-facing core

- `docs/operations/README.md`
- `docs/operations/RUNBOOK.md`
- `docs/operations/ALERTING-CONFIG.md`
- `docs/operations/ANALYTICS.md`
- `docs/security/README.md`
- `docs/security/AUDIT_REPORT.md` (retain with date/validity framing)
- `docs/forum/ModerationWorkflow.md`
- `audits/AUDIT_ADMIN_LOGS_ROLES.md` (candidate relocation into admin governance subtree)
- `audits/AUDIT_ROLES_ACCESS_CONTROL.md` (candidate relocation)
- `audits/VERIFICATION.md` (candidate relocation/demotion depending on claim migration)

### User-facing core

- `docs/features/README.md`
- `docs/features/forum.md`
- `docs/features/RUNTIME_COMMANDS.md` (requires audience split notes to avoid operator-only leakage)

### Contract/interface/governance core

- `docs/GATE_SCORING_POLICY_GOC.md`
- `docs/rag_task3_source_governance.md`
- `docs/rag_task4_readiness_and_trace.md`
- `docs/rag_task4_evaluation_harness.md`
- `docs/rag_retrieval_hardening.md`

## Separated non-curated surfaces (not in audience-facing active map)

### AI execution-control surfaces

- ~~`docs/superpowers/plans/*`~~ / ~~`docs/superpowers/specs/*`~~ — **removed 2026-04-10**; archived under `docs/archive/superpowers-legacy-execution-2026/` (see `SUPERPOWERS_*` ledgers in `docs/archive/documentation-consolidation-2026/`)
- `docs/mcp/*` when content is execution-control/program governance rather than stable user/admin/dev guidance
- `docs/plans/*` (program execution plans)

### Audit/program-history surfaces

- `docs/audit/gate_*_baseline.md` (except active claim-audit references and X1 protected registry behavior)
- `docs/reports/*`
- `docs/research_mvp_*`
- `docs/ROADMAP_MVP_*`
- `docs/PHASE0_FREEZE_CLOSURE_NOTE_GOC.md`

### External distribution mirrors

- `outgoing/**` package docs
- `docs/g9_evaluator_b_external_package/**` mirror docs (retained but not mixed into general audience map)

## Curated-surface exclusion rule

A doc must be excluded from curated audience-facing navigation if both are true:

1. Its primary function is process execution/history/control; and
2. Active operational/contract truth can be migrated into curated retained docs.

## Notes on coverage

- This map is a control artifact for Task 2 execution and does not claim all rewrites/moves are complete.
- Long-tail tracked markdown under `writers-room/**` and content authoring markdown remains classified as domain assets, not general audience docs, unless explicitly elevated by product/user docs policy.
