# Durable truth migration ledger

Consolidation execution (2026). Maps **legacy sources** to **canonical destinations** where operational truth was merged or superseded.

| Source (legacy path) | Destination (canonical path) | Migration summary |
|----------------------|------------------------------|-------------------|
| `docs/architecture/runtime_authority_decision.md` | `docs/technical/runtime/runtime-authority-and-state-flow.md` | Decision text folded into consolidated runtime authority page; original archived |
| `docs/architecture/ServerArchitecture.md` | `docs/technical/architecture/service-boundaries.md` | Service ownership and compatibility rules summarized |
| `docs/architecture/ai_stack_in_world_of_shadows.md` | `docs/technical/ai/ai-stack-overview.md` | Stale milestone list superseded by current-stack overview |
| `docs/architecture/rag_in_world_of_shadows.md` | `docs/technical/ai/RAG.md` | Storage, ingestion, hybrid path, profiles |
| `docs/rag_task3_source_governance.md` | `docs/technical/ai/RAG.md` § Source governance | Governance lanes, policy version, profile gates |
| `docs/rag_task4_*.md`, `docs/rag_retrieval_*.md` | `docs/technical/ai/RAG.md` + archive copies | Evaluation/harness detail retained in archive; active surface summarizes behavior |
| `docs/architecture/mcp_in_world_of_shadows.md` | `docs/technical/integration/MCP.md` | Capability modes, audit, wiring |
| `docs/architecture/langgraph_in_world_of_shadows.md` | `docs/technical/integration/LangGraph.md` | Graph nodes, authority boundary, diagnostics |
| `docs/architecture/langchain_integration_in_world_of_shadows.md` | `docs/technical/integration/LangChain.md` | Runtime + Writers’ Room LC usage |
| `docs/architecture/writers_room_on_unified_stack.md` | `docs/technical/content/writers-room-and-publishing-flow.md` | Stages, HITL, shared stack |
| `docs/architecture/observability_and_governance_in_world_of_shadows.md` | `docs/technical/operations/observability-and-governance.md` | Renamed in place (git mv) |
| `docs/dev/architecture/runtime-authority-and-session-lifecycle.md` (body) | `docs/technical/runtime/runtime-authority-and-state-flow.md` | Long-form moved; dev file is seam stub |
| `docs/dev/architecture/ai-stack-rag-langgraph-and-goc-seams.md` (body) | `docs/technical/ai/*`, `integration/*` | Long-form moved; dev file is seam stub |
| `docs/dev/testing/test-pyramid-and-suite-map.md` (truth) | `docs/technical/reference/test-strategy-and-suite-layout.md` | Technical test strategy canonical; dev file retained for contributors |

Archived **without** merging narrative into active docs (evidence-only): `docs/archive/architecture-legacy/area2_*.md`, `task4_*closure*`, inspector suite closure docs — still indexed for gate archaeology.

See [DURABLE_TRUTH_MIGRATION_VERIFICATION_TABLE.md](./DURABLE_TRUTH_MIGRATION_VERIFICATION_TABLE.md) for per-claim verification.
