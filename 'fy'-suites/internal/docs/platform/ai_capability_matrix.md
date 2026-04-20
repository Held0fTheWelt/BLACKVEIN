# AI Capability Matrix

This report shows which AI/graph/retrieval mechanisms are already wired into the current fy workspace and which ones are still aspirational.

## Shared mechanisms

- langgraph_ready: inspect_graph, audit_graph, context_pack_graph, triage_graph
- langchain_ready: structured-output-compatible envelopes, tool-like suite commands, retrieval/context-pack surfaces
- rag_ready: semantic_index, context_packs, cross_suite_intelligence
- slm_llm_routing: model_router, decision_policy

## Per-suite mechanisms

### contractify

- decision_policy
- import/legacy-import
- consolidate
- ADR reflection

### testify

- ADR reflection checks
- cross-suite status use

### documentify

- template-aware generation
- AI-readable tracks

### docify

- inline-explain guidance
- public API doc checks

### despaghettify

- local spike surfacing

### templatify

- template inventory/validation/drift

### usabilify

- human-readable next steps

### securify

- security lane + secret-risk review

### observifyfy

- internal suite-memory and non-contaminating tracking

### mvpify

- prepared MVP import
- doc mirroring
- cross-suite orchestration

### metrify

- usage ledger
- cost reporting
- observify bridge
- AI spend summaries

### diagnosta

- bounded readiness cases
- blocker graphs
- claim-honesty outputs
- strategy-profile-aware diagnosis

### coda

- bounded closure packs
- cross-suite obligations/tests/docs
- explicit residue ledgers
- review-first closure assembly

## Aspirational next upgrades

- Swap graph recipe stubs for real LangGraph checkpointers and human-interrupt resume once external runtime dependencies are allowed.
- Bind model-router task classes to concrete LangChain model backends and provider-native structured output in production deployments.
- Promote semantic index scoring to stronger embedding/vector backends when cost/runtime policy permits.
