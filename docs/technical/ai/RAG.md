# RAG (retrieval-augmented generation)

**Purpose:** Support **runtime turns**, **Writers’ Room** review, and **improvement** workflows with project-owned retrieval while keeping **narrative authority** in world-engine and **governance** in backend/admin layers.

## Storage model

- **Local persistence** (not a hosted vector DB): default path `.wos/rag/runtime_corpus.json`.
- Startup tries **cache load** first; rebuild when **source fingerprint** changes (selected paths: size + mtime).
- Persisted corpus carries `index_version`, `corpus_fingerprint`, per-chunk `source_version` / `source_hash`, and profile version markers.

## Ingestion sources

Ingestion reads repository-owned sources:

- `content/**/*` — `.md`, `.json`, `.yml`, `.yaml`
- `docs/technical/**/*.md` — technical documentation (replacing the former `docs/architecture/**/*.md` glob in policy text)
- `docs/reports/**/*.md` — review and evaluation artifacts where included by configuration

Tracked fixture JSON under `backend/fixtures/improvement_experiment_runs/` is **excluded** from the canonical fingerprint glob in `ai_stack/rag.py` so sample experiment payloads are not ingested as architecture text.

Chunk metadata includes `source_path`, `source_name`, `content_class`, `source_version` (`sha256:` prefix), `source_hash`, `canonical_priority`, sparse-vector terms, and norms.

## Scoring paths

### Sparse (always available)

Canonicalized tokens, concept expansion, IDF-weighted sparse vectors, cosine similarity. If dense/hybrid is off or fails, `ContextRetriever` uses `retrieval_route=sparse_fallback`.

### Dense / hybrid (optional)

- Optional dependency: `fastembed` (see `world-engine/requirements.txt`, `backend/requirements.txt`).
- Model: `BAAI/bge-small-en-v1.5` (ONNX via fastembed), L2-normalized.
- Artifacts: `.wos/rag/runtime_embeddings.npz` + `runtime_embeddings.meta.json` beside the corpus; version mismatches force rebuild.
- **Routing:** `retrieval_route=hybrid` when encoding succeeds; otherwise sparse fallback (`embedding_query_encode_failed` in notes when query-time encode fails).

### Environment variables

| Variable | Effect |
|----------|--------|
| `WOS_RAG_DISABLE_EMBEDDINGS` | `1` / `true` / `yes` forces sparse-only |
| `WOS_RAG_EMBEDDING_CACHE_DIR` | Cache dir for `TextEmbedding` (reproducible CI) |
| `HF_HOME`, `HUGGINGFACE_HUB_CACHE` | May affect hub download layout |

Probe without side effects: `ai_stack.semantic_embedding.embedding_backend_probe()`.

### Profile boosts

Content-class boosts, canonical priority, module match, scene hints — applied on top of hybrid or sparse base scoring.

## Domains and profiles

- `runtime` / `runtime_turn_support`
- `writers_room` / `writers_review`
- `improvement` / `improvement_eval`

Domain content access gates apply before ranking.

## Source governance (retrieval policy)

A **governance layer** sits on top of lifecycle metadata and rerank quality:

- **Lanes:** `canonical`, `supporting`, `draft_working`, `internal_review`, `evaluative` — from `ContentClass`, `canonical_priority`, and repo-relative `source_path` (e.g. `content/published/` vs `content/modules/`).
- **Visibility classes:** `runtime_safe`, `writers_working`, `improvement_diagnostic`.
- **Policy version:** `retrieval_policy_version` is `task3_source_governance_v1` (`RETRIEVAL_POLICY_VERSION` in `ai_stack/rag.py`).

**Runtime profile (`runtime_turn_support`):** hard gate drops same-module **draft_working** authored chunks from the rerank pool when a **published canonical** authored chunk (`canonical_priority >= 4`) for that `module_id` is already present. **Writers’ profile** keeps broader draft visibility with soft boosts. **Improvement profile** adds small boosts for policy-guideline chunks.

Outputs expose `source_evidence_lane`, `source_visibility_class`, `policy_note`, and related fields on hits and context packs.

## Active wiring

- **World-engine:** `build_runtime_retriever(...)` on the runtime turn path.
- **Writers’ Room:** `wos.context_pack.build` in `writers_room` mode; retriever bridge shares semantics.

## Limits

- Hybrid retrieval is **local linear scan** over chunk vectors (no ANN service); first use may download ONNX unless cached.
- OS variance for ONNX and HF cache (e.g. Windows symlinks) — sparse path remains the portable baseline.
- No retrieval quality dashboard in-product yet.

## Historical task documents

Embedding hardening and evaluation harness details from former `docs/rag_task4_*.md` and gate reports are **archived** under [`docs/archive/rag-task-legacy/`](../archive/rag-task-legacy/) with claims mapped in [`../documentation-consolidation-2026/DURABLE_TRUTH_MIGRATION_VERIFICATION_TABLE.md`](../documentation-consolidation-2026/DURABLE_TRUTH_MIGRATION_VERIFICATION_TABLE.md).
