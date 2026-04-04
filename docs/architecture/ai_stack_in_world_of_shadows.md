# AI Stack in World of Shadows

Status: Canonical architecture baseline for Milestones 0-5.

## Layered stack

World of Shadows uses the following AI stack model:

1. Model layer: LLM and SLM providers.
2. Orchestration layer: LangGraph (planned for M6+ integration).
3. Integration layer: LangChain (planned for M6+ integration).
4. Knowledge layer: RAG ingestion/retrieval (planned for M6+ integration).
5. Action layer: MCP capability surface (planned for M6+ integration).
6. Runtime host: World-Engine story runtime (authoritative turn/state commit).
7. Policy and governance layer: Backend/Admin.

The stack is cumulative, but runtime authority is never delegated to a model.

## Runtime authority model

- World-Engine is the single authoritative host for story session execution.
- Backend and Admin provide:
  - policy enforcement,
  - review and diagnostics surfaces,
  - content publishing workflows,
  - governance and moderation controls.

## Input contract direction

Natural-language player input is the primary runtime contract.
Explicit commands are still supported, but only as one recognized interpretation mode
inside the broader input understanding pipeline.

## AI proposal vs runtime commit

AI output is proposal data, not committed state.
The runtime must:

- validate proposals,
- apply policy and legality checks,
- decide accepted mutations/transitions,
- commit authoritative state changes.

## Milestone 0-5 implementation scope

Implemented in M0-M5:

- canonical architecture and authority docs,
- canonical authored content compiler outputs,
- shared story runtime core extraction,
- World-Engine story runtime hosting APIs,
- model registry/routing/adapters with diagnostics,
- structured natural-language input interpretation contract and integration.

Deferred to M6+:

- full LangChain integration,
- full LangGraph orchestration graph,
- production RAG indexing/retrieval pipelines,
- production MCP tool network for runtime actions.
