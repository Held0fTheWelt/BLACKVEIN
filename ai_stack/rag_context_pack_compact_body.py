"""Ordered hits, snippet trim, and ``compact_context`` body lines + ``sources`` list (DS-009 optional)."""

from __future__ import annotations

from ai_stack.rag_constants import RETRIEVAL_PIPELINE_VERSION, RETRIEVAL_POLICY_VERSION
from ai_stack.rag_context_pack_section_titles import section_title_for_pack_role
from ai_stack.rag_retrieval_dtos import RetrievalHit, RetrievalResult
from ai_stack.rag_retrieval_policy_pool import _pack_sort_key

SNIPPET_HARD_MAX = 320


def trim_snippet_for_compact(snippet: str) -> str:
    s = snippet.strip()
    if len(s) > SNIPPET_HARD_MAX:
        return s[: SNIPPET_HARD_MAX - 3].rstrip() + "..."
    return s


def hits_ordered_for_profile(result: RetrievalResult, profile: str) -> list[RetrievalHit]:
    return sorted(result.hits, key=lambda h: _pack_sort_key(h, profile))


def build_compact_lines_and_sources(
    result: RetrievalResult,
    profile: str,
    ordered_hits: list[RetrievalHit],
) -> tuple[list[str], list[dict[str, str]]]:
    lines: list[str] = [
        (
            f"Evidence pack — domain={result.request.domain.value}, profile={profile}, "
            f"pipeline={RETRIEVAL_PIPELINE_VERSION}, policy={RETRIEVAL_POLICY_VERSION}:"
        ),
    ]
    sources: list[dict[str, str]] = []
    current_section: str | None = None
    ordinal = 0
    for hit in ordered_hits:
        role = hit.pack_role or "supporting_context"
        title = section_title_for_pack_role(profile, role)
        if title and title != current_section:
            current_section = title
            lines.append(f"--- {title} ---")
        ordinal += 1
        snippet = trim_snippet_for_compact(hit.snippet)
        lane = hit.source_evidence_lane or "unknown"
        vis = hit.source_visibility_class or "unknown"
        lines.append(
            f"{ordinal}. [{hit.source_name}] role={role} lane={lane} visibility={vis} {snippet}"
        )
        sources.append(
            {
                "chunk_id": hit.chunk_id,
                "source_path": hit.source_path,
                "snippet": snippet,
                "content_class": hit.content_class,
                "selection_reason": hit.selection_reason,
                "source_version": hit.source_version,
                "score": f"{hit.score:.4f}",
                "pack_role": hit.pack_role,
                "why_selected": hit.why_selected,
                "source_evidence_lane": hit.source_evidence_lane,
                "source_visibility_class": hit.source_visibility_class,
                "policy_note": hit.policy_note,
                "profile_policy_influence": hit.profile_policy_influence,
            }
        )
    return lines, sources
