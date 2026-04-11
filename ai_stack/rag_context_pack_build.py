"""Build ``ContextPack`` from ``RetrievalResult`` (orchestrator; DS-009 + optional submodules)."""

from __future__ import annotations

from ai_stack.rag_constants import RETRIEVAL_PIPELINE_VERSION, RETRIEVAL_POLICY_VERSION
from ai_stack.rag_context_pack_compact_body import build_compact_lines_and_sources, hits_ordered_for_profile
from ai_stack.rag_context_pack_result_tail import (
    context_pack_tail_fields,
    empty_context_pack,
    pack_index_trace_tuple,
)
from ai_stack.rag_context_pack_trace_footer import append_trace_and_governance_footer
from ai_stack.rag_retrieval_dtos import ContextPack, RetrievalResult
from ai_stack.rag_retrieval_lexical import DOMAIN_DEFAULT_PROFILE


def _resolved_profile(result: RetrievalResult) -> str:
    return result.request.profile or DOMAIN_DEFAULT_PROFILE[result.request.domain]


def assemble_context_pack(result: RetrievalResult) -> ContextPack:
    """Turn a retrieval result into a ``ContextPack`` (same contract as ``ContextPackAssembler.assemble``)."""
    trace = pack_index_trace_tuple(result)
    if not result.hits:
        return empty_context_pack(result)

    profile = _resolved_profile(result)
    ordered = hits_ordered_for_profile(result, profile)
    lines, sources = build_compact_lines_and_sources(result, profile, ordered)
    append_trace_and_governance_footer(result, profile, lines, sources)

    return ContextPack(
        summary=(
            f"{len(result.hits)} evidence chunk(s) | domain={result.request.domain.value} | profile={profile} "
            f"| pipeline={RETRIEVAL_PIPELINE_VERSION} | policy={RETRIEVAL_POLICY_VERSION}"
        ),
        compact_context="\n".join(lines),
        sources=sources,
        hit_count=len(result.hits),
        profile=result.request.profile,
        domain=result.request.domain.value,
        status=result.status.value,
        **context_pack_tail_fields(result, trace),
    )
