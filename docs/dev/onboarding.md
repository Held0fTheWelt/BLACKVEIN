# Developer onboarding

Welcome. This page orients **new contributors** in a few minutes; deep system truth lives under [`docs/technical/`](../technical/README.md).

## Read in order

1. [Contributing and repo layout](contributing.md) — branches, layout, where code lives.
2. [Local development and test workflow](local-development-and-test-workflow.md) — venvs, Compose vs bare metal, common pytest entry points.
3. [System map (services)](../start-here/system-map-services-and-data-stores.md) — how processes connect.
4. [Architecture overview (technical)](../technical/architecture/architecture-overview.md) — authority and major packages.
5. [Normative contracts index](contracts/normative-contracts-index.md) — binding documents when you change behavior.

## God of Carnage slice

- Player-visible summary: [`docs/start-here/god-of-carnage-as-an-experience.md`](../start-here/god-of-carnage-as-an-experience.md)
- Turn contract: [`docs/CANONICAL_TURN_CONTRACT_GOC.md`](../CANONICAL_TURN_CONTRACT_GOC.md)
- Vertical slice checklist: [`docs/VERTICAL_SLICE_CONTRACT_GOC.md`](../VERTICAL_SLICE_CONTRACT_GOC.md)

## AI stack quick links

- [AI stack overview](../technical/ai/ai-stack-overview.md)
- [RAG](../technical/ai/RAG.md)
- [LangGraph](../technical/integration/LangGraph.md)
- [LangChain](../technical/integration/LangChain.md)
- [MCP integration](../technical/integration/MCP.md)

## Session / runtime quick links

- [Runtime authority and state flow](../technical/runtime/runtime-authority-and-state-flow.md)
- Developer seam notes: [Runtime authority and session lifecycle](architecture/runtime-authority-and-session-lifecycle.md), [AI stack, RAG, LangGraph, and GoC seams](architecture/ai-stack-rag-langgraph-and-goc-seams.md)

## Flask extensions (globals)

- Canonical list and init order: module docstring on `backend/app/extensions.py` (what `db`, `jwt`, `limiter`, `migrate`, `mail` are for and how `create_app` wires them).

## Tests

- [Test strategy and suite layout (technical)](../technical/reference/test-strategy-and-suite-layout.md)
- [Test pyramid (dev)](testing/test-pyramid-and-suite-map.md)
