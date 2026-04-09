# RAG retrieval core hardening (Task 1)

English implementation note for the local hybrid RAG subsystem (`ai_stack/rag.py`, `ai_stack/semantic_embedding.py`).

## What was hardened

### Embedding backend (`semantic_embedding.py`)

- **`EncodeOutcome`** and **`encode_texts_detailed` / `encode_query_detailed`** return stable reason codes for every failure path (env disabled, empty input, missing NumPy, missing fastembed, encode count mismatch, runtime errors).
- **`EmbeddingBackendReport`** now includes **`primary_reason_code`**, **`cache_dir_identity`** (resolved cache path or `__default__`), and continues to expose **`messages`** as a full code tuple.
- **`embedding_cache_dir_identity_for_meta()`** records cache location in dense-index metadata for observability.
- Public **`encode_texts` / `encode_query`** remain backward compatible (`ndarray | None`).

### Index lifecycle (`rag.py`)

- **`DENSE_INDEX_META_SCHEMA`** (`c1_dense_index_meta_v2`) gates persisted dense metadata. Legacy meta without schema is rejected (rebuild).
- **`vectors_canonical_sha256`**: SHA-256 over **row-major float32 vector bytes** of the stored matrix (not NPZ file bytes).
- **Commit order**: write temp NPZ, write temp meta JSON, **`os.replace` NPZ then meta**. Meta is the commit marker; orphan NPZ without valid meta is never loaded (`uncommitted_vectors_only` + reason `dense_meta_missing_or_uncommitted`).
- **`DenseIndexLoadResult`** and **`_load_corpus_embedding_index`** return explicit **`reason_codes`** and **`artifact_validity`** (`valid` / `invalid` / `missing` / `uncommitted_vectors_only`).
- **`_ensure_corpus_embedding_index`** sets corpus-level diagnostics: **`rag_dense_*`**, **`rag_embedding_*`**, records rebuild reasons, and treats save failures as **`partial_write_failure`** with no silent success.

### Degradation modes (`RetrievalDegradationMode`)

Stable string enum values:

| Value | Meaning |
| --- | --- |
| `hybrid_ok` | Hybrid scoring used (including intentional `use_sparse_only` as “ok” for routing). |
| `sparse_fallback_due_to_no_backend` | Env off or backend probe not `embedding_backend_ok`. |
| `sparse_fallback_due_to_encode_failure` | Query dense encode failed. |
| `sparse_fallback_due_to_invalid_or_missing_dense_index` | Backend ok but no usable committed dense index. |
| `rebuilt_dense_index` | **Dense index build action** when a new index was written this session (`rag_dense_index_build_action`). |
| `degraded_due_to_partial_persistence_problem` | Uncommitted NPZ / partial write detected on load path. |
| `corpus_empty` | No chunks in corpus. |

`RetrievalResult` / `ContextPack` carry **`degradation_mode`**, **`dense_index_build_action`**, **`dense_rebuild_reason`**, **`dense_artifact_validity`**, **`embedding_reason_codes`**, **`embedding_index_version`**, **`embedding_cache_dir_identity`**. Capability **`wos.context_pack.build`** passes the same fields under `retrieval`.

## Rebuild and invalidation rules

Rebuild dense index when any of the following holds after load:

- Meta missing, wrong schema, JSON invalid, fingerprint / corpus or embedding version / model id / chunk count / dim / **canonical hash** mismatch.
- NPZ missing or load/shape errors.
- Orphan NPZ (no meta): load fails; next successful ensure rewrites both artifacts.

Corpus JSON invalidation is unchanged: fingerprint and `INDEX_VERSION` on `PersistentRagStore.load`.

## Optional improvements beyond minimum

- Explicit **`DenseIndexLoadResult`** instead of silent `None` from load.
- Corpus **runtime diagnostics** fields (not persisted in corpus JSON) for operator clarity.
- Focused tests for drift, hash mismatch, orphan NPZ, missing NPZ, meta replace failure, and query-encode fallback.

## Intentionally deferred (later tasks)

- Hybrid weighting / reranking / context packing redesign.
- Source governance and MCP tool surface.
- Distributed vector store or multi-host replication.
