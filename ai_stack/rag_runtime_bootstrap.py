"""Wire ingestion, persistence, embedding index, and ``ContextRetriever`` for a repo root (DS-003 stage 11)."""

from __future__ import annotations

from pathlib import Path

from ai_stack.rag_context_pack_assembler import ContextPackAssembler
from ai_stack.rag_context_retriever import ContextRetriever
from ai_stack.rag_corpus import InMemoryRetrievalCorpus
from ai_stack.rag_embedding_index import _ensure_corpus_embedding_index
from ai_stack.rag_ingestion import RagIngestionPipeline
from ai_stack.rag_persistent_store import PersistentRagStore


def build_runtime_retriever(repo_root: Path) -> tuple[ContextRetriever, ContextPackAssembler, InMemoryRetrievalCorpus]:
    persistence_path = repo_root / ".wos" / "rag" / "runtime_corpus.json"
    pipeline = RagIngestionPipeline()
    fingerprint = pipeline.compute_source_fingerprint(repo_root)
    store = PersistentRagStore(persistence_path)
    cached = store.load(expected_fingerprint=fingerprint)
    if cached is not None:
        cached.storage_path = str(persistence_path)
        corpus = cached
    else:
        corpus = pipeline.build_corpus(repo_root, source_fingerprint=fingerprint)
        corpus.storage_path = str(persistence_path)
        store.save(corpus)
    emb_index = _ensure_corpus_embedding_index(corpus, persistence_path)
    model_id = emb_index.model_id if emb_index is not None else ""
    return ContextRetriever(corpus, embedding_index=emb_index, embedding_model_id=model_id), ContextPackAssembler(), corpus
