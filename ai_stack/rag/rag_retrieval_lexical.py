"""
Lexical / semantic term building, sparse weights, and hybrid-core
helpers for RAG retrieval (DS-003 stage 4).
"""

from __future__ import annotations

import math
import re
from typing import Protocol

from ai_stack.rag.rag_constants import (
    HYBRID_DENSE_WEAK_THRESHOLD,
    HYBRID_DENSE_WEIGHT,
    HYBRID_SPARSE_STRONG_THRESHOLD,
    HYBRID_SPARSE_WEIGHT,
    HYBRID_WEAK_DENSE_SPARSE_EMPHASIS,
    PROFILE_HYBRID_WEIGHTS,
    RERANK_AGREEMENT_BONUS_CAP,
    RERANK_AGREEMENT_MIN_SIGNAL,
)
from ai_stack.rag.rag_types import ContentClass, RetrievalDomain

PROFILE_VERSIONS = {
    "runtime_turn_support": "runtime_profile_v3_source_policy",
    "writers_review": "writers_profile_v3_source_policy",
    "improvement_eval": "improvement_profile_v3_source_policy",
    "research_eval": "research_profile_v1_source_policy",
}

SEMANTIC_CANON = {
    "argument": "conflict",
    "argue": "conflict",
    "argued": "conflict",
    "dispute": "conflict",
    "fight": "conflict",
    "fighting": "conflict",
    "chaos": "escalation",
    "chaotic": "escalation",
    "collapse": "escalation",
    "escalates": "escalation",
    "escalate": "escalation",
    "families": "family",
    "parents": "family",
    "dinner": "confrontation",
    "civility": "social_norm",
    "manners": "social_norm",
    "canon": "authoritative",
    "published": "authoritative",
    "tension": "conflict",
    "strained": "conflict",
}

SEMANTIC_EXPANSIONS = {
    "conflict": ("dispute", "argument", "fight"),
    "escalation": ("chaos", "collapse", "intensify"),
    "confrontation": ("dinner", "encounter"),
    "social_norm": ("civility", "manners"),
    "authoritative": ("canon", "published"),
}

PROFILE_CONTENT_BOOSTS: dict[str, dict[ContentClass, float]] = {
    "runtime_turn_support": {
        ContentClass.AUTHORED_MODULE: 1.4,
        ContentClass.RUNTIME_PROJECTION: 0.8,
        ContentClass.CHARACTER_PROFILE: 0.5,
        ContentClass.TRANSCRIPT: 0.2,
        ContentClass.POLICY_GUIDELINE: 0.6,
    },
    "writers_review": {
        ContentClass.AUTHORED_MODULE: 1.0,
        ContentClass.REVIEW_NOTE: 0.9,
        ContentClass.POLICY_GUIDELINE: 0.7,
        ContentClass.CHARACTER_PROFILE: 0.4,
        ContentClass.TRANSCRIPT: 0.2,
    },
    "improvement_eval": {
        ContentClass.EVALUATION_ARTIFACT: 1.2,
        ContentClass.REVIEW_NOTE: 0.6,
        ContentClass.TRANSCRIPT: 0.6,
        ContentClass.AUTHORED_MODULE: 0.6,
        ContentClass.POLICY_GUIDELINE: 0.4,
    },
    "research_eval": {
        ContentClass.AUTHORED_MODULE: 0.9,
        ContentClass.EVALUATION_ARTIFACT: 0.8,
        ContentClass.REVIEW_NOTE: 0.7,
        ContentClass.TRANSCRIPT: 0.6,
        ContentClass.POLICY_GUIDELINE: 0.6,
        ContentClass.CHARACTER_PROFILE: 0.5,
    },
}

PROFILE_CANONICAL_WEIGHT = {
    "runtime_turn_support": 0.8,
    "writers_review": 0.45,
    "improvement_eval": 0.3,
    "research_eval": 0.4,
}

DOMAIN_DEFAULT_PROFILE = {
    RetrievalDomain.RUNTIME: "runtime_turn_support",
    RetrievalDomain.WRITERS_ROOM: "writers_review",
    RetrievalDomain.IMPROVEMENT: "improvement_eval",
    RetrievalDomain.RESEARCH: "research_eval",
}


class _SparseVectorChunk(Protocol):
    """``_SparseVectorChunk`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    semantic_terms: dict[str, float]
    term_norm: float


def _raw_tokens(text: str) -> list[str]:
    """Describe what ``_raw_tokens`` does in one line (verb-led summary for
    this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        text: ``text`` (str); meaning follows the type and call sites.
    
    Returns:
        list[str]:
            Returns a value of type ``list[str]``; see the function body for structure, error paths, and sentinels.
    """
    return [token for token in re.findall(r"[a-z0-9_]+", text.lower()) if len(token) >= 3]


def _normalize_token(token: str) -> str:
    """``_normalize_token`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        token: ``token`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    normalized = token.strip().lower()
    if not normalized:
        return normalized
    if normalized in SEMANTIC_CANON:
        return SEMANTIC_CANON[normalized]
    for suffix in ("ing", "ed", "es", "s"):
        if normalized.endswith(suffix) and len(normalized) >= len(suffix) + 3:
            candidate = normalized[: -len(suffix)]
            if candidate in SEMANTIC_CANON:
                return SEMANTIC_CANON[candidate]
            normalized = candidate
            break
    return SEMANTIC_CANON.get(normalized, normalized)


def _build_semantic_terms(text: str) -> dict[str, float]:
    """``_build_semantic_terms`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        text: ``text`` (str); meaning follows the type and call sites.
    
    Returns:
        dict[str, float]:
            Returns a value of type ``dict[str, float]``; see the function body for structure, error paths, and sentinels.
    """
    terms: dict[str, float] = {}
    tokens = [_normalize_token(token) for token in _raw_tokens(text)]
    tokens = [token for token in tokens if len(token) >= 3]
    for token in tokens:
        terms[token] = terms.get(token, 0.0) + 1.0
        for related in SEMANTIC_EXPANSIONS.get(token, ()):
            terms[related] = terms.get(related, 0.0) + 0.35
    for left, right in zip(tokens, tokens[1:]):
        bigram = f"{left}_{right}"
        terms[bigram] = terms.get(bigram, 0.0) + 0.25
    return terms


def _apply_sparse_vector_weights(chunks: list[_SparseVectorChunk]) -> None:
    """Describe what ``_apply_sparse_vector_weights`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        chunks: ``chunks`` (list[_SparseVectorChunk]); meaning follows the type and call sites.
    """
    if not chunks:
        return
    document_frequency: dict[str, int] = {}
    for chunk in chunks:
        for term in chunk.semantic_terms.keys():
            document_frequency[term] = document_frequency.get(term, 0) + 1
    total_docs = float(len(chunks))
    for chunk in chunks:
        weighted_terms: dict[str, float] = {}
        for term, tf in chunk.semantic_terms.items():
            idf = 1.0 + math.log((1.0 + total_docs) / (1.0 + float(document_frequency.get(term, 0))))
            weighted_terms[term] = float(tf) * idf
        norm = math.sqrt(sum(weight * weight for weight in weighted_terms.values()))
        chunk.semantic_terms = weighted_terms
        chunk.term_norm = norm


def _cosine_similarity(query_terms: dict[str, float], query_norm: float, chunk: _SparseVectorChunk) -> float:
    """``_cosine_similarity`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        query_terms: ``query_terms`` (dict[str, float]); meaning follows the type and call sites.
        query_norm: ``query_norm`` (float); meaning follows the type and call sites.
        chunk: ``chunk`` (_SparseVectorChunk); meaning follows the type and call sites.
    
    Returns:
        float:
            Returns a value of type ``float``; see the function body for structure, error paths, and sentinels.
    """
    if query_norm <= 0 or chunk.term_norm <= 0:
        return 0.0
    dot = 0.0
    for term, query_weight in query_terms.items():
        dot += query_weight * chunk.semantic_terms.get(term, 0.0)
    if dot <= 0:
        return 0.0
    return dot / (query_norm * chunk.term_norm)


def _profile_hybrid_weights(profile_name: str, domain: RetrievalDomain) -> tuple[float, float]:
    """``_profile_hybrid_weights`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        profile_name: ``profile_name`` (str); meaning follows the type and call sites.
        domain: ``domain`` (RetrievalDomain); meaning follows the type and call sites.
    
    Returns:
        tuple[float, float]:
            Returns a value of type ``tuple[float, float]``; see the function body for structure, error paths, and sentinels.
    """
    default_prof = DOMAIN_DEFAULT_PROFILE[domain]
    key = profile_name or default_prof
    return PROFILE_HYBRID_WEIGHTS.get(key, PROFILE_HYBRID_WEIGHTS.get(default_prof, (HYBRID_DENSE_WEIGHT, HYBRID_SPARSE_WEIGHT)))


def _hybrid_core_initial(
    dense_sim: float,
    sparse_sim: float,
    *,
    use_hybrid: bool,
    w_dense: float,
    w_sparse: float,
) -> float:
    """Initial hybrid core: weighted blend plus an explicit weak-dense
    rescue rule.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        dense_sim: ``dense_sim`` (float); meaning follows the type and call sites.
        sparse_sim: ``sparse_sim`` (float); meaning follows the type and call sites.
        use_hybrid: ``use_hybrid`` (bool); meaning follows the type and call sites.
        w_dense: ``w_dense`` (float); meaning follows the type and call sites.
        w_sparse: ``w_sparse`` (float); meaning follows the type and call sites.
    
    Returns:
        float:
            Returns a value of type ``float``; see the function body for structure, error paths, and sentinels.
    """
    if not use_hybrid:
        return sparse_sim
    linear = w_dense * dense_sim + w_sparse * sparse_sim
    if dense_sim < HYBRID_DENSE_WEAK_THRESHOLD and sparse_sim > HYBRID_SPARSE_STRONG_THRESHOLD:
        rescue = HYBRID_WEAK_DENSE_SPARSE_EMPHASIS * sparse_sim + (1.0 - HYBRID_WEAK_DENSE_SPARSE_EMPHASIS) * dense_sim
        return max(linear, rescue)
    return linear


def _rerank_agreement_bonus(dense_sim: float, sparse_sim: float, *, use_hybrid: bool) -> float:
    """Single-stage dense/sparse agreement signal (rerank only).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        dense_sim: ``dense_sim`` (float); meaning follows the type and call sites.
        sparse_sim: ``sparse_sim`` (float); meaning follows the type and call sites.
        use_hybrid: ``use_hybrid`` (bool); meaning follows the type and call sites.
    
    Returns:
        float:
            Returns a value of type ``float``; see the function body for structure, error paths, and sentinels.
    """
    if not use_hybrid:
        return 0.0
    if dense_sim < RERANK_AGREEMENT_MIN_SIGNAL or sparse_sim < RERANK_AGREEMENT_MIN_SIGNAL:
        return 0.0
    return RERANK_AGREEMENT_BONUS_CAP * min(dense_sim, sparse_sim)


def _normalize_for_dup(text: str) -> str:
    """``_normalize_for_dup`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        text: ``text`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    return " ".join(text.lower().split())


def _char_trigram_jaccard(a: str, b: str) -> float:
    """``_char_trigram_jaccard`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        a: ``a`` (str); meaning follows the type and call sites.
        b: ``b`` (str); meaning follows the type and call sites.
    
    Returns:
        float:
            Returns a value of type ``float``; see the function body for structure, error paths, and sentinels.
    """
    def trigrams(s: str) -> set[str]:
        """3-gram set over normalized *s* (see ``_normalize_for_dup``).
        
        Args:
            s: Input string (may be shorter than three characters).
        
        Returns:
            set[str]:
                Shingles; short inputs collapse to ``{s}`` or ``set()``.
        """

        s = _normalize_for_dup(s)
        if len(s) < 3:
            return {s} if s else set()
        return {s[i : i + 3] for i in range(len(s) - 2)}

    ta, tb = trigrams(a), trigrams(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0
