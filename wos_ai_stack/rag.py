from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
import re


class RetrievalDomain(StrEnum):
    RUNTIME = "runtime"
    WRITERS_ROOM = "writers_room"
    IMPROVEMENT = "improvement"


class RetrievalStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    FALLBACK = "fallback"


class ContentClass(StrEnum):
    AUTHORED_MODULE = "authored_module"
    RUNTIME_PROJECTION = "runtime_projection"
    CHARACTER_PROFILE = "character_profile"
    TRANSCRIPT = "transcript"
    REVIEW_NOTE = "review_note"
    EVALUATION_ARTIFACT = "evaluation_artifact"
    POLICY_GUIDELINE = "policy_guideline"


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
}


class RetrievalDomainError(ValueError):
    pass


@dataclass(slots=True)
class CorpusChunk:
    chunk_id: str
    source_path: str
    source_name: str
    content_class: ContentClass
    text: str
    module_id: str | None = None


@dataclass(slots=True)
class InMemoryRetrievalCorpus:
    chunks: list[CorpusChunk]
    built_at: str
    source_count: int

    @classmethod
    def empty(cls) -> "InMemoryRetrievalCorpus":
        return cls(chunks=[], built_at=datetime.now(timezone.utc).isoformat(), source_count=0)


@dataclass(slots=True)
class RetrievalRequest:
    domain: RetrievalDomain
    profile: str
    query: str
    module_id: str | None = None
    scene_id: str | None = None
    max_chunks: int = 4


@dataclass(slots=True)
class RetrievalHit:
    chunk_id: str
    source_path: str
    source_name: str
    content_class: str
    score: float
    snippet: str
    selection_reason: str


@dataclass(slots=True)
class RetrievalResult:
    request: RetrievalRequest
    status: RetrievalStatus
    hits: list[RetrievalHit]
    ranking_notes: list[str]
    error: str | None = None


@dataclass(slots=True)
class ContextPack:
    summary: str
    compact_context: str
    sources: list[dict[str, str]]
    hit_count: int
    profile: str
    domain: str
    status: str
    ranking_notes: list[str]


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9_]+", text.lower()) if len(token) >= 3}


def _detect_content_class(path: Path) -> ContentClass | None:
    normalized = str(path).replace("\\", "/").lower()
    if "/content/" in normalized:
        return ContentClass.AUTHORED_MODULE
    if "/var/runs/" in normalized:
        return ContentClass.TRANSCRIPT
    if "/docs/architecture/" in normalized:
        return ContentClass.POLICY_GUIDELINE
    if "/docs/reports/" in normalized:
        filename = path.name.lower()
        if "eval" in filename or "acceptance" in filename:
            return ContentClass.EVALUATION_ARTIFACT
        return ContentClass.REVIEW_NOTE
    if "projection" in normalized:
        return ContentClass.RUNTIME_PROJECTION
    if "character" in normalized:
        return ContentClass.CHARACTER_PROFILE
    return None


class RagIngestionPipeline:
    def __init__(self, *, chunk_size: int = 600, overlap: int = 120, max_sources: int = 250) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.max_sources = max_sources

    def build_corpus(self, repo_root: Path) -> InMemoryRetrievalCorpus:
        patterns = [
            "content/**/*.md",
            "content/**/*.json",
            "content/**/*.yml",
            "content/**/*.yaml",
            "docs/architecture/**/*.md",
            "docs/reports/**/*.md",
            "world-engine/app/var/runs/**/*.json",
        ]
        files: list[Path] = []
        for pattern in patterns:
            files.extend(repo_root.glob(pattern))
        selected = sorted({file for file in files if file.is_file()})[: self.max_sources]
        chunks: list[CorpusChunk] = []
        for file in selected:
            content_class = _detect_content_class(file)
            if content_class is None:
                continue
            text = file.read_text(encoding="utf-8", errors="ignore").strip()
            if not text:
                continue
            module_id = "god_of_carnage" if "god_of_carnage" in text.lower() or "god_of_carnage" in str(file) else None
            for index, chunk_text in enumerate(self._chunk_text(text)):
                if not chunk_text.strip():
                    continue
                rel_path = file.relative_to(repo_root).as_posix()
                chunks.append(
                    CorpusChunk(
                        chunk_id=f"{rel_path}::chunk_{index}",
                        source_path=rel_path,
                        source_name=file.name,
                        content_class=content_class,
                        text=chunk_text.strip(),
                        module_id=module_id,
                    )
                )
        return InMemoryRetrievalCorpus(
            chunks=chunks,
            built_at=datetime.now(timezone.utc).isoformat(),
            source_count=len(selected),
        )

    def _chunk_text(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]
        chunks: list[str] = []
        start = 0
        step = max(1, self.chunk_size - self.overlap)
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += step
        return chunks


class ContextRetriever:
    def __init__(self, corpus: InMemoryRetrievalCorpus) -> None:
        self.corpus = corpus

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        if request.domain not in DOMAIN_CONTENT_ACCESS:
            raise RetrievalDomainError(f"Unknown retrieval domain: {request.domain}")
        if not self.corpus.chunks:
            return RetrievalResult(
                request=request,
                status=RetrievalStatus.DEGRADED,
                hits=[],
                ranking_notes=["retrieval_corpus_empty"],
                error="retrieval_corpus_empty",
            )

        allowed_classes = DOMAIN_CONTENT_ACCESS[request.domain]
        tokens = _tokenize(request.query)
        ranked: list[tuple[float, CorpusChunk, str]] = []
        for chunk in self.corpus.chunks:
            if chunk.content_class not in allowed_classes:
                continue
            chunk_tokens = _tokenize(chunk.text)
            overlap = tokens.intersection(chunk_tokens)
            score = float(len(overlap))
            reasons: list[str] = []
            if overlap:
                reasons.append(f"token_overlap={len(overlap)}")
            if request.module_id and chunk.module_id and request.module_id == chunk.module_id:
                score += 2.0
                reasons.append("module_match_boost=2")
            if request.scene_id and request.scene_id in chunk.text:
                score += 1.5
                reasons.append("scene_hint_boost=1.5")
            if score <= 0:
                continue
            ranked.append((score, chunk, "; ".join(reasons) or "lexical_match"))

        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = ranked[: max(1, request.max_chunks)]
        hits = [
            RetrievalHit(
                chunk_id=chunk.chunk_id,
                source_path=chunk.source_path,
                source_name=chunk.source_name,
                content_class=chunk.content_class.value,
                score=score,
                snippet=chunk.text[:400],
                selection_reason=reason,
            )
            for score, chunk, reason in selected
        ]
        if not hits:
            return RetrievalResult(
                request=request,
                status=RetrievalStatus.FALLBACK,
                hits=[],
                ranking_notes=["no_ranked_hits_for_query"],
                error="no_ranked_hits",
            )
        ranking_notes = [f"{hit.source_path} score={hit.score:.2f} ({hit.selection_reason})" for hit in hits]
        return RetrievalResult(
            request=request,
            status=RetrievalStatus.OK,
            hits=hits,
            ranking_notes=ranking_notes,
            error=None,
        )


class ContextPackAssembler:
    def assemble(self, result: RetrievalResult) -> ContextPack:
        if not result.hits:
            return ContextPack(
                summary="No retrieval context available.",
                compact_context="",
                sources=[],
                hit_count=0,
                profile=result.request.profile,
                domain=result.request.domain.value,
                status=result.status.value,
                ranking_notes=result.ranking_notes,
            )
        lines = ["Retrieved context (ranked):"]
        sources: list[dict[str, str]] = []
        for index, hit in enumerate(result.hits, start=1):
            lines.append(f"{index}. [{hit.source_name}] {hit.snippet}")
            sources.append(
                {
                    "source_path": hit.source_path,
                    "content_class": hit.content_class,
                    "selection_reason": hit.selection_reason,
                }
            )
        return ContextPack(
            summary=f"Retrieved {len(result.hits)} chunks for profile={result.request.profile}.",
            compact_context="\n".join(lines),
            sources=sources,
            hit_count=len(result.hits),
            profile=result.request.profile,
            domain=result.request.domain.value,
            status=result.status.value,
            ranking_notes=result.ranking_notes,
        )


def build_runtime_retriever(repo_root: Path) -> tuple[ContextRetriever, ContextPackAssembler, InMemoryRetrievalCorpus]:
    corpus = RagIngestionPipeline().build_corpus(repo_root)
    return ContextRetriever(corpus), ContextPackAssembler(), corpus
