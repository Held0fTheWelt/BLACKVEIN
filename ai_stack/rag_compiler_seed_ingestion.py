"""
Merge backend ``retrieval_corpus_seed`` projections into the runtime RAG corpus.

Compiler seeds are authoritative structured chunks (canonical steps, entities,
knowledge surfaces). Raw module YAML file ingestion is skipped for modules whose
seeds loaded successfully to avoid duplicate noisy retrieval.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from ai_stack.rag_corpus import CorpusChunk
from ai_stack.rag_retrieval_lexical import _build_semantic_terms
from ai_stack.rag_types import ContentClass

_COMPILED_CHUNK_PREFIX = "compiled:"
_COMPILED_SOURCE_VERSION_PREFIX = "compiled_seed:"


def _ensure_backend_on_path(repo_root: Path) -> Path:
    backend_root = (repo_root / "backend").resolve()
    backend_str = str(backend_root)
    if backend_str not in sys.path:
        sys.path.insert(0, backend_str)
    return backend_root


def discover_compilable_module_ids(repo_root: Path) -> list[str]:
    """Module directory names that contain a ``module.yaml`` manifest."""
    modules_dir = repo_root / "content" / "modules"
    if not modules_dir.is_dir():
        return []
    module_ids: list[str] = []
    for child in sorted(modules_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue
        if (child / "module.yaml").is_file():
            module_ids.append(child.name)
    return module_ids


def module_tree_source_prefix(module_id: str) -> str:
    return f"content/modules/{module_id}/"


def _compiled_canonical_priority(metadata: dict[str, object]) -> int:
    if metadata.get("authority") == "module_canonical":
        return 5
    return 4


def retrieval_seed_to_corpus_chunk(
    *,
    module_id: str,
    module_version: str,
    chunk_id: str,
    kind: str,
    text: str,
    metadata: dict[str, object],
) -> CorpusChunk | None:
    body = text.strip()
    if not body:
        return None
    source_path = str(metadata.get("source_path") or "").strip()
    if not source_path:
        source_path = f"content/modules/{module_id}/compiled/{kind}/{chunk_id}"
    source_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    source_version = f"{_COMPILED_SOURCE_VERSION_PREFIX}{module_version}:{source_hash[:16]}"
    resolved_module_id = str(metadata.get("module_id") or module_id).strip() or module_id
    return CorpusChunk(
        chunk_id=f"{_COMPILED_CHUNK_PREFIX}{module_id}:{chunk_id}",
        source_path=source_path,
        source_name=Path(source_path).name or kind,
        content_class=ContentClass.RUNTIME_PROJECTION,
        text=body,
        module_id=resolved_module_id,
        source_version=source_version,
        source_hash=source_hash,
        canonical_priority=_compiled_canonical_priority(metadata),
        semantic_terms=_build_semantic_terms(body),
    )


def load_compiler_seed_chunks(
    repo_root: Path,
) -> tuple[list[CorpusChunk], set[str]]:
    """Compile each content module and convert ``retrieval_corpus_seed`` chunks."""
    module_ids = discover_compilable_module_ids(repo_root)
    if not module_ids:
        return [], set()

    try:
        _ensure_backend_on_path(repo_root)
        from app.content.compiler import compile_module
        from app.content.module_exceptions import ModuleLoadError
    except ImportError:
        return [], set()

    chunks: list[CorpusChunk] = []
    compiled_module_ids: set[str] = set()
    modules_root = repo_root / "content" / "modules"

    for module_id in module_ids:
        try:
            output = compile_module(module_id, root_path=modules_root)
        except ModuleLoadError:
            continue
        except Exception:
            continue
        seed = output.retrieval_corpus_seed
        module_chunks: list[CorpusChunk] = []
        for row in seed.chunks:
            corpus_chunk = retrieval_seed_to_corpus_chunk(
                module_id=module_id,
                module_version=seed.module_version,
                chunk_id=row.chunk_id,
                kind=row.kind,
                text=row.text,
                metadata=dict(row.metadata or {}),
            )
            if corpus_chunk is not None:
                module_chunks.append(corpus_chunk)
        if not module_chunks:
            continue
        chunks.extend(module_chunks)
        compiled_module_ids.add(module_id)

    chunks.sort(key=lambda chunk: chunk.chunk_id)
    return chunks, compiled_module_ids


def fingerprint_compiler_seed_chunks(chunks: list[CorpusChunk]) -> str:
    digest = hashlib.sha256()
    if not chunks:
        digest.update(b"no_compiler_seeds")
        return digest.hexdigest()
    for chunk in chunks:
        digest.update(
            f"{chunk.chunk_id}:{chunk.source_version}:{chunk.source_hash}".encode("utf-8")
        )
    return digest.hexdigest()
