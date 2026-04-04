# C1 REFOCUS Gate Report — Deepen RAG Into a More Trustworthy Operational Layer

**Date:** 2026-04-04
**Status:** PASS

## Gap Addressed

`_build_semantic_terms` in `wos_ai_stack/rag.py` performs semantic canonicalization via
`SEMANTIC_CANON` (e.g., `"argue"` → `"conflict"`) and expands canonical terms into related
paraphrases via `SEMANTIC_EXPANSIONS`. While the RAG pipeline was exercised in various tests,
no test explicitly verified that ingesting content using a canonical term (e.g., `"conflict"`)
and querying with a domain paraphrase (e.g., `"argue"`) actually returned a result — i.e.,
that semantic expansion meaningfully lifts recall for non-obvious phrasing.

## Work Done

Added `test_semantic_expansion_boosts_recall_for_paraphrased_query` to
`wos_ai_stack/tests/test_rag.py`.

The test:
1. Ingests a document containing the canonical term `"conflict"` and a distracting document
   about sports with no relevant terms.
2. Queries with `"argue about values"` — `"argue"` maps to `"conflict"` via `SEMANTIC_CANON`.
3. Asserts `status == OK` and that the `god_of_carnage` document appears in the hits.

This proves the `_normalize_token` → `_build_semantic_terms` pipeline actually improves recall
for paraphrased queries, rather than relying on lexical overlap alone.

## Semantic Expansion Path Verified

- Raw token: `"argue"`
- `_normalize_token("argue")` → looks up `SEMANTIC_CANON["argue"]` → returns `"conflict"`
- `_build_semantic_terms` adds `"conflict"` with weight 1.0 and expands via
  `SEMANTIC_EXPANSIONS["conflict"]` = `("dispute", "argument", "fight")` at weight 0.35 each
- Document containing `"conflict"` scores against both the canonical and expansion terms

## Test Results

```
collected 10 items
test_ingestion_builds_corpus_from_repo_owned_sources                  PASSED
test_retrieval_is_deterministic_for_known_relevant_content            PASSED
test_retrieval_supports_semantic_phrasing_not_only_exact_overlap      PASSED
test_retrieval_domain_separation_excludes_runtime_from_review_only_content PASSED
test_retrieval_profile_boosts_canonical_content_for_runtime           PASSED
test_context_pack_exposes_attribution_and_selection_notes             PASSED
test_runtime_retriever_persists_and_reuses_index                      PASSED
test_ingestion_metadata_changes_when_source_content_changes           PASSED
test_semantic_expansion_boosts_recall_for_paraphrased_query           PASSED
test_retrieval_gracefully_handles_sparse_or_absent_corpus             PASSED
10 passed in 0.45s
```

## Verdict

**PASS** — Semantic expansion (paraphrase → canonical term → retrieval boost) is now explicitly
verified. The RAG layer is demonstrably more trustworthy than lexical-match-only retrieval.
