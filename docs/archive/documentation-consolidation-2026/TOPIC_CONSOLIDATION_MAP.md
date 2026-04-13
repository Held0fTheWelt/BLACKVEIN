# Documentation topic consolidation map

Consolidation pass: 2026. Maps **enduring topics** to a **single canonical active document** under `docs/technical/` (or audience roots). Legacy sources are archived under `docs/archive/` after migration verification.

| Topic | Canonical active document | Former / duplicate sources (disposition) |
|-------|---------------------------|------------------------------------------|
| Platform overview (plain) | `docs/start-here/what-is-world-of-shadows.md` | Renamed from `world-of-shadows-overview.md` |
| System operation story | `docs/start-here/how-world-of-shadows-works.md` | New; synthesizes overview + system map |
| GoC as experience (orientation) | `docs/start-here/god-of-carnage-as-an-experience.md` | Renamed from `god-of-carnage-experience-overview.md` |
| Glossary (full) | `docs/reference/glossary.md` | Canonical definitions; `docs/start-here/glossary.md` is a short pointer |
| Runtime authority & session flow | `docs/technical/runtime/runtime-authority-and-state-flow.md` | Merged from `runtime_authority_decision.md`, dev runtime doc (archived originals where redundant) |
| Architecture overview | `docs/technical/architecture/architecture-overview.md` | `ai_stack_in_world_of_shadows.md` (stale milestones superseded), start-here material |
| Service boundaries | `docs/technical/architecture/service-boundaries.md` | `ServerArchitecture.md`, `BackendApi.md` (archived after merge) |
| AI stack (current) | `docs/technical/ai/ai-stack-overview.md` | `ai_stack_in_world_of_shadows.md`, `llm_slm_role_stratification.md` (detail retained or cross-linked) |
| RAG | `docs/technical/ai/RAG.md` | `rag_in_world_of_shadows.md`, `rag_task3_source_governance.md`, root `rag_task4_*.md`, `rag_retrieval_*.md` |
| MCP (system) | `docs/technical/integration/MCP.md` | `mcp_in_world_of_shadows.md` |
| LangGraph | `docs/technical/integration/LangGraph.md` | `langgraph_in_world_of_shadows.md`, parts of dev AI seams doc |
| LangChain | `docs/technical/integration/LangChain.md` | `langchain_integration_in_world_of_shadows.md` |
| Writers’ Room & publishing | `docs/technical/content/writers-room-and-publishing-flow.md` | `writers_room_on_unified_stack.md`, `content-modules-and-compiler-pipeline` (dev stub remains) |
| Test strategy | `docs/technical/reference/test-strategy-and-suite-layout.md` | `dev/testing/test-pyramid-and-suite-map.md` (dev stub), `docs/testing/README.md` |
| Area2 / task closure narratives | — | `docs/archive/architecture-legacy/*` (archived) |
| Canonical Turn Contract (GoC) | `docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md` | **Narrow exception** — lives under `docs/MVPs/MVP_VSL_And_GoC_Contracts/` |
| Vertical slice / gate scoring / MVP roadmaps | `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md`, `docs/MVPs/MVP_VSL_And_GoC_Contracts/GATE_SCORING_POLICY_GOC.md`, `docs/MVPs/**/ROADMAP_MVP_*.md` | **Narrow exception** where they describe implemented slice / MVP set |

## Task 1A–4 baseline revalidation note

- `docs/audit/TASK_2_CURATED_DOCS_SURFACE_MAP.md` listed `docs/rag_task*` as curated core; **stale** relative to this consolidation — RAG truth is now **`docs/technical/ai/RAG.md`** only on the active surface.
- Other Task 2/3/4 paths remain valid as **historical evidence** under `docs/audit/`; active navigation must not depend on them for reader onboarding.
