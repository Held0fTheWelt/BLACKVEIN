"""Shared ``ContextPack`` tail fields and empty-hit pack (DS-009 optional)."""

from __future__ import annotations

from ai_stack.rag_retrieval_dtos import ContextPack, RetrievalResult


def pack_index_trace_tuple(result: RetrievalResult) -> tuple[str, str, str]:
    """``pack_index_trace_tuple`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        result: ``result`` (RetrievalResult); meaning follows the type and call sites.
    
    Returns:
        tuple[str, str, str]:
            Returns a value of type ``tuple[str, str, str]``; see the function body for structure, error paths, and sentinels.
    """
    return (result.index_version, result.corpus_fingerprint, result.storage_path)


def context_pack_tail_fields(result: RetrievalResult, trace: tuple[str, str, str]) -> dict:
    """Describe what ``context_pack_tail_fields`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        result: ``result`` (RetrievalResult); meaning follows the type and call sites.
        trace: ``trace`` (tuple[str, str, str]); meaning follows the type and call sites.
    
    Returns:
        dict:
            Returns a value of type ``dict``; see the function body for structure, error paths, and sentinels.
    """
    return {
        "ranking_notes": result.ranking_notes,
        "index_version": trace[0],
        "corpus_fingerprint": trace[1],
        "storage_path": trace[2],
        "retrieval_route": result.retrieval_route,
        "embedding_model_id": result.embedding_model_id,
        "degradation_mode": result.degradation_mode,
        "dense_index_build_action": result.dense_index_build_action,
        "dense_rebuild_reason": result.dense_rebuild_reason,
        "dense_artifact_validity": result.dense_artifact_validity,
        "embedding_reason_codes": result.embedding_reason_codes,
        "embedding_index_version": result.embedding_index_version,
        "embedding_cache_dir_identity": result.embedding_cache_dir_identity,
        "retrieval_authority": dict(result.retrieval_authority or {}),
    }


def empty_context_pack(result: RetrievalResult) -> ContextPack:
    """``empty_context_pack`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        result: ``result`` (RetrievalResult); meaning follows the type and call sites.
    
    Returns:
        ContextPack:
            Returns a value of type ``ContextPack``; see the function body for structure, error paths, and sentinels.
    """
    trace = pack_index_trace_tuple(result)
    return ContextPack(
        summary="No evidence chunks retrieved for this query.",
        compact_context="",
        sources=[],
        hit_count=0,
        profile=result.request.profile,
        domain=result.request.domain.value,
        status=result.status.value,
        **context_pack_tail_fields(result, trace),
    )
