# Retrieval quality upgrade (Task 2)

This note describes the **Task 2** changes to the World of Shadows retrieval layer (`ai_stack/rag.py`): hybrid v2 calibration, deterministic reranking, near-duplicate suppression, and profile-aware context packing. **Task 1** lifecycle fields (`retrieval_route`, `degradation_mode`, dense index actions, artifact validity, embedding reason codes, etc.) are unchanged in meaning; Task 2 only appends compact **quality** notes and does not fold lifecycle state into scores.

## Version marker

- **`RETRIEVAL_PIPELINE_VERSION`** (`task2_hybrid_v2`): logical label for ranking/packing behavior. It is **not** `INDEX_VERSION` (corpus JSON / storage compatibility stays on `c1_next_hybrid_v1`).

## Hybrid v2 (initial score)

- **Per-profile dense/sparse weights** (`PROFILE_HYBRID_WEIGHTS`): small shifts so runtime favors slightly more dense signal, improvement slightly more sparse (evaluative vocabulary).
- **Weak-dense rescue**: if dense cosine is below `HYBRID_DENSE_WEAK_THRESHOLD` and sparse cosine is above `HYBRID_SPARSE_STRONG_THRESHOLD`, the hybrid core uses `max(linear_blend, rescue_blend)` with an explicit sparse emphasis constant—so strong lexical evidence is not collapsed by a weak embedding match.
- **Initial score** still combines scaled hybrid core, profile content boosts, canonical weight × `canonical_priority`, and smaller **initial** module/scene boosts; large module emphasis is completed in reranking (see below).

## Dense/sparse agreement

- **Single stage**: agreement is applied **only in reranking** as `RERANK_AGREEMENT_BONUS_CAP * min(dense, sparse)` when both signals exceed `RERANK_AGREEMENT_MIN_SIGNAL`. It is **not** duplicated inside the initial hybrid core.

## Deterministic reranking

- Build a **candidate pool** of size `min(RERANK_POOL_CAP, max(RERANK_POOL_MIN, max_chunks * RERANK_POOL_FACTOR))` from chunks sorted by initial score (tie-break: `chunk_id`).
- **Additive, named adjustments** (examples):
  - Extra **module match** weight (`RERANK_MODULE_MATCH_EXTRA` per profile).
  - **Runtime**: small boost for high canonical authored modules; **penalty** on transcript/runtime-projection clutter when a strong authored module for the requested `module_id` is present in the pool.
  - **Writers room**: boosts for `REVIEW_NOTE` and `TRANSCRIPT`.
  - **Improvement**: stronger boosts for `EVALUATION_ARTIFACT`, then `REVIEW_NOTE`, then `TRANSCRIPT`.
  - **Redundancy**: mild penalty vs. higher initial-scoring pool neighbors using character trigram Jaccard overlap.
- Final rerank ordering: sort by rerank score, then `chunk_id`.

## Near-duplicate suppression

- After reranking, a **greedy** pass keeps chunks in order; drops a candidate if trigram Jaccard vs. any kept chunk ≥ `DUP_TRIGRAM_JACCARD_DROP`, or if same `source_path` and Jaccard ≥ `DUP_SAME_SOURCE_JACCARD_DROP` (with a narrow exception for improvement + `EVALUATION_ARTIFACT`).
- **Improvement** uses a slightly higher duplicate threshold so near-repeated eval phrasing is not over-pruned.
- Suppression reasons appear as compact `dup_suppressed …` lines in `ranking_notes` (capped count + overflow hint).

## Context packing

- **`ContextPackAssembler`** reorders hits for **workflow sections** (e.g. runtime: “Canonical evidence” then “Supporting context”; improvement: “Evaluative evidence” first). Snippets are lightly trimmed for `compact_context`.
- Each `RetrievalHit` carries **`pack_role`** and **`why_selected`**; `ContextPack.sources` includes the same keys for downstream tools.

## Observability

- **Prefix notes** remain Task-1-shaped (`retrieval_route=…`, `degradation_mode=…`, dense fields, optional embedding failures).
- **Quality block**: `retrieval_pipeline_version=…`, hybrid weight summary, `rerank_pool_size=…`, optional `dup_suppressed…`, then per-hit lines with `pack_role` and full selection string (initial + rerank fragments).

## Optional upward extensions (beyond minimum)

- `_ScoredCandidate` internal struct for a clear retrieve pipeline.
- Profile-specific rerank constants tables and explicit clutter penalty when strong authored evidence exists in the pool.
- Sectioned `compact_context` with a stable footer key `context_pack_order=workflow_sections_then_ordinal`.

## Intentionally deferred

- Published vs. draft **governance** policy beyond existing path-based `canonical_priority`.
- External cross-encoder or API rerankers.
- Large offline evaluation harnesses or MCP-wide trace redesign.
- Embedding backend or dense persistence format changes.
