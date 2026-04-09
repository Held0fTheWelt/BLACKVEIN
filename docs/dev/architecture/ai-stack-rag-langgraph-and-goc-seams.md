# AI stack: RAG, LangGraph, and GoC seams (developer seam)

**Canonical technical documentation:**

- [`docs/technical/ai/ai-stack-overview.md`](../../technical/ai/ai-stack-overview.md)
- [`docs/technical/ai/RAG.md`](../../technical/ai/RAG.md)
- [`docs/technical/integration/LangGraph.md`](../../technical/integration/LangGraph.md)
- [`docs/technical/integration/LangChain.md`](../../technical/integration/LangChain.md)

**Quick integration map** (unchanged intent):

| Piece | Location |
|-------|----------|
| Turn graph executor | `ai_stack/langgraph_runtime.py` |
| GoC YAML / seams | `ai_stack/goc_yaml_authority.py`, `goc_turn_seams.py`, `scene_director_goc.py` |
| RAG | `ai_stack/rag.py` |
| LangChain bridge | `ai_stack/langchain_integration/` |
| Capabilities | `ai_stack/capabilities.py` |

**Normative slice contracts:** [`docs/VERTICAL_SLICE_CONTRACT_GOC.md`](../../VERTICAL_SLICE_CONTRACT_GOC.md), [`docs/CANONICAL_TURN_CONTRACT_GOC.md`](../../CANONICAL_TURN_CONTRACT_GOC.md).

Plain-language counterpart: [`docs/start-here/how-ai-fits-the-platform.md`](../../start-here/how-ai-fits-the-platform.md).
