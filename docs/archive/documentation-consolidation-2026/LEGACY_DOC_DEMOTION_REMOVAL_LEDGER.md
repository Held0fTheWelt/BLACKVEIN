# Legacy documentation demotion / removal ledger

| Old path | Disposition | Rationale |
|----------|-------------|-----------|
| `docs/architecture/*.md` (except `README.md`) | **Archived** under `docs/archive/architecture-legacy/` or **moved** to `docs/technical/**` | Active technical surface consolidated under `docs/technical/`; `docs/architecture/README.md` is redirect-only |
| `docs/rag_task*.md`, `docs/rag_retrieval_*.md` (root) | **Archived** to `docs/archive/rag-task-legacy/` | Single canonical `docs/technical/ai/RAG.md` on active surface |
| `docs/GoC_Gate_Baseline_Audit_Plan.md` | **Archived** to `docs/archive/documentation-consolidation-2026/` | Large program plan; not primary human onboarding |
| `docs/start-here/world-of-shadows-overview.md` | **Renamed** → `what-is-world-of-shadows.md` | Mandatory filename alignment |
| `docs/start-here/god-of-carnage-experience-overview.md` | **Renamed** → `god-of-carnage-as-an-experience.md` | Mandatory filename alignment |
| `docs/user/getting-started-player.md` | **Renamed** → `getting-started.md` | Mandatory filename alignment |
| `docs/dev/contributing-and-repo-layout.md` | **Renamed** → `contributing.md` | Mandatory filename alignment |
| `docs/dev/local-development.md` | **Renamed** → `local-development-and-test-workflow.md` | Mandatory filename alignment |
| `docs/CANONICAL_TURN_CONTRACT_GOC.md` | **Retained** at repo `docs/` root | Narrow normative exception |
| `docs/VERTICAL_SLICE_CONTRACT_GOC.md`, `docs/GATE_SCORING_POLICY_GOC.md`, `docs/ROADMAP_MVP_*.md` | **Retained** at `docs/` root | MVP / slice exception (not generalized to other task docs) |
| `docs/audit/TASK_*` | **Retained** in place | Historical evidence; explicitly excluded from audience onboarding in `INDEX.md` |
