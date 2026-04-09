# Writers’ Room and publishing flow

## Canonical authored content

- **Source of truth for runtime:** YAML modules under `content/modules/<module_id>/` (`module.yaml`, `scenes.yaml`, characters, triggers, transitions, endings, relationships, …).
- **Loader / models:** `backend/app/content/module_loader.py`, `module_models.py`.
- **Compiler:** `backend/app/content/compiler/` produces projections consumed by runtime, retrieval, and review.

## Three projections

1. **`runtime_projection`** — consumed by world-engine story runtime loading.
2. **`retrieval_corpus_seed`** — feeds RAG ingestion (`ai_stack/rag.py`).
3. **`review_export_seed`** — governance and review surfaces.

Conceptual model (authored shapes and invariants): [`canonical_authored_content_model.md`](canonical_authored_content_model.md) (same folder).

## God of Carnage binding

For GoC, **YAML is primary**; builtins must not silently override YAML. See [`docs/VERTICAL_SLICE_CONTRACT_GOC.md`](../../VERTICAL_SLICE_CONTRACT_GOC.md).

## Writers’ Room workflow (backend-first)

Primary path: `POST /api/v1/writers-room/reviews`.

Stages (see `workflow_manifest.stages` in payloads):

1. Request intake (JWT).
2. LangGraph Writers’ Room **seed** workflow.
3. `wos.context_pack.build` (domain `writers_room`) — retrieval analysis.
4. Shared model routing + adapters — proposal generation.
5. Structured artifact packaging (comments, patch/variant candidates).
6. `wos.review_bundle.build` — governance envelope.
7. LangChain retriever bridge preview for cross-stack visibility.
8. **Human review** — `accept` | `reject` | `revise` via `POST .../reviews/<id>/decision`.

Outputs are **recommendation-only** until publishing governance applies changes. Publishing authority stays in **backend/admin** processes, not in model output alone.

## Duplicate-truth warning (demo tree)

`writers-room/app/models/implementations/god_of_carnage/` may hold markdown and registry assets that can **diverge** from `content/modules/god_of_carnage/`. Treat **canonical module YAML** as runtime truth unless product policy states otherwise.

## Related

- [`docs/technical/ai/RAG.md`](../ai/RAG.md)
- [`docs/technical/integration/MCP.md`](../integration/MCP.md)
- Dev-oriented compiler notes: [`docs/dev/architecture/content-modules-and-compiler-pipeline.md`](../../dev/architecture/content-modules-and-compiler-pipeline.md)
