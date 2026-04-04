# C1-next gate report — stronger semantic retrieval foundation

## Verdict: **Pass**

## Scope completed

- Added **local ONNX embeddings** via `fastembed` (`BAAI/bge-small-en-v1.5`) with L2-normalized vectors.
- Persisted dense index alongside the existing JSON corpus: `.wos/rag/runtime_embeddings.npz` + `runtime_embeddings.meta.json` (fingerprint + corpus/index/embedding version + model id + chunk count).
- **`ContextRetriever` hybrid scoring**: weighted mix of dense cosine and existing sparse semantic-term cosine; profile, canonical, module, and scene boosts unchanged.
- **Explicit `retrieval_route`**: `hybrid` when the dense index and query encoding succeed; **`sparse_fallback`** when embeddings are disabled (`WOS_RAG_DISABLE_EMBEDDINGS`), missing/corrupt index, or query encode failure (with `embedding_query_encode_failed` in ranking notes when applicable).
- **Corpus JSON version** bumped to `c1_next_hybrid_v1` so prior caches invalidate; embedding sidecar uses `c1_next_embed_v1`.
- **Capability and LangGraph fallback payloads** expose `retrieval_route`, `embedding_model_id`, and `top_hit_score`; audit summaries include `retrieval_route` and `top_hit_score` where present.

## Files changed

| Area | Files |
|------|--------|
| Embeddings | `wos_ai_stack/semantic_embedding.py` (new) |
| RAG | `wos_ai_stack/rag.py` |
| Capabilities / runtime | `wos_ai_stack/capabilities.py`, `wos_ai_stack/langgraph_runtime.py` |
| Dependencies | `backend/requirements.txt`, `world-engine/requirements.txt` |
| Tests | `wos_ai_stack/tests/test_rag.py`, `backend/tests/test_improvement_routes.py` (mock index version / retrieval fields) |

## What semantic step was truly added

- **Real dense vectors** (384-d BGE-small-en ONNX) combined with the existing sparse layer—not a rename of heuristics.
- **Durable local vector store** (npz + versioned meta), rebuilt when corpus fingerprint or index versions change.

## What remained from the lightweight system

- `SEMANTIC_CANON`, `SEMANTIC_EXPANSIONS`, TF–IDF-style sparse vectors, domain/profile separation, `PersistentRagStore` JSON corpus, chunking and canonical priority rules—all **retained**; sparse path remains the **honest fallback**.

## Where the stronger retrieval path is used

- **`build_runtime_retriever`** (World-Engine `StoryRuntimeManager`, backend improvement + writers-room workflows) loads/builds the embedding index and constructs `ContextRetriever` with dense weights.
- **Runtime**: LangGraph path via `wos.context_pack.build` (when registry present) or direct assembler path includes new retrieval fields.
- **Non-runtime**: `writers_room` and `improvement` modes use the same registry and retriever from `build_runtime_retriever`.

## What is still intentionally lightweight

- **Single-host** JSON + npz under `.wos/rag/`—no distributed vector DB, replication, or multi-tenant isolation.
- **First-run model download** from Hugging Face hub for `fastembed` (dev/CI must allow cache or network once).
- **No ANN index**—linear scan over chunk embeddings (acceptable for current corpus sizes).

## Tests added/updated

- **New (embedding-gated via `pytest.mark.skipif`)**: hybrid vs `use_sparse_only` paraphrase; embedding persistence across `build_runtime_retriever` reload; hybrid for runtime + improvement profiles.
- **New**: `WOS_RAG_DISABLE_EMBEDDINGS=1` forces explicit `sparse_fallback`.
- **Updated**: improvement route empty-retrieval mock uses current `INDEX_VERSION` and new retrieval keys.

## Exact test commands run

```text
python -m pytest wos_ai_stack/tests/test_rag.py -v --tb=short
python -m pytest wos_ai_stack/tests/test_langchain_integration.py wos_ai_stack/tests/test_capabilities.py -v --tb=short
python -m pytest wos_ai_stack/tests/test_langgraph_runtime.py -v --tb=short
cd world-engine && python -m pytest tests/test_story_runtime_rag_runtime.py -v --tb=short
cd backend && python -m pytest tests/test_writers_room_routes.py tests/test_improvement_routes.py -v --tb=short
```

## Reason for verdict

All C1-next gate conditions are met: materially more semantic retrieval when embeddings are available, real persisted index, active code paths use it, tests demonstrate hybrid advantage over sparse-only on a constructed low-overlap paraphrase, and limitations are **not** overstated as enterprise-grade.

## Remaining risk

- **Embedding availability**: environments without `fastembed`/onnx or without model cache fall back to sparse-only (explicit, but weaker retrieval).
- **Linear dense scan** may become slow if corpus size grows without an ANN layer.
