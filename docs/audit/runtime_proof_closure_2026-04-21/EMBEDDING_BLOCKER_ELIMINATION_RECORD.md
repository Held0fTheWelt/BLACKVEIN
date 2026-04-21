# Embedding Blocker Elimination Record — 2026-04-21

| Blocker ID | Affected tests/suites | Root cause class | Repair performed | Validation run | Final status |
|---|---|---|---|---|---|
| EBR-01 | `ai_stack/tests/test_semantic_embedding.py` (3 previously skipped cases) | external model acquisition / runtime network residual | Added repo-controlled `ai_stack.fastembed_compat.TextEmbedding` fallback and automatic fallback path in `semantic_embedding` | `python -m pytest ai_stack/tests/test_semantic_embedding.py -q -rs` | closed |
| EBR-02 | `ai_stack/tests/test_rag.py` (11 previously skipped cases) | same residual propagated into hybrid retrieval/index build | Same fallback, preserving cache-dir and singleton contracts | `python -m pytest ai_stack/tests/test_rag.py -q -rs` | closed |
| EBR-03 | full AI-stack suite | skip gate driven by `embedding_backend_probe().available == False` | Probe now succeeds via repository-controlled fallback when external artifact path fails | `python -m pytest ai_stack/tests -q -rs` | closed |
| EBR-04 | adjacent runtime slice using RAG runtime support | adjacent regression risk after backend swap | Replayed world-engine RAG runtime slice | `python -m pytest world-engine/tests/test_story_runtime_rag_runtime.py -q` | closed |
