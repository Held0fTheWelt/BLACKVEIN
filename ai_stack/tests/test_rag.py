from __future__ import annotations

from pathlib import Path

import pytest

from ai_stack.rag import (
    ContentClass,
    DENSE_INDEX_META_SCHEMA,
    RETRIEVAL_POLICY_VERSION,
    RetrievalDegradationMode,
    ContextPackAssembler,
    ContextRetriever,
    INDEX_VERSION,
    PersistentRagStore,
    RagIngestionPipeline,
    RETRIEVAL_PIPELINE_VERSION,
    SourceEvidenceLane,
    governance_view_for_chunk,
    RetrievalDomain,
    RetrievalRequest,
    RetrievalStatus,
    build_runtime_retriever,
)
from ai_stack.tests.embedding_markers import requires_embeddings


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
    assert result.degradation_mode == RetrievalDegradationMode.SPARSE_FALLBACK_NO_BACKEND.value
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


def test_degradation_metadata_when_embeddings_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOS_RAG_DISABLE_EMBEDDINGS", "1")
    _write(tmp_path / "content" / "x.md", "alpha beta gamma dispute.")
    retriever, _, _ = build_runtime_retriever(tmp_path)
    res = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="dispute",
            max_chunks=1,
        )
    )
    assert res.degradation_mode == RetrievalDegradationMode.SPARSE_FALLBACK_NO_BACKEND.value
    assert res.retrieval_route == "sparse_fallback"
    assert any(res.degradation_mode in n for n in res.ranking_notes)


@requires_embeddings
def test_valid_dense_index_reused_shows_reused_persisted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WOS_RAG_DISABLE_EMBEDDINGS", raising=False)
    _write(tmp_path / "content" / "doc.md", "Koala eucalyptus canopy nocturnal.")
    r1, _, c1 = build_runtime_retriever(tmp_path)
    assert c1.rag_dense_index_build_action == RetrievalDegradationMode.REBUILT_DENSE_INDEX.value
    r2, _, c2 = build_runtime_retriever(tmp_path)
    assert c2.rag_dense_index_build_action == "reused_persisted"
    assert r2.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="koala",
            max_chunks=1,
        )
    ).degradation_mode == RetrievalDegradationMode.HYBRID_OK.value


@requires_embeddings
def test_corpus_drift_triggers_dense_rebuild(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WOS_RAG_DISABLE_EMBEDDINGS", raising=False)
    p = tmp_path / "content" / "drift.md"
    _write(p, "version one text")
    build_runtime_retriever(tmp_path)
    _write(p, "version two completely different content for drift")
    _, _, c2 = build_runtime_retriever(tmp_path)
    assert c2.rag_dense_index_build_action == RetrievalDegradationMode.REBUILT_DENSE_INDEX.value


@requires_embeddings
def test_embedding_meta_version_mismatch_invalidates_dense(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    monkeypatch.delenv("WOS_RAG_DISABLE_EMBEDDINGS", raising=False)
    _write(tmp_path / "content" / "m.md", "persistent meta drift test corpus")
    _, _, corpus = build_runtime_retriever(tmp_path)
    meta_path = Path(corpus.storage_path).parent / "runtime_embeddings.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["embedding_index_version"] = "bogus_version"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    _, _, c2 = build_runtime_retriever(tmp_path)
    assert c2.rag_dense_index_build_action == RetrievalDegradationMode.REBUILT_DENSE_INDEX.value


@requires_embeddings
def test_orphan_npz_without_meta_is_not_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    from ai_stack.rag import _load_corpus_embedding_index

    monkeypatch.delenv("WOS_RAG_DISABLE_EMBEDDINGS", raising=False)
    _write(tmp_path / "content" / "o.md", "orphan npz without committed meta")
    _, _, corpus = build_runtime_retriever(tmp_path)
    meta_path = Path(corpus.storage_path).parent / "runtime_embeddings.meta.json"
    meta_path.unlink()
    load_res = _load_corpus_embedding_index(corpus, Path(corpus.storage_path))
    assert "dense_meta_missing_or_uncommitted" in load_res.reason_codes
    assert load_res.artifact_validity == "uncommitted_vectors_only"
    _, _, c2 = build_runtime_retriever(tmp_path)
    assert c2.rag_dense_index_build_action == RetrievalDegradationMode.REBUILT_DENSE_INDEX.value
    assert meta_path.is_file()
    loaded = json.loads(meta_path.read_text(encoding="utf-8"))
    assert loaded.get("dense_meta_schema") == DENSE_INDEX_META_SCHEMA


@requires_embeddings
def test_vectors_hash_mismatch_rejects_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    monkeypatch.delenv("WOS_RAG_DISABLE_EMBEDDINGS", raising=False)
    _write(tmp_path / "content" / "h.md", "hash mismatch rejection case")
    _, _, corpus = build_runtime_retriever(tmp_path)
    meta_path = Path(corpus.storage_path).parent / "runtime_embeddings.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["vectors_canonical_sha256"] = "0" * 64
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    _, _, c2 = build_runtime_retriever(tmp_path)
    assert c2.rag_dense_index_build_action == RetrievalDegradationMode.REBUILT_DENSE_INDEX.value


@requires_embeddings
def test_missing_npz_rebuilds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WOS_RAG_DISABLE_EMBEDDINGS", raising=False)
    _write(tmp_path / "content" / "n.md", "missing npz file recovery")
    _, _, corpus = build_runtime_retriever(tmp_path)
    npz = Path(corpus.storage_path).parent / "runtime_embeddings.npz"
    npz.unlink()
    _, _, c2 = build_runtime_retriever(tmp_path)
    assert "dense_npz_missing" in c2.rag_dense_load_reason_codes or c2.rag_dense_index_build_action == RetrievalDegradationMode.REBUILT_DENSE_INDEX.value
    assert npz.is_file()


def test_sparse_when_fastembed_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import importlib

    monkeypatch.delenv("WOS_RAG_DISABLE_EMBEDDINGS", raising=False)
    real = importlib.import_module

    def fake(name: str, package=None):
        if name == "fastembed":
            raise ImportError("no fastembed")
        return real(name, package)

    monkeypatch.setattr(importlib, "import_module", fake)
    _write(tmp_path / "content" / "z.md", "sparse only no fastembed")
    retriever, _, _ = build_runtime_retriever(tmp_path)
    res = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="sparse",
            max_chunks=1,
        )
    )
    assert res.retrieval_route == "sparse_fallback"
    assert res.degradation_mode == RetrievalDegradationMode.SPARSE_FALLBACK_NO_BACKEND.value


@requires_embeddings
def test_sparse_when_query_encode_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import ai_stack.rag as rag_mod

    monkeypatch.delenv("WOS_RAG_DISABLE_EMBEDDINGS", raising=False)
    _write(tmp_path / "content" / "q.md", "query encode failure sparse path")
    retriever, _, _ = build_runtime_retriever(tmp_path)

    def boom(_q: str):
        from ai_stack.semantic_embedding import EncodeOutcome

        return EncodeOutcome(None, ("embedding_runtime_error",))

    monkeypatch.setattr(rag_mod, "encode_query_detailed", boom)
    res = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="anything",
            max_chunks=1,
        )
    )
    assert res.retrieval_route == "sparse_fallback"
    assert res.degradation_mode == RetrievalDegradationMode.SPARSE_FALLBACK_ENCODE_FAILURE.value


@requires_embeddings
def test_meta_commit_order_survives_replace_failure_on_meta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import json
    import os

    monkeypatch.delenv("WOS_RAG_DISABLE_EMBEDDINGS", raising=False)
    _write(tmp_path / "content" / "a.md", "atomic replace meta failure")
    _, _, corpus = build_runtime_retriever(tmp_path)
    meta_path = Path(corpus.storage_path).parent / "runtime_embeddings.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["num_chunks"] = 99999
    corrupted = json.dumps(meta, indent=2)
    meta_path.write_text(corrupted, encoding="utf-8")
    calls = {"n": 0}
    real_replace = os.replace

    def flaky_replace(src: str, dst: str) -> None:
        calls["n"] += 1
        if dst.endswith("runtime_embeddings.meta.json") and calls["n"] >= 2:
            raise OSError("simulated_meta_replace_failure")
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", flaky_replace)
    from ai_stack.rag import RagIngestionPipeline

    fp = RagIngestionPipeline().compute_source_fingerprint(tmp_path)
    corpus2 = RagIngestionPipeline().build_corpus(tmp_path, source_fingerprint=fp)
    corpus2.storage_path = corpus.storage_path
    from ai_stack.rag import _ensure_corpus_embedding_index

    _ensure_corpus_embedding_index(corpus2, Path(corpus.storage_path))
    assert corpus2.rag_dense_artifact_validity == "partial_write_failure"
    assert meta_path.read_text(encoding="utf-8") == corrupted


def test_profile_specific_ranking_differs_for_same_query(tmp_path: Path) -> None:
    """Runtime, writers, and improvement profiles should surface different evidence mixes."""
    _write(
        tmp_path / "content" / "modules" / "mod_a" / "scene.md",
        "Canon scene text about dinner dispute civility collapse for the module.",
    )
    _write(
        tmp_path / "docs" / "reports" / "review_mod_a.md",
        "Review note: red flags remediation and writer feedback for dinner dispute module.",
    )
    _write(
        tmp_path / "docs" / "reports" / "eval_mod_a.md",
        "Acceptance evaluation metrics sandbox variant trigger coverage for the module.",
    )
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    query = "dinner dispute sandbox variant metrics remediation"
    rt = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query=query,
            module_id="mod_a",
            max_chunks=3,
            use_sparse_only=True,
        )
    )
    wr = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.WRITERS_ROOM,
            profile="writers_review",
            query=query,
            module_id="mod_a",
            max_chunks=3,
            use_sparse_only=True,
        )
    )
    im = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.IMPROVEMENT,
            profile="improvement_eval",
            query=query,
            module_id="mod_a",
            max_chunks=3,
            use_sparse_only=True,
        )
    )
    assert rt.hits[0].content_class == ContentClass.AUTHORED_MODULE.value
    assert any(h.content_class == ContentClass.REVIEW_NOTE.value for h in wr.hits)
    assert any(h.content_class == ContentClass.EVALUATION_ARTIFACT.value for h in im.hits)
    rt_classes = [h.content_class for h in rt.hits]
    im_classes = [h.content_class for h in im.hits]
    assert rt_classes != im_classes or rt.hits[0].chunk_id != im.hits[0].chunk_id


def test_runtime_prefers_canonical_over_transcript_when_both_match(tmp_path: Path) -> None:
    """Runtime profile should deprioritize transcript clutter when strong authored module exists."""
    body = (
        "dinner dispute civility collapse chaos families argument escalation confrontation "
        "same thematic keywords repeated for overlap"
    )
    _write(tmp_path / "content" / "modules" / "goc" / "canon.md", f"Authored canon: {body}")
    _write(
        tmp_path / "world-engine" / "app" / "var" / "runs" / "live.json",
        f'{{"transcript":"{body}"}}',
    )
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    res = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="dinner dispute civility collapse chaos families",
            module_id="goc",
            max_chunks=2,
            use_sparse_only=True,
        )
    )
    assert res.hits[0].content_class == ContentClass.AUTHORED_MODULE.value


def test_rerank_can_reorder_behind_module_match_sparse_only(tmp_path: Path) -> None:
    """Module-scoped rerank extra should overtake a higher-lexical off-module chunk (deterministic)."""
    qterms = (
        "acceptance evaluation metrics trigger coverage sandbox variant comparison "
        "recommendation diagnostic"
    )
    _write(
        tmp_path / "content" / "published" / "other_mod" / "canon.md",
        f"Published canon packed with keywords: {qterms} {qterms} extra density for sparse scoring.",
    )
    _write(
        tmp_path / "content" / "modules" / "target_mod" / "draft.md",
        f"Module target_mod draft: {qterms}",
    )
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    req = RetrievalRequest(
        domain=RetrievalDomain.RUNTIME,
        profile="runtime_turn_support",
        query="acceptance evaluation metrics trigger coverage sandbox variant",
        module_id="target_mod",
        max_chunks=2,
        use_sparse_only=True,
    )
    res = retriever.retrieve(req)
    top_path = res.hits[0].source_path.replace("\\", "/")
    assert "target_mod" in top_path
    assert any("rerank_module_extra" in h.selection_reason for h in res.hits if "target_mod" in h.source_path)


def test_near_duplicate_suppression_frees_top_slots(tmp_path: Path) -> None:
    """Near-identical chunks should not both consume top-k after dedup."""
    text_a = "Unique evaluation trigger coverage sandbox variant metrics acceptance story."
    text_b = text_a + " "  # effectively identical for trigram Jaccard
    _write(tmp_path / "content" / "alpha.md", text_a)
    _write(tmp_path / "content" / "beta.md", text_b)
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    res = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.IMPROVEMENT,
            profile="improvement_eval",
            query="evaluation trigger coverage sandbox variant metrics",
            max_chunks=3,
            use_sparse_only=True,
        )
    )
    paths = {h.source_path.replace("\\", "/") for h in res.hits}
    assert "alpha.md" in str(paths) or "beta.md" in str(paths)
    assert not ("alpha.md" in str(paths) and "beta.md" in str(paths))
    assert any("dup_suppressed" in n for n in res.ranking_notes)


def test_context_pack_orders_sections_and_includes_pack_metadata(tmp_path: Path) -> None:
    """Assembler should group workflow sections and expose pack_role / why_selected."""
    _write(
        tmp_path / "content" / "published" / "pm" / "canon.md",
        "Published priority canon dispute civility for packing order test.",
    )
    _write(
        tmp_path / "content" / "modules" / "pm" / "notes.md",
        "Supporting draft dispute civility overlap for packing order test.",
    )
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    assembler = ContextPackAssembler()
    result = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="dispute civility packing order",
            module_id="pm",
            max_chunks=2,
            use_sparse_only=True,
        )
    )
    pack = assembler.assemble(result)
    assert "Canonical evidence" in pack.compact_context
    assert RETRIEVAL_PIPELINE_VERSION in pack.compact_context
    assert pack.sources[0].get("pack_role")
    assert pack.sources[0].get("why_selected")
    assert any("retrieval_pipeline_version=" in n for n in pack.ranking_notes)


def test_ranking_notes_include_quality_pipeline_hybrid_weights(tmp_path: Path) -> None:
    _write(tmp_path / "content" / "z.md", "gamma ray evaluation metrics sandbox.")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    res = ContextRetriever(corpus).retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="evaluation metrics sandbox",
            max_chunks=1,
            use_sparse_only=True,
        )
    )
    joined = " ".join(res.ranking_notes)
    assert RETRIEVAL_PIPELINE_VERSION in joined
    assert "hybrid_v2_weights_dense=" in joined
    assert "rerank_pool_size=" in joined


def test_sparse_fallback_still_populates_task1_prefix_and_quality_notes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sparse path must keep Task 1-style prefix notes and append Task 2 quality notes."""
    monkeypatch.setenv("WOS_RAG_DISABLE_EMBEDDINGS", "1")
    _write(tmp_path / "content" / "t.md", "sparse fallback pipeline check alpha beta.")
    retriever, _, _ = build_runtime_retriever(tmp_path)
    res = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="alpha beta pipeline",
            max_chunks=1,
        )
    )
    assert res.retrieval_route == "sparse_fallback"
    notes = res.ranking_notes
    assert any(n.startswith("retrieval_route=") for n in notes)
    assert any(n.startswith("degradation_mode=") for n in notes)
    assert any("retrieval_pipeline_version=" in n for n in notes)
    assert any(n.startswith("retrieval_policy_version=") for n in notes)


def test_runtime_hard_excludes_module_draft_when_published_canonical_in_pool(tmp_path: Path) -> None:
    """Task 3 hard gate: runtime drops same-module draft authored chunks when published canonical exists."""
    shared = "Dinner dispute families civility collapse chaos escalation unique tokens for overlap."
    _write(tmp_path / "content" / "modules" / "gate_mod" / "draft.md", shared)
    _write(tmp_path / "content" / "published" / "gate_mod" / "canon.md", shared)
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    res = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="dinner dispute families civility collapse chaos escalation",
            module_id="gate_mod",
            max_chunks=2,
            use_sparse_only=True,
        )
    )
    assert res.status == RetrievalStatus.OK
    assert len(res.hits) >= 1
    paths = {h.source_path.replace("\\", "/") for h in res.hits}
    assert any("content/published/gate_mod/" in p for p in paths)
    assert not any("content/modules/gate_mod/draft.md" in p for p in paths)
    joined = " ".join(res.ranking_notes)
    assert "policy_hard_excluded_pool_count=" in joined
    assert "draft_when_published_canonical_in_pool" in joined


def test_writers_room_retains_draft_alongside_published_canonical(tmp_path: Path) -> None:
    """Writers profile does not apply the runtime draft hard-exclusion gate."""
    # Distinct bodies so near-duplicate suppression does not drop the draft chunk.
    draft_body = "Writers room draft dispute civility collapse chaos working material unique draft notes."
    pub_body = "Writers room published canon dispute civility collapse chaos authoritative line."
    _write(tmp_path / "content" / "modules" / "wr_mod" / "draft.md", draft_body)
    _write(tmp_path / "content" / "published" / "wr_mod" / "canon.md", pub_body)
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    res = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.WRITERS_ROOM,
            profile="writers_review",
            query="writers room dispute civility collapse chaos draft published canon",
            module_id="wr_mod",
            max_chunks=3,
            use_sparse_only=True,
        )
    )
    assert res.status == RetrievalStatus.OK
    paths = {h.source_path.replace("\\", "/") for h in res.hits}
    assert any("content/published/wr_mod/" in p for p in paths)
    assert any("content/modules/wr_mod/draft.md" in p for p in paths)
    assert "policy_hard_excluded_pool_count=" not in " ".join(res.ranking_notes)


def test_runtime_retains_module_draft_when_no_published_canonical_anchor(tmp_path: Path) -> None:
    """Without published-tree canonical for the module, runtime may keep module draft as anchor evidence."""
    body = "Solo module draft anchor dispute civility collapse for runtime policy note test."
    _write(tmp_path / "content" / "modules" / "solo_mod" / "only_draft.md", body)
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    res = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="solo module draft anchor dispute civility collapse",
            module_id="solo_mod",
            max_chunks=1,
            use_sparse_only=True,
        )
    )
    assert res.status == RetrievalStatus.OK
    assert res.hits
    assert "content/modules/solo_mod/" in res.hits[0].source_path.replace("\\", "/")
    assert res.hits[0].source_evidence_lane == SourceEvidenceLane.DRAFT_WORKING.value
    assert "draft_lane_retained_no_published_canonical_anchor" in res.hits[0].policy_note


def test_governance_metadata_on_hits_and_context_pack_sources(tmp_path: Path) -> None:
    """Hits and ContextPack.sources expose evidence lane, visibility, and policy trace fields."""
    _write(
        tmp_path / "content" / "published" / "gm" / "canon.md",
        "Governance metadata published canon dispute civility.",
    )
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    assembler = ContextPackAssembler()
    res = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="governance metadata dispute civility",
            module_id="gm",
            max_chunks=1,
            use_sparse_only=True,
        )
    )
    pack = assembler.assemble(res)
    h0 = res.hits[0]
    assert h0.source_evidence_lane == SourceEvidenceLane.CANONICAL.value
    assert h0.source_visibility_class == "runtime_safe"
    assert h0.policy_note.startswith("allowed:")
    assert h0.profile_policy_influence
    s0 = pack.sources[0]
    assert s0.get("source_evidence_lane") == SourceEvidenceLane.CANONICAL.value
    assert s0.get("policy_note")
    assert s0.get("profile_policy_influence")
    assert RETRIEVAL_POLICY_VERSION in pack.compact_context
    assert "context_pack_governance=runtime_canonical_first_when_available" in pack.compact_context


def test_runtime_task2_clutter_penalty_distinct_from_task3_policy_soft_notes(tmp_path: Path) -> None:
    """Task 2 ``runtime_clutter_penalty`` remains on transcript; Task 3 adds separate ``policy_*`` notes."""
    body = (
        "Transcript clutter dispute civility collapse chaos families argument "
        "keyword overlap for transcript penalty test."
    )
    _write(tmp_path / "content" / "modules" / "tr_mod" / "canon.md", f"Canon authored: {body}")
    _write(
        tmp_path / "world-engine" / "app" / "var" / "runs" / "live.json",
        f'{{"transcript":"{body}"}}',
    )
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    res = retriever.retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query="transcript clutter dispute civility collapse chaos families",
            module_id="tr_mod",
            max_chunks=2,
            use_sparse_only=True,
        )
    )
    assert res.status == RetrievalStatus.OK
    tr_hits = [h for h in res.hits if "var/runs" in h.source_path.replace("\\", "/")]
    for h in tr_hits:
        assert "runtime_clutter_penalty" in h.selection_reason
    assert any("retrieval_policy_version=" in n for n in res.ranking_notes)


def test_improvement_policy_soft_boost_on_policy_guideline(tmp_path: Path) -> None:
    """Improvement profile applies ``policy_soft_improvement_policy_diagnostic`` (orthogonal to Task 2 rerank)."""
    _write(
        tmp_path / "docs" / "architecture" / "eval_policy.md",
        "Architecture policy diagnostic evaluation metrics sandbox trigger coverage soft policy.",
    )
    _write(tmp_path / "content" / "noise_eval.md", "Noise text without architecture policy diagnostic wording.")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    res = ContextRetriever(corpus).retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.IMPROVEMENT,
            profile="improvement_eval",
            query="architecture policy diagnostic evaluation metrics sandbox trigger",
            max_chunks=2,
            use_sparse_only=True,
        )
    )
    assert res.status == RetrievalStatus.OK
    pol = [h for h in res.hits if h.content_class == ContentClass.POLICY_GUIDELINE.value]
    assert pol
    assert "policy_soft_improvement_policy_diagnostic" in pol[0].selection_reason


def test_improvement_profile_prefers_evaluative_lane_in_metadata(tmp_path: Path) -> None:
    """Improvement retrieval labels evaluative sources clearly in hit metadata."""
    _write(
        tmp_path / "docs" / "reports" / "eval_governance.md",
        "Acceptance evaluation metrics sandbox variant trigger coverage governance test.",
    )
    _write(tmp_path / "content" / "filler.md", "Unrelated cooking recipe without evaluation metrics.")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    res = ContextRetriever(corpus).retrieve(
        RetrievalRequest(
            domain=RetrievalDomain.IMPROVEMENT,
            profile="improvement_eval",
            query="acceptance evaluation metrics sandbox variant trigger coverage",
            max_chunks=2,
            use_sparse_only=True,
        )
    )
    assert res.status == RetrievalStatus.OK
    eval_hits = [h for h in res.hits if h.content_class == ContentClass.EVALUATION_ARTIFACT.value]
    assert eval_hits
    assert eval_hits[0].source_evidence_lane == SourceEvidenceLane.EVALUATIVE.value
    assert "evaluative_lane_preferred" in eval_hits[0].policy_note


def test_governance_view_matches_ingested_paths(tmp_path: Path) -> None:
    """Sanity: governance_view_for_chunk classifies published vs modules paths on stored chunks."""
    _write(tmp_path / "content" / "published" / "x" / "a.md", "published body")
    _write(tmp_path / "content" / "modules" / "x" / "b.md", "modules body")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    by_path = {c.source_path.replace("\\", "/"): c for c in corpus.chunks}
    assert governance_view_for_chunk(by_path["content/published/x/a.md"]).evidence_lane == SourceEvidenceLane.CANONICAL
    assert governance_view_for_chunk(by_path["content/modules/x/b.md"]).evidence_lane == SourceEvidenceLane.DRAFT_WORKING
