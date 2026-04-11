"""RAG layer: version strings, tuning weights, and domain access map (DS-003 split from rag.py)."""

from __future__ import annotations

from ai_stack.rag_types import ContentClass, RetrievalDomain

DOMAIN_CONTENT_ACCESS: dict[RetrievalDomain, set[ContentClass]] = {
    RetrievalDomain.RUNTIME: {
        ContentClass.AUTHORED_MODULE,
        ContentClass.RUNTIME_PROJECTION,
        ContentClass.CHARACTER_PROFILE,
        ContentClass.TRANSCRIPT,
        ContentClass.POLICY_GUIDELINE,
    },
    RetrievalDomain.WRITERS_ROOM: {
        ContentClass.AUTHORED_MODULE,
        ContentClass.RUNTIME_PROJECTION,
        ContentClass.CHARACTER_PROFILE,
        ContentClass.TRANSCRIPT,
        ContentClass.REVIEW_NOTE,
        ContentClass.POLICY_GUIDELINE,
    },
    RetrievalDomain.IMPROVEMENT: {
        ContentClass.AUTHORED_MODULE,
        ContentClass.RUNTIME_PROJECTION,
        ContentClass.TRANSCRIPT,
        ContentClass.REVIEW_NOTE,
        ContentClass.EVALUATION_ARTIFACT,
        ContentClass.POLICY_GUIDELINE,
    },
    RetrievalDomain.RESEARCH: {
        ContentClass.AUTHORED_MODULE,
        ContentClass.RUNTIME_PROJECTION,
        ContentClass.TRANSCRIPT,
        ContentClass.REVIEW_NOTE,
        ContentClass.EVALUATION_ARTIFACT,
        ContentClass.POLICY_GUIDELINE,
        ContentClass.CHARACTER_PROFILE,
    },
}


INDEX_VERSION = "c1_next_hybrid_v1"

# Dense index on disk: meta JSON is the commit marker (see module docstring).
DENSE_INDEX_META_SCHEMA = "c1_dense_index_meta_v2"

# Retrieval ranking behavior version (not corpus/storage INDEX_VERSION).
RETRIEVAL_PIPELINE_VERSION = "task2_hybrid_v2"

# Source policy layer version (Task 3); orthogonal to pipeline and index versions.
RETRIEVAL_POLICY_VERSION = "task3_source_governance_v1"

# Legacy single-weight hybrid (superseded by profile maps; kept for tests/import stability).
HYBRID_DENSE_WEIGHT = 0.62
HYBRID_SPARSE_WEIGHT = 0.38

# Per-profile dense/sparse balance for initial hybrid core (both signals in ~[0, 1]).
PROFILE_HYBRID_WEIGHTS: dict[str, tuple[float, float]] = {
    "runtime_turn_support": (0.58, 0.42),
    "writers_review": (0.60, 0.38),
    "improvement_eval": (0.54, 0.46),
    "research_eval": (0.57, 0.43),
}

# Weak dense + strong sparse: do not let a low dense cosine collapse a strong lexical match.
HYBRID_DENSE_WEAK_THRESHOLD = 0.24
HYBRID_SPARSE_STRONG_THRESHOLD = 0.33
# Rescue blend emphasizes sparse when dense is weak (explicit, linear).
HYBRID_WEAK_DENSE_SPARSE_EMPHASIS = 0.78

# Initial score scale (keeps final scores in a band compatible with downstream heuristics).
HYBRID_CORE_SCALE = 4.0

# Reranking pool sizing (deterministic).
RERANK_POOL_FACTOR = 4
RERANK_POOL_MIN = 16
RERANK_POOL_CAP = 56

# Agreement bonus applies only in reranking when both signals exceed a floor (single stage).
RERANK_AGREEMENT_MIN_SIGNAL = 0.14
RERANK_AGREEMENT_BONUS_CAP = 0.40

# Near-duplicate suppression (character trigram Jaccard, deterministic).
DUP_TRIGRAM_JACCARD_DROP = 0.91
DUP_SAME_SOURCE_JACCARD_DROP = 0.86
DUP_IMPROVEMENT_RELAXATION = 0.94

# Initial retrieval boosts (reranking adds profile-specific module emphasis).
INITIAL_MODULE_MATCH_BOOST = 1.15
INITIAL_SCENE_HINT_BOOST = 1.12
RERANK_MODULE_MATCH_EXTRA: dict[str, float] = {
    "runtime_turn_support": 1.22,
    "writers_review": 1.05,
    "improvement_eval": 0.88,
}
