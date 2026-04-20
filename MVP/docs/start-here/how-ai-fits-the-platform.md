# How AI fits the platform

This page is **layered**: a short plain-language summary first, then technical pointers for implementers.

## Plain language

**Artificial intelligence** in World of Shadows helps **run narrative turns**: it can retrieve context from authored content, propose what happens next, and shape dramatic delivery. **The platform does not treat the model as the boss of truth.** A **runtime pipeline** checks proposals against rules and **commits** only what is allowed. **Operators and developers** also use **tooling** (including an **MCP server** in this repo) to inspect health and content—tools are **not** a replacement for the play service’s authority.

Think of it as: **AI suggests** → **runtime decides** → **players see** validated results.

## Technical layer (developers)

### Retrieval (RAG)

`ai_stack/rag.py` builds **context packs** for prompts using repository paths and module semantics (including distinctions such as `content/modules/` vs `content/published/`). Retrieval feeds the turn graph’s `retrieve_context` stage. Governance-oriented docs also live under `docs/rag_task*.md` and related files.

### Orchestration (LangGraph, GoC slice)

For God of Carnage, `ai_stack/langgraph_runtime.py` defines `RuntimeTurnGraphExecutor` with a **single graph** whose high-level stages include interpretation, retrieval, canonical YAML resolution, scene direction, model invocation, **validation seam**, **commit seam**, visible render, and packaged output. The **normative node list and state fields** are anchored in `docs/VERTICAL_SLICE_CONTRACT_GOC.md` §3.

> Note: archived milestone-era stack summaries may lag the **implemented** GoC graph; when they differ, prefer the **vertical slice contract**, [`docs/technical/ai/ai-stack-overview.md`](../technical/ai/ai-stack-overview.md), and root `README.md` AI section for **current** GoC behavior.

### LangChain

`ai_stack/langchain_integration/` bridges **adapter invocation** for structured outputs and related flows (including Writers Room paths). It supports the graph but does not replace validation/commit rules.

### Proposal vs commit

**AI output** is **proposal data** until validation approves and commit applies effects. Authority boundaries are summarized in [`docs/technical/runtime/runtime-authority-and-state-flow.md`](../technical/runtime/runtime-authority-and-state-flow.md) and detailed in `docs/CANONICAL_TURN_CONTRACT_GOC.md`.

### MCP tooling

`tools/mcp_server/` exposes **read-oriented** tools (module listing, content search, health) and selected backend operations as implemented. Developers should read [MCP server developer guide](../dev/tooling/mcp-server-developer-guide.md) for boundaries and env configuration.

### Writers Room

Backend **Writers Room** workflows (`/api/v1/writers-room/...`) support review-oriented AI flows. **Canonical module YAML** under `content/modules/` remains the slice’s **authored source of truth** unless product policy explicitly elevates another path.

## Related

- [Glossary](../reference/glossary.md) — RAG, LangGraph, MCP, proposal vs commit.
- [System map](system-map-services-and-data-stores.md) — where the play service sits.
- [Normative contracts index](../dev/contracts/normative-contracts-index.md) — binding documents for implementers.
