"""
Handler factories for wos.context_pack / transcript / review_bundle
capabilities (Feinsplit).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ai_stack.rag import ContextPackAssembler, ContextRetriever


def build_context_pack_handler(
    retriever: "ContextRetriever",
    assembler: "ContextPackAssembler",
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Describe what ``build_context_pack_handler`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        retriever: ``retriever`` ('ContextRetriever'); meaning follows the type and call sites.
        assembler: ``assembler`` ('ContextPackAssembler'); meaning follows the type and call sites.
    
    Returns:
        Callable[[dict[str, Any]], dict[str, Any]]:
            Returns a value of type ``Callable[[dict[str, Any]], dict[str,
            Any]]``; see the function body for structure, error paths, and sentinels.
    """
    def context_pack_handler(payload: dict[str, Any]) -> dict[str, Any]:
        from ai_stack.rag_constants import RETRIEVAL_POLICY_VERSION
        from ai_stack.rag_retrieval_dtos import RetrievalRequest, filter_retrieval_result_by_min_score
        from ai_stack.rag_types import RetrievalDomain

        domain = RetrievalDomain(payload.get("domain", RetrievalDomain.RUNTIME.value))
        request = RetrievalRequest(
            domain=domain,
            profile=payload["profile"],
            query=payload["query"],
            module_id=payload.get("module_id"),
            scene_id=payload.get("scene_id"),
            max_chunks=int(payload.get("max_chunks", 4)),
            use_sparse_only=bool(payload.get("use_sparse_only", False)),
        )
        retrieval_result = retriever.retrieve(request)
        retrieval_result, _removed_count = filter_retrieval_result_by_min_score(
            retrieval_result,
            payload.get("retrieval_min_score"),
        )
        context_pack = assembler.assemble(retrieval_result)
        top_score = ""
        if context_pack.sources:
            top_score = str(context_pack.sources[0].get("score", ""))

        return {
            "retrieval": {
                "domain": context_pack.domain,
                "profile": context_pack.profile,
                "status": context_pack.status,
                "hit_count": context_pack.hit_count,
                "sources": context_pack.sources,
                "ranking_notes": context_pack.ranking_notes,
                "index_version": context_pack.index_version,
                "corpus_fingerprint": context_pack.corpus_fingerprint,
                "storage_path": context_pack.storage_path,
                "retrieval_route": context_pack.retrieval_route,
                "embedding_model_id": context_pack.embedding_model_id,
                "top_hit_score": top_score,
                "degradation_mode": context_pack.degradation_mode,
                "dense_index_build_action": context_pack.dense_index_build_action,
                "dense_rebuild_reason": context_pack.dense_rebuild_reason,
                "dense_artifact_validity": context_pack.dense_artifact_validity,
                "embedding_reason_codes": list(context_pack.embedding_reason_codes),
                "embedding_index_version": context_pack.embedding_index_version,
                "embedding_cache_dir_identity": context_pack.embedding_cache_dir_identity,
                "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
            },
            "context_text": context_pack.compact_context,
        }

    return context_pack_handler


def build_transcript_read_handler(repo_root: Path) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Describe what ``build_transcript_read_handler`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        repo_root: ``repo_root`` (Path); meaning follows the type and call sites.
    
    Returns:
        Callable[[dict[str, Any]], dict[str, Any]]:
            Returns a value of type ``Callable[[dict[str, Any]], dict[str,
            Any]]``; see the function body for structure, error paths, and sentinels.
    """
    from ai_stack.capabilities import CapabilityInvocationError

    def transcript_read_handler(payload: dict[str, Any]) -> dict[str, Any]:
        run_id = payload["run_id"]
        run_file = repo_root / "world-engine" / "app" / "var" / "runs" / f"{run_id}.json"
        if not run_file.exists():
            raise CapabilityInvocationError("wos.transcript.read", "run_not_found")
        return {
            "run_id": run_id,
            "content": run_file.read_text(encoding="utf-8", errors="ignore")[:10000],
        }

    return transcript_read_handler


def build_review_bundle_handler() -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Describe what ``build_review_bundle_handler`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        Callable[[dict[str, Any]], dict[str, Any]]:
            Returns a value of type ``Callable[[dict[str, Any]], dict[str,
            Any]]``; see the function body for structure, error paths, and sentinels.
    """
    from uuid import uuid4

    def review_bundle_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "bundle_id": uuid4().hex,
            "module_id": payload["module_id"],
            "summary": payload.get("summary", ""),
            "recommendations": payload.get("recommendations", []),
            "evidence_sources": payload.get("evidence_sources", []),
            "status": "recommendation_only",
        }

    return review_bundle_handler
