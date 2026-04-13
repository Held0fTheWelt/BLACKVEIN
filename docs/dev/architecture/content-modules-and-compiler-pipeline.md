# Content modules and compiler pipeline

How **canonical YAML modules** become **runtime**, **retrieval**, and **review** projections.

## Canonical source

- Files live under `content/modules/<module_id>/` (`module.yaml`, `scenes.yaml`, `characters.yaml`, `triggers.yaml`, `transitions.yaml`, `endings.yaml`, `relationships.yaml`, …).
- Loader models: `backend/app/content/module_loader.py`, `module_models.py`.
- Conceptual model: [`docs/technical/content/canonical_authored_content_model.md`](../../technical/content/canonical_authored_content_model.md).

## Backend services

- `backend/app/content/module_service.py` — load/validate modules from the content root.
- `backend/app/content/compiler/` — compilation to projections (inspect package for stages and outputs).

## Projections

The canonical model defines three compiled projections:

1. **`runtime_projection`** — consumed by world-engine story runtime loading paths.
2. **`retrieval_corpus_seed`** — feeds RAG / indexing approaches (see `ai_stack/rag.py`).
3. **`review_export_seed`** — governance and review surfaces.

## GoC binding

For God of Carnage, **YAML is primary**; builtins such as `god_of_carnage_solo` are **secondary** and must not silently override YAML (`docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md` §6).

## Duplicate-truth risk (writers-room)

`writers-room/app/models/implementations/god_of_carnage/` contains markdown and registry assets that may **diverge** from `content/modules/god_of_carnage/`. Treat **canonical module YAML** as runtime truth unless product policy explicitly states otherwise (`docs/audit/TASK_1B_CROSS_STACK_COHESION_BASELINE.md`).

## Related

- [AI stack, RAG, LangGraph, and GoC seams](ai-stack-rag-langgraph-and-goc-seams.md)
- [Writers’ room and publishing flow](../../technical/content/writers-room-and-publishing-flow.md) (if extending review flows)
