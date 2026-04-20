# Architecture overview

World of Shadows is a **multi-service narrative platform**: a player web app, an admin web app, a **backend** (API, auth, persistence, content compilation), and a **play service** (`world-engine/`) that owns **authoritative live session** execution. Shared library code lives in `story_runtime_core/`; AI-assisted turns run through `ai_stack/` (retrieval, LangGraph, LangChain adapters, capabilities) under **runtime rules**—models propose; the runtime **validates and commits**.

## Layered responsibilities

| Layer | Repository location | Responsibility |
|-------|---------------------|----------------|
| Player UI | `frontend/` | Public routes, play shell, WebSocket bootstrap to play service |
| Admin UI | `administration-tool/` | Operations and governance UI; backend APIs only |
| Backend | `backend/` | REST API, database, auth, forum/news/wiki, content module load/compile, integration with play service |
| Play service | `world-engine/` | Session lifecycle, turn execution, authoritative runtime session state |
| Shared runtime models | `story_runtime_core/` | Interpretation contracts, registry, adapters reused by backend and world-engine |
| AI stack | `ai_stack/` | RAG, LangGraph turn graph (GoC), LangChain structured invocation, MCP-aligned capabilities |
| Canonical content | `content/modules/<module_id>/` | YAML-first modules (including God of Carnage) |
| Writers’ Room demo | `writers-room/` | Optional UI over backend Writers’ Room APIs |
| MCP tools | `tools/mcp_server/` | Developer/operator tooling surface |

## Authority (summary)

- **World-engine** is the authoritative host for **story session** execution and committed turn effects.
- **Backend** owns policy, publishing governance, admin APIs, and persistence for platform data.
- **AI output** is **proposal data** until runtime validation and commit rules allow state changes. See [`runtime-authority-and-state-flow.md`](../runtime/runtime-authority-and-state-flow.md) and [`docs/CANONICAL_TURN_CONTRACT_GOC.md`](../../CANONICAL_TURN_CONTRACT_GOC.md) for GoC.

## Primary player input

Natural-language input is the **primary** contract at the play UI; structured commands remain supported as one interpretation mode. See [`player_input_interpretation_contract.md`](../runtime/player_input_interpretation_contract.md) and [`docs/start-here/how-ai-fits-the-platform.md`](../../start-here/how-ai-fits-the-platform.md) (plain language).

## Where to read next

- **Service boundaries and URLs:** [`service-boundaries.md`](service-boundaries.md)
- **AI/RAG/orchestration:** [`../ai/ai-stack-overview.md`](../ai/ai-stack-overview.md)
- **Session/trace observability:** [`../operations/observability-and-governance.md`](../operations/observability-and-governance.md) — traces, audits, governance APIs
- **ADR (runtime authority):** [`docs/governance/adr-0001-runtime-authority-in-world-engine.md`](../../governance/adr-0001-runtime-authority-in-world-engine.md)
