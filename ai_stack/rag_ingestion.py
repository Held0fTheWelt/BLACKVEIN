"""
Corpus ingestion: source discovery, chunking, and fingerprinting (DS-003
stage 9).
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from ai_stack.rag_constants import INDEX_VERSION
from ai_stack.rag_retrieval_lexical import (
    PROFILE_VERSIONS,
    _apply_sparse_vector_weights,
    _build_semantic_terms,
)
from ai_stack.rag_types import ContentClass
from ai_stack.rag_corpus import CorpusChunk, InMemoryRetrievalCorpus

_MODULE_PATH = re.compile(r"(?i)^content/modules/([^/]+)/")
_PUBLISHED_MODULE_PATH = re.compile(r"(?i)^content/published/([^/]+)/")


def _world_engine_var_runs_json_files(repo_root: Path) -> list[Path]:
    """JSON run logs under ``world-engine/**/var/runs/``.

    A literal ``Path.glob("world-engine/**/var/runs/**/*.json")`` is not reliable on
    all supported Python versions when ``**`` sits between fixed segments; walk the
    tree and match ``var`` / ``runs`` path segments instead.
    """
    we = repo_root / "world-engine"
    if not we.is_dir():
        return []
    found: list[Path] = []
    for path in we.rglob("*.json"):
        if not path.is_file():
            continue
        parts = tuple(p.lower() for p in path.parts)
        for i in range(len(parts) - 1):
            if parts[i] == "var" and parts[i + 1] == "runs":
                found.append(path)
                break
    return found


def _infer_module_id(repo_root: Path, file: Path) -> str | None:
    """Resolve module_id from conventional paths; flat
    ``content/<stem>.md`` uses file stem.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        repo_root: ``repo_root`` (Path); meaning follows the type and call sites.
        file: ``file`` (Path); meaning follows the type and call sites.
    
    Returns:
        str | None:
            Returns a value of type ``str | None``; see the function body for structure, error paths, and sentinels.
    """
    try:
        rel = file.relative_to(repo_root).as_posix()
    except ValueError:
        return None
    m = _MODULE_PATH.match(rel)
    if m:
        return m.group(1)
    m = _PUBLISHED_MODULE_PATH.match(rel)
    if m:
        return m.group(1)
    parts = Path(rel).parts
    if len(parts) == 2 and parts[0].lower() == "content":
        name = parts[1]
        stem = Path(name).stem
        if stem and stem.lower() not in {"modules", "published"}:
            return stem
    return None


def _detect_content_class(path: Path) -> ContentClass | None:
    """``_detect_content_class`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        path: ``path`` (Path); meaning follows the type and call sites.
    
    Returns:
        ContentClass | None:
            Returns a value of type ``ContentClass | None``; see the function body for structure, error paths, and sentinels.
    """
    normalized = str(path).replace("\\", "/").lower()
    if "/content/" in normalized:
        return ContentClass.AUTHORED_MODULE
    if "/var/runs/" in normalized:
        return ContentClass.TRANSCRIPT
    if "/docs/technical/" in normalized or "/docs/architecture/" in normalized:
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
    """``RagIngestionPipeline`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    def __init__(self, *, chunk_size: int = 600, overlap: int = 120, max_sources: int = 250) -> None:
        """``__init__`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            chunk_size: ``chunk_size`` (int); meaning follows the type and call sites.
            overlap: ``overlap`` (int); meaning follows the type and call sites.
            max_sources: ``max_sources`` (int); meaning follows the type and call sites.
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.max_sources = max_sources

    def _source_patterns(self) -> list[str]:
        """``_source_patterns`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            list[str]:
                Returns a value of type ``list[str]``; see the function body for structure, error paths, and sentinels.
        """
        return [
            "content/**/*.md",
            "content/**/*.json",
            "content/**/*.yml",
            "content/**/*.yaml",
            "docs/technical/**/*.md",
            "docs/architecture/**/*.md",
            "docs/reports/**/*.md",
        ]

    def _select_sources(self, repo_root: Path) -> list[Path]:
        """``_select_sources`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            repo_root: ``repo_root`` (Path); meaning follows the type and call sites.
        
        Returns:
            list[Path]:
                Returns a value of type ``list[Path]``; see the function body for structure, error paths, and sentinels.
        """
        files: list[Path] = []
        for pattern in self._source_patterns():
            files.extend(repo_root.glob(pattern))
        files.extend(_world_engine_var_runs_json_files(repo_root))
        return sorted({file for file in files if file.is_file()})[: self.max_sources]

    def compute_source_fingerprint(self, repo_root: Path) -> str:
        """Describe what ``compute_source_fingerprint`` does in one line
        (verb-led summary for this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            repo_root: ``repo_root`` (Path); meaning follows the type and call sites.
        
        Returns:
            str:
                Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
        """
        selected = self._select_sources(repo_root)
        return self._fingerprint_for_selected(repo_root, selected)

    @staticmethod
    def _fingerprint_for_selected(repo_root: Path, selected: list[Path]) -> str:
        """Describe what ``_fingerprint_for_selected`` does in one line
        (verb-led summary for this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            repo_root: ``repo_root`` (Path); meaning follows the type and call sites.
            selected: ``selected`` (list[Path]); meaning follows the type and call sites.
        
        Returns:
            str:
                Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
        """
        digest = hashlib.sha256()
        for file in selected:
            rel = file.relative_to(repo_root).as_posix()
            stat = file.stat()
            digest.update(f"{rel}:{stat.st_size}:{stat.st_mtime_ns}".encode("utf-8"))
        return digest.hexdigest()

    @staticmethod
    def _canonical_priority(path: Path, content_class: ContentClass) -> int:
        """``_canonical_priority`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            path: ``path`` (Path); meaning follows the type and call sites.
            content_class: ``content_class`` (ContentClass); meaning follows the type and call sites.
        
        Returns:
            int:
                Returns a value of type ``int``; see the function body for structure, error paths, and sentinels.
        """
        normalized = path.as_posix().lower()
        if content_class == ContentClass.AUTHORED_MODULE:
            if "/content/published/" in normalized:
                return 4
            if "/content/modules/" in normalized:
                return 3
            return 2
        if "/content/published/" in normalized or "canonical" in normalized:
            return 2
        if content_class == ContentClass.POLICY_GUIDELINE:
            return 1
        return 0

    def build_corpus(self, repo_root: Path, *, source_fingerprint: str | None = None) -> InMemoryRetrievalCorpus:
        """``build_corpus`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            repo_root: ``repo_root`` (Path); meaning follows the type and call sites.
            source_fingerprint: ``source_fingerprint`` (str | None); meaning follows the type and call sites.
        
        Returns:
            InMemoryRetrievalCorpus:
                Returns a value of type ``InMemoryRetrievalCorpus``; see the function body for structure, error paths, and sentinels.
        """
        selected = self._select_sources(repo_root)
        chunks: list[CorpusChunk] = []
        for file in selected:
            content_class = _detect_content_class(file)
            if content_class is None:
                continue
            text = file.read_text(encoding="utf-8", errors="ignore").strip()
            if not text:
                continue
            source_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            source_version = f"sha256:{source_hash[:16]}"
            module_id = _infer_module_id(repo_root, file)
            canonical_priority = self._canonical_priority(file, content_class)
            for index, chunk_text in enumerate(self._chunk_text(text)):
                if not chunk_text.strip():
                    continue
                rel_path = file.relative_to(repo_root).as_posix()
                chunks.append(
                    CorpusChunk(
                        chunk_id=f"{rel_path}@{source_version}::chunk_{index}",
                        source_path=rel_path,
                        source_name=file.name,
                        content_class=content_class,
                        text=chunk_text.strip(),
                        module_id=module_id,
                        source_version=source_version,
                        source_hash=source_hash,
                        canonical_priority=canonical_priority,
                        semantic_terms=_build_semantic_terms(chunk_text),
                    )
                )
        _apply_sparse_vector_weights(chunks)
        corpus_fingerprint = source_fingerprint or self._fingerprint_for_selected(repo_root, selected)
        return InMemoryRetrievalCorpus(
            chunks=chunks,
            built_at=datetime.now(timezone.utc).isoformat(),
            source_count=len(selected),
            index_version=INDEX_VERSION,
            corpus_fingerprint=corpus_fingerprint,
            storage_path="",
            profile_versions=dict(PROFILE_VERSIONS),
        )

    def _chunk_text(self, text: str) -> list[str]:
        """``_chunk_text`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            text: ``text`` (str); meaning follows the type and call sites.
        
        Returns:
            list[str]:
                Returns a value of type ``list[str]``; see the function body for structure, error paths, and sentinels.
        """
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
