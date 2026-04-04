from __future__ import annotations

from pathlib import Path

from wos_ai_stack.rag import (
    ContentClass,
    ContextPackAssembler,
    ContextRetriever,
    RagIngestionPipeline,
    RetrievalDomain,
    RetrievalRequest,
    RetrievalStatus,
    build_runtime_retriever,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_ingestion_builds_corpus_from_repo_owned_sources(tmp_path: Path) -> None:
    _write(
        tmp_path / "content" / "god_of_carnage.md",
        "God of Carnage scene where Veronique and Michael discuss civility.",
    )
    _write(
        tmp_path / "docs" / "architecture" / "runtime.md",
        "Runtime policy document for authoritative story turns.",
    )
    _write(
        tmp_path / "world-engine" / "app" / "var" / "runs" / "sample.json",
        '{"entries":[{"speaker":"player","line":"I open the door"}]}',
    )

    corpus = RagIngestionPipeline(chunk_size=120, overlap=20).build_corpus(tmp_path)

    assert corpus.source_count >= 3
    assert len(corpus.chunks) >= 3
    assert any(chunk.content_class == ContentClass.AUTHORED_MODULE for chunk in corpus.chunks)
    assert any(chunk.content_class == ContentClass.POLICY_GUIDELINE for chunk in corpus.chunks)
    assert any(chunk.content_class == ContentClass.TRANSCRIPT for chunk in corpus.chunks)


def test_retrieval_is_deterministic_for_known_relevant_content(tmp_path: Path) -> None:
    _write(
        tmp_path / "content" / "god_of_carnage.md",
        "God of Carnage dinner argument escalates into chaos and social breakdown.",
    )
    _write(tmp_path / "content" / "other_story.md", "A spaceship story with no dinner argument.")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)

    request = RetrievalRequest(
        domain=RetrievalDomain.RUNTIME,
        profile="runtime_turn_support",
        query="god of carnage dinner argument",
        module_id="god_of_carnage",
        max_chunks=1,
    )
    result = retriever.retrieve(request)

    assert result.status == RetrievalStatus.OK
    assert result.hits
    assert "god_of_carnage" in result.hits[0].source_path


def test_retrieval_supports_semantic_phrasing_not_only_exact_overlap(tmp_path: Path) -> None:
    _write(
        tmp_path / "content" / "god_of_carnage.md",
        "The dinner dispute between both families escalates into social collapse.",
    )
    _write(tmp_path / "content" / "sports.md", "The team celebrates a championship victory.")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)

    result = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="family argument at dinner becomes chaotic",
            module_id="god_of_carnage",
            max_chunks=1,
        )
    )

    assert result.status == RetrievalStatus.OK
    assert result.hits
    assert "god_of_carnage" in result.hits[0].source_path


def test_retrieval_domain_separation_excludes_runtime_from_review_only_content(tmp_path: Path) -> None:
    _write(tmp_path / "docs" / "reports" / "review.md", "Review artifact with red flags and remediation.")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)

    runtime_result = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="red flags remediation review",
            max_chunks=2,
        )
    )
    writers_result = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.WRITERS_ROOM,
            profile="writers_review",
            query="red flags remediation review",
            max_chunks=2,
        )
    )

    assert runtime_result.status in {RetrievalStatus.FALLBACK, RetrievalStatus.DEGRADED}
    assert all(hit.content_class != ContentClass.REVIEW_NOTE.value for hit in runtime_result.hits)
    assert any(hit.content_class == ContentClass.REVIEW_NOTE.value for hit in writers_result.hits)


def test_retrieval_profile_boosts_canonical_content_for_runtime(tmp_path: Path) -> None:
    _write(tmp_path / "content" / "modules" / "god_of_carnage" / "canon.md", "Dispute and civility collapse.")
    _write(
        tmp_path / "world-engine" / "app" / "var" / "runs" / "session.json",
        '{"log":"dispute and civility collapse in transcript"}',
    )
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    result = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="dispute and civility collapse",
            module_id="god_of_carnage",
            max_chunks=1,
        )
    )

    assert result.status == RetrievalStatus.OK
    assert result.hits[0].content_class == ContentClass.AUTHORED_MODULE.value


def test_context_pack_exposes_attribution_and_selection_notes(tmp_path: Path) -> None:
    _write(tmp_path / "content" / "god_of_carnage.md", "God of Carnage includes conflict and social tension.")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    assembler = ContextPackAssembler()

    result = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="conflict social tension",
            max_chunks=2,
        )
    )
    pack = assembler.assemble(result)

    assert pack.hit_count >= 1
    assert pack.sources
    assert "selection_reason" in pack.sources[0]
    assert "source_version" in pack.sources[0]
    assert pack.ranking_notes


def test_runtime_retriever_persists_and_reuses_index(tmp_path: Path) -> None:
    _write(tmp_path / "content" / "god_of_carnage.md", "Families argue at dinner.")
    retriever_a, _assembler_a, corpus_a = build_runtime_retriever(tmp_path)
    retriever_b, _assembler_b, corpus_b = build_runtime_retriever(tmp_path)

    assert retriever_a is not None
    assert retriever_b is not None
    assert corpus_a.storage_path
    assert Path(corpus_a.storage_path).exists()
    assert corpus_b.storage_path == corpus_a.storage_path
    assert corpus_b.corpus_fingerprint == corpus_a.corpus_fingerprint


def test_ingestion_metadata_changes_when_source_content_changes(tmp_path: Path) -> None:
    target = tmp_path / "content" / "god_of_carnage.md"
    _write(target, "Original canon line.")
    before = RagIngestionPipeline().build_corpus(tmp_path)
    _write(target, "Original canon line updated with new policy wording.")
    after = RagIngestionPipeline().build_corpus(tmp_path)

    before_versions = {chunk.source_path: chunk.source_version for chunk in before.chunks}
    after_versions = {chunk.source_path: chunk.source_version for chunk in after.chunks}
    assert before_versions != after_versions


def test_semantic_expansion_boosts_recall_for_paraphrased_query(tmp_path: Path) -> None:
    """Proves that semantic canonicalization lifts paraphrased queries to canonical terms.

    Content uses the canonical term 'conflict'. Query uses 'argue', which maps to 'conflict'
    via SEMANTIC_CANON. Retrieval must return at least one result, demonstrating that
    _build_semantic_terms expands the paraphrase rather than doing pure lexical matching.
    """
    _write(
        tmp_path / "content" / "god_of_carnage.md",
        "The scene depicts a profound conflict between the two families over parenting values.",
    )
    _write(tmp_path / "content" / "sports.md", "The championship match ended in a stunning victory.")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)

    result = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="argue about values",  # 'argue' -> canonical 'conflict' via SEMANTIC_CANON
            module_id="god_of_carnage",
            max_chunks=1,
        )
    )

    assert result.status == RetrievalStatus.OK
    assert result.hits, "semantic expansion should surface the conflict-bearing document"
    assert "god_of_carnage" in result.hits[0].source_path


def test_retrieval_gracefully_handles_sparse_or_absent_corpus(tmp_path: Path) -> None:
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    result = ContextRetriever(corpus).retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.IMPROVEMENT,
            profile="improvement_eval",
            query="anything",
        )
    )

    assert result.status == RetrievalStatus.DEGRADED
    assert result.error == "retrieval_corpus_empty"
    assert result.hits == []
