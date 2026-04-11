"""Context fingerprint and LangChain preview helpers (DS-002)."""

from __future__ import annotations

import hashlib
from typing import Any

from langchain_core.documents import Document


def _context_fingerprint(context_text: str, *, max_bytes: int = 2048) -> str:
    sample = context_text.encode("utf-8", errors="replace")[:max_bytes]
    return hashlib.sha256(sample).hexdigest()[:16]


def _langchain_preview_documents_from_context_pack(
    retrieval_inner: dict[str, Any],
    *,
    max_chunks: int = 3,
) -> tuple[list[Document], str]:
    """Build LangChain documents from the primary ``wos.context_pack.build`` payload (no second retrieve)."""
    sources = retrieval_inner.get("sources") if isinstance(retrieval_inner, dict) else None
    if not isinstance(sources, list):
        return [], "primary_context_pack_empty"
    docs: list[Document] = []
    for row in sources[:max_chunks]:
        if not isinstance(row, dict):
            continue
        path = str(row.get("source_path") or "")
        snippet = str(row.get("snippet") or "")
        if not path and not snippet:
            continue
        docs.append(
            Document(
                page_content=snippet or "(no snippet)",
                metadata={
                    "chunk_id": row.get("chunk_id", ""),
                    "source_path": path,
                    "source_version": row.get("source_version", ""),
                    "domain": str(retrieval_inner.get("domain") or ""),
                    "content_class": row.get("content_class", ""),
                    "score": row.get("score", ""),
                    "index_version": retrieval_inner.get("index_version", ""),
                    "corpus_fingerprint": retrieval_inner.get("corpus_fingerprint", ""),
                },
            )
        )
    label = "primary_context_pack" if docs else "primary_context_pack_no_hits"
    return docs, label
