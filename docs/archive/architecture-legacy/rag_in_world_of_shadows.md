# RAG in World of Shadows

Status: C1 repaired baseline (semantic + persistent operational retrieval).

## Purpose

Provide retrieval support for authoritative runtime, Writers-Room review workflows, and improvement/evaluation workflows while keeping narrative authority in World-Engine and governance in backend/admin layers.

## Storage approach

- Runtime retriever persistence is active by default through `.wos/rag/runtime_corpus.json`.
- Startup retrieval now attempts cache load first and rebuilds only when the source fingerprint changes.
- Source fingerprinting is based on selected source file path + size + mtime metadata.
- Persisted corpus carries:
  - `index_version`
  - `corpus_fingerprint`
  - per-chunk `source_version` and `source_hash`
  - retrieval profile version markers

This is a local persistent store, not a distributed vector database.

## Ingestion and metadata/versioning

Ingestion reads project-owned sources:

- `content/**/*` authored materials (`.md`, `.json`, `.yml`, `.yaml`)
- `docs/architecture/**/*.md` policy and architecture guidance
- `docs/reports/**/*.md` review and evaluation artifacts
- Tracked **fixture** JSON under `backend/fixtures/improvement_experiment_runs/` is intentionally **excluded** from the canonical RAG fingerprint glob set in `ai_stack/rag.py` (refresh 2026-04-09) to avoid ingesting sample experiment payloads as architecture text.

Chunk metadata includes:

- `source_path`, `source_name`, `content_class`
- `source_version` (`sha256:<prefix>`) and `source_hash`
- `canonical_priority` (authored/canonical material receives higher priority)
- semantic sparse-vector terms and norm

When source content changes, chunk source versions change accordingly.

## Embedding/retrieval approach

### Sparse path (always available)

- Canonicalized token normalization, concept expansion terms, weighted sparse vectors with IDF weighting, cosine similarity ranking.
- Does not require `fastembed` or downloaded models.
- When the dense path is unavailable or disabled, `ContextRetriever` uses this path only and sets `retrieval_route=sparse_fallback` (explicit in ranking notes).

### Dense / hybrid path (C1-next, optional at install time)

- **Optional dependency:** `fastembed` (declared in `world-engine/requirements.txt` and `backend/requirements.txt`). The stack runs without it; hybrid scoring is off in that case.
- **Strongly recommended for full BC-next / C1-next verification:** environments that must prove the hybrid path should install `fastembed`, allow a one-time model fetch (or use a pre-populated cache), and pin the cache directory for reproducibility.
- **Model:** `BAAI/bge-small-en-v1.5` (ONNX via fastembed), L2-normalized vectors.
- **Artifacts:** `.wos/rag/runtime_embeddings.npz` + `runtime_embeddings.meta.json` next to `runtime_corpus.json`, versioned so mismatched fingerprints or index versions force rebuild.
- **Explicit routing:** `retrieval_route=hybrid` when the dense index and query encoding succeed; otherwise `sparse_fallback` (e.g. missing dependency, `WOS_RAG_DISABLE_EMBEDDINGS`, corrupt sidecar, or query encode failure—with `embedding_query_encode_failed` in ranking notes when the failure happens at query time).

### Environment variables (embedding cache and toggles)

| Variable | Effect |
|----------|--------|
| `WOS_RAG_DISABLE_EMBEDDINGS` | When set to `1` / `true` / `yes`, disables dense encoding and forces sparse-only retrieval (explicit fallback). |
| `WOS_RAG_EMBEDDING_CACHE_DIR` | When set to a directory path, passed to `fastembed.TextEmbedding(cache_dir=...)` so model/ONNX downloads land in a known location (recommended for CI and reproducible local runs). |
| `HF_HOME`, `HUGGINGFACE_HUB_CACHE`, etc. | Standard Hugging Face hub variables may still influence download/cache layout when the fastembed stack uses the hub; the table above documents the repo-specific override. |

### Introspection

- `ai_stack.semantic_embedding.embedding_backend_probe()` returns structured availability (`import_ok`, `encode_ok`, `disabled_by_env`, reason codes) without writing RAG files. Use it in tooling or tests instead of inferring capability from retrieval alone.

### Profile and context boosts

Applied on top of the chosen scoring path (hybrid or sparse):

- content-class boosts by profile
- canonical priority boost
- module match boost
- scene hint boost

## Retrieval domains and active profiles

- `runtime` domain, profile `runtime_turn_support`
- `writers_room` domain, profile `writers_review`
- `improvement` domain, profile `improvement_eval`

Domain content access gates remain enforced before ranking.

## Canonical authored/published prioritization

Canonical authored material is treated as a first-class source through:

- explicit authored-module classification
- canonical-priority metadata at ingestion
- profile-level canonical boost during ranking

This keeps runtime retrieval biased toward canonical authored truth where relevant.

## Real wiring in active paths

- World-Engine runtime turn execution uses `build_runtime_retriever(...)` and therefore the persistent semantic corpus path.
- Writers-Room workflow uses the same retrieval core through capability invocation (`wos.context_pack.build`) with `writers_review` profile.

## Current limits

- **Hybrid dense retrieval** is local, linear scan over chunk vectors (no ANN service); first use may require network access to fetch the ONNX model unless the cache is already populated.
- **OS / runtime variance:** ONNX execution and Hugging Face cache behavior (e.g. symlinks on Windows) can differ by machine; the sparse path remains the portable baseline.
- Persistence is single-node local JSON + optional npz sidecars; not a distributed vector database.
- There is no advanced profile auto-tuning or retrieval quality dashboard yet.

See `docs/reports/ai_stack_gates/H1_EMBEDDING_HARDENING_GATE_REPORT.md` for the embedding/cache hardening gate and remaining environment risk.
