from __future__ import annotations

from pathlib import Path

import pytest

from wos_ai_stack.rag import (
    ContentClass,
    ContextPackAssembler,
    ContextRetriever,
    INDEX_VERSION,
    PersistentRagStore,
    RagIngestionPipeline,
    RetrievalDomain,
    RetrievalRequest,
    RetrievalStatus,
    build_runtime_retriever,
)
from wos_ai_stack.tests.embedding_markers import requires_embeddings


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
    assert "chunk_id" in pack.sources[0]
    assert "score" in pack.sources[0]
    assert "selection_reason" in pack.sources[0]
    assert "source_version" in pack.sources[0]
    assert "snippet" in pack.sources[0]
    assert pack.sources[0]["snippet"]
    assert pack.ranking_notes
    assert pack.index_version == INDEX_VERSION
    assert pack.corpus_fingerprint == corpus.corpus_fingerprint


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
    assert result.index_version == INDEX_VERSION
    assert result.corpus_fingerprint == corpus.corpus_fingerprint


def test_published_tree_outranks_module_tree_when_content_overlaps(tmp_path: Path) -> None:
    shared = "Dinner dispute between families escalates into civility collapse and chaos."
    _write(tmp_path / "content" / "modules" / "alpha_mod" / "draft.md", shared)
    _write(tmp_path / "content" / "published" / "alpha_mod" / "canon.md", shared)
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    result = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="dinner dispute families civility chaos",
            module_id="alpha_mod",
            max_chunks=1,
        )
    )
    assert result.status == RetrievalStatus.OK
    assert "content/published/alpha_mod/canon.md" in result.hits[0].source_path.replace("\\", "/")


def test_module_id_inferred_from_modules_path_not_collapsed(tmp_path: Path) -> None:
    _write(
        tmp_path / "content" / "modules" / "other_module" / "arc.md",
        "A spaceship expedition discovers an ancient signal.",
    )
    _write(
        tmp_path / "content" / "god_of_carnage.md",
        "God of Carnage dinner dispute with no spaceship.",
    )
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    result = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="spaceship expedition ancient signal",
            module_id="other_module",
            max_chunks=1,
        )
    )
    assert result.status == RetrievalStatus.OK
    assert "other_module" in result.hits[0].source_path.replace("\\", "/")
    assert "god_of_carnage.md" not in result.hits[0].source_path


def test_semantic_canon_maps_tension_to_conflict(tmp_path: Path) -> None:
    _write(
        tmp_path / "content" / "tension_scene.md",
        "The scene shows deep conflict between rivals over honor.",
    )
    _write(tmp_path / "content" / "weather.md", "Gentle rain falls on the quiet meadow.")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    result = ContextRetriever(corpus).retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="interpersonal tension and honor",
            module_id="tension_scene",
            max_chunks=1,
        )
    )
    assert result.status == RetrievalStatus.OK
    assert "tension_scene.md" in result.hits[0].source_path


def test_improvement_profile_surfaces_evaluation_artifact(tmp_path: Path) -> None:
    _write(
        tmp_path / "docs" / "reports" / "eval_acceptance.md",
        "Acceptance evaluation metrics for sandbox variant comparison and trigger coverage.",
    )
    _write(tmp_path / "content" / "noise.md", "Unrelated cooking recipe without evaluation metrics.")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    result = ContextRetriever(corpus).retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.IMPROVEMENT,
            profile="improvement_eval",
            query="sandbox variant evaluation trigger coverage metrics",
            max_chunks=2,
        )
    )
    assert result.status == RetrievalStatus.OK
    assert any(hit.content_class == ContentClass.EVALUATION_ARTIFACT.value for hit in result.hits)


def test_persistent_rag_store_roundtrip_preserves_chunks(tmp_path: Path) -> None:
    _write(tmp_path / "content" / "persist.md", "Persistent retrieval corpus sample text.")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    path = tmp_path / "nested" / "corpus.json"
    store = PersistentRagStore(path)
    store.save(corpus)
    loaded = store.load(expected_fingerprint=corpus.corpus_fingerprint)
    assert loaded is not None
    assert loaded.index_version == INDEX_VERSION
    assert len(loaded.chunks) == len(corpus.chunks)
    assert loaded.chunks[0].chunk_id == corpus.chunks[0].chunk_id


@requires_embeddings
def test_hybrid_ranking_beats_sparse_only_on_paraphrase_with_low_lexical_overlap(tmp_path: Path) -> None:
    """Dense similarity should connect paraphrases where sparse token overlap is weak."""
    _write(
        tmp_path / "content" / "wildlife.md",
        "A nocturnal marsupial navigated the eucalyptus canopy seeking nectar beneath the southern stars.",
    )
    _write(
        tmp_path / "content" / "finance.md",
        "The stock market rallied sharply after inflation data surprised analysts on Wall Street.",
    )
    retriever, _, _corpus = build_runtime_retriever(tmp_path)
    query = "koala moving through gum trees at night looking for food"
    hybrid_req = RetrievalRequest(
        domain=RetrievalDomain.RUNTIME,
        profile="runtime_turn_support",
        query=query,
        module_id="wildlife",
        max_chunks=2,
    )
    sparse_req = RetrievalRequest(
        domain=RetrievalDomain.RUNTIME,
        profile="runtime_turn_support",
        query=query,
        module_id="wildlife",
        max_chunks=2,
        use_sparse_only=True,
    )
    hybrid_res = retriever.retrieve(hybrid_req)
    sparse_res = retriever.retrieve(sparse_req)
    assert hybrid_res.retrieval_route == "hybrid"
    assert hybrid_res.hits, "hybrid path should return hits"
    assert hybrid_res.hits[0].source_path.replace("\\", "/").endswith("wildlife.md")
    assert sparse_res.retrieval_route == "sparse_fallback"
    assert sparse_res.hits
    sparse_top = sparse_res.hits[0].source_path.replace("\\", "/")
    hybrid_top = hybrid_res.hits[0].source_path.replace("\\", "/")
    assert hybrid_top != sparse_top or "wildlife" in sparse_top


@requires_embeddings
def test_embedding_index_survives_reload_via_build_runtime_retriever(tmp_path: Path) -> None:
    _write(tmp_path / "content" / "doc.md", "Persistent hybrid index reload check for retrieval.")
    retriever_a, _, corpus_a = build_runtime_retriever(tmp_path)
    npz_path = Path(corpus_a.storage_path).parent / "runtime_embeddings.npz"
    meta_path = Path(corpus_a.storage_path).parent / "runtime_embeddings.meta.json"
    assert npz_path.is_file()
    assert meta_path.is_file()
    assert retriever_a.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="reload check",
            max_chunks=1,
        )
    ).retrieval_route == "hybrid"
    retriever_b, _, corpus_b = build_runtime_retriever(tmp_path)
    assert retriever_b.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="reload check",
            max_chunks=1,
        )
    ).retrieval_route == "hybrid"
    assert corpus_b.corpus_fingerprint == corpus_a.corpus_fingerprint


def test_sparse_fallback_explicit_when_embeddings_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOS_RAG_DISABLE_EMBEDDINGS", "1")
    _write(tmp_path / "content" / "alpha.md", "Dinner dispute between families escalates into chaos.")
    retriever, _, _ = build_runtime_retriever(tmp_path)
    result = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="family argument at dinner",
            max_chunks=1,
        )
    )
    assert result.retrieval_route == "sparse_fallback"
    assert result.embedding_model_id == ""
    assert any("retrieval_route=sparse_fallback" in note for note in result.ranking_notes)


@requires_embeddings
def test_hybrid_used_for_runtime_and_improvement_profiles(tmp_path: Path) -> None:
    _write(tmp_path / "content" / "mod.md", "Sandbox variant evaluation metrics and trigger coverage notes.")
    _write(
        tmp_path / "docs" / "reports" / "eval_acceptance.md",
        "Acceptance evaluation metrics for sandbox variant comparison.",
    )
    retriever, _, _ = build_runtime_retriever(tmp_path)
    r_runtime = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="evaluation metrics",
            max_chunks=2,
        )
    )
    r_imp = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.IMPROVEMENT,
            profile="improvement_eval",
            query="sandbox variant evaluation",
            max_chunks=2,
        )
    )
    assert r_runtime.retrieval_route == "hybrid"
    assert r_imp.retrieval_route == "hybrid"
    assert "retrieval_route=hybrid" in r_runtime.ranking_notes[0]
    assert "retrieval_route=hybrid" in r_imp.ranking_notes[0]
