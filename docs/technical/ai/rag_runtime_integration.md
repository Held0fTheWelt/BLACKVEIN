# RAG runtime integration (target architecture and doc map)

This page ties **retrieval** to the **live turn path**, **ADR-0041**, **Narrator/NPC** context, and **authority boundaries**. It complements [RAG.md](RAG.md) (mechanics, domains, governance) with **integration rules** and ADR ownership.

**Normative governance:** [ADR-0044](../../ADR/adr-0044-runtime-rag-context-fabric-routing-and-authority-boundaries.md) (routing, authority metadata, ADR-0041 and frontend boundaries), [ADR-0045](../../ADR/adr-0045-runtime-memory-indexes-and-retrieval-write-contracts.md) (memory indexes, write contracts, audience filters).

## What RAG should become

- A **bounded context fabric**: ranked evidence + structured bundles for models and operators.
- **Not** engine truth: canonical state remains world-engine session + commit records + validation seams (`ai_stack/langgraph/langgraph_runtime_executor.py`).

## Routing inputs (target contract)

Build a **retrieval plan** from:

| Input | Source (examples) |
| ----- | ------------------- |
| Turn class | LangGraph / turn situation records |
| Selected capabilities | `ai_stack/capabilities/capability_selector.py` output when present |
| Active actor / lane | Actor lane hydration, turn state |
| Beat phase | Planner truth / beat signals from committed path |
| Authority scope | `runtime_generation` vs `operator_diagnostic` vs writers/improvement domains |

The plan selects: **profile**, **max chunks**, **allowed lanes** (content module vs session memory vs diagnostic-only), and **exclusions** (e.g. no private NPC lane for Narrator unless policy-bound dramatic irony).

## Consumer bundles

| Bundle | Purpose | Authority |
| ------ | ------- | --------- |
| Narrator | Scene voice, disclosure, sensory anchors | Prompt support; must respect disclosure and lane |
| NPC | Goals, conflicts, private memory | Prompt support; filtered per `npc_self` |
| Validator observation | Drift, hints | Observation only; never sole seam proof |
| Operator diagnostic | ADR/Matrix/Langfuse/MCP | Non-player authority; no readiness promotion by itself |

## Canonical vs retrieved (quick reference)

| Kind | Examples | Truth? |
| ---- | -------- | ------ |
| Canonical runtime state | `StorySession`, environment, committed aspects | Yes (for play) |
| Content module | YAML/MD policy and canon | Authoring truth |
| Retrieved chunk / `context_text` | `.wos/rag/` hits | No |
| Langfuse/MCP | Traces, scores | Evidence, not play truth |
| Capability Matrix / ADR docs | Governance metadata | Not runtime state |

## Implementation anchors (code)

- Retrieval and packs: `ai_stack/rag/__init__.py`, `ai_stack/rag/rag_context_retriever.py`, `ai_stack/rag/rag_context_pack_assembler.py`, `ai_stack/capabilities/capabilities_registry_context_writers_handlers.py` (`wos.context_pack.build`).
- Runtime graph: `ai_stack/langgraph/langgraph_runtime_executor.py` (`_retrieve_context`, `run_validation_seam`, `run_commit_seam`).
- ADR-0041: `ai_stack/capabilities/capability_selector.py`, `ai_stack/capabilities/capability_validator_registry.py`, `ai_stack/validation_authority_bridge.py`, `ai_stack/runtime_readiness_consumer.py`.
- Session truth: `world-engine/app/story_runtime/manager.py`, `world-engine/app/story_runtime/commit_models.py`.
- Player bundle: `backend/app/api/v1/game_routes.py` (`_player_session_bundle`).
- Play shell: `frontend/static/play_shell.js` (display backend fields; no readiness inference from text).

## Phased delivery (reference)

Align implementation waves with the repository integration plan (P0: boundaries + routing + indexes + gates; P1: operator diagnostic lanes; P2: analytics/long-horizon convenience). This document does not duplicate line-by-line task lists; use the accepted plan artifact and ADR-0044/0045 for governance decisions.

## Verification

When changing **only** ADR or technical docs touched by Capability Matrix or ADR-0039 gates, run:

```bash
cd D:\WorldOfShadows
python -m pytest tests/test_capability_matrix_documentation_readiness.py -q
python -m pytest tests/gates/test_adr_0039_pi_scope.py tests/gates/test_adr0039_pi_scope.py -q
git diff --check
```
