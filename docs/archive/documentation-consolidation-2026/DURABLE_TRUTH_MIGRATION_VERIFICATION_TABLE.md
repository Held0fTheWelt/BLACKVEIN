# Durable truth migration verification table

| Source document | Source section / locator | Destination document | Destination section | Migration status | Verification status |
|-----------------|--------------------------|------------------------|---------------------|------------------|----------------------|
| `docs/architecture/runtime_authority_decision.md` | § Decision summary + ownership boundaries | `docs/technical/runtime/runtime-authority-and-state-flow.md` | § Decision summary + matrix | Merged | Verified — headings cover backend / world-engine / shared core / ai_stack |
| `docs/architecture/rag_in_world_of_shadows.md` | § Storage, ingestion globs, hybrid env vars, profiles | `docs/technical/ai/RAG.md` | § Storage through domains | Merged | Verified — `ai_stack/rag.py` glob updated to `docs/technical/**/*.md` |
| `docs/rag_task3_source_governance.md` | § Source policy model + profile table | `docs/technical/ai/RAG.md` | § Source governance | Merged | Verified — policy version + lane concepts present |
| `docs/architecture/mcp_in_world_of_shadows.md` | § Capability categories, modes, audit | `docs/technical/integration/MCP.md` | Full document | Merged | Verified |
| `docs/architecture/langgraph_in_world_of_shadows.md` | § Nodes, state, diagnostics | `docs/technical/integration/LangGraph.md` | Full document | Merged | Verified |
| `docs/architecture/langchain_integration_in_world_of_shadows.md` | § Runtime + Writers’ Room paths | `docs/technical/integration/LangChain.md` | Full document | Merged | Verified |
| `docs/architecture/ServerArchitecture.md` | § Boundary summary | `docs/technical/architecture/service-boundaries.md` | § Backend/Frontend/Admin/Play | Merged | Verified |
| `docs/architecture/writers_room_on_unified_stack.md` | § Canonical flow stages | `docs/technical/content/writers-room-and-publishing-flow.md` | § Writers’ Room workflow | Merged | Verified |
| `docs/architecture/observability_and_governance_in_world_of_shadows.md` | Entire document | `docs/technical/operations/observability-and-governance.md` | (same content, renamed) | Moved | Verified — file identity preserved |
| `docs/architecture/ai_stack_in_world_of_shadows.md` | § Layered stack / authority | `docs/technical/ai/ai-stack-overview.md` | § Layers + graph | Superseded | Verified — stale “planned M6+” wording not carried forward; current behavior documented |
| `docs/rag_task4_readiness_and_trace.md` | Operational evaluation detail | `docs/archive/rag-task-legacy/rag_task4_readiness_and_trace.md` | — | Archived | Verified — not required on active reader path; summary only in `RAG.md` |
| `docs/GoC_Gate_Baseline_Audit_Plan.md` | Program plan | `docs/archive/documentation-consolidation-2026/GoC_Gate_Baseline_Audit_Plan.md` | — | Archived | Verified — narrow contract docs remain root; plan is historical |
| `docs/archive/architecture-legacy/area2_*.md` | Various gate tables | — | — | Not migrated to active surface | N/A — intentionally evidence-only per consolidation policy |

**Gate:** No listed source was deleted from git history; moves are `git mv` to `docs/archive/` or superseded by explicit canonical pages with verification rows above.
