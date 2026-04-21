# Post-Repair Validation Record — 2026-04-21 (embedding lane)

## Exact commands and outcomes

- `python -m pytest ai_stack/tests/test_semantic_embedding.py -q -rs` → **8 passed**
- `python -m pytest ai_stack/tests/test_rag.py -q -rs` → **56 passed**
- `python -m pytest ai_stack/tests -q -rs` → **222 passed, 0 skipped**
- `python -m pytest world-engine/tests/test_story_runtime_rag_runtime.py -q` → **8 passed, 1 warning**

## Change versus the previous state

Previous state:
- `python -m pytest ai_stack/tests -q -rs` → **208 passed, 14 skipped**

Current state:
- `python -m pytest ai_stack/tests -q -rs` → **222 passed, 0 skipped**

Delta:
- all 14 embedding-gated skips removed
- no newly exposed AI-stack product failures in the replayed suite

## Evidence classification

- `ai_stack/tests/test_semantic_embedding.py`: direct embedding backend / cache wiring proof
- `ai_stack/tests/test_rag.py`: direct hybrid retrieval + dense-index persistence proof
- `ai_stack/tests`: full local AI-stack replay proof for the repository lane
- `world-engine/tests/test_story_runtime_rag_runtime.py`: adjacent runtime regression guard after embedding backend change
