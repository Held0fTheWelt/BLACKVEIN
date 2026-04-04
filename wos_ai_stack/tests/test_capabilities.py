from __future__ import annotations

from pathlib import Path

import pytest

from wos_ai_stack import (
    CapabilityAccessDeniedError,
    CapabilityInvocationError,
    CapabilityValidationError,
    ContextPackAssembler,
    ContextRetriever,
    RagIngestionPipeline,
    build_retrieval_trace,
    create_default_capability_registry,
)


def test_build_retrieval_trace_evidence_strength_follows_hit_count() -> None:
    assert build_retrieval_trace({"hit_count": 2, "status": "ok"})["evidence_strength"] == "strong"
    assert build_retrieval_trace({"hit_count": 0, "status": "ok"})["evidence_strength"] == "none"
    assert build_retrieval_trace(None)["evidence_strength"] == "none"


def _build_registry(tmp_path: Path):
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage capability retrieval sample.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    assembler = ContextPackAssembler()
    return create_default_capability_registry(retriever=retriever, assembler=assembler, repo_root=tmp_path)


def test_capability_registration_exposes_schema_and_modes(tmp_path: Path) -> None:
    registry = _build_registry(tmp_path)
    capabilities = registry.list_capabilities()

    assert any(cap["name"] == "wos.context_pack.build" for cap in capabilities)
    context_pack_cap = next(cap for cap in capabilities if cap["name"] == "wos.context_pack.build")
    assert "profile" in context_pack_cap["input_schema"]["required"]
    assert "runtime" in context_pack_cap["allowed_modes"]


def test_capability_denied_access_is_typed_and_audited(tmp_path: Path) -> None:
    registry = _build_registry(tmp_path)
    with pytest.raises(CapabilityAccessDeniedError):
        registry.invoke(
            name="wos.review_bundle.build",
            mode="runtime",
            actor="runtime_turn_graph",
            payload={"module_id": "god_of_carnage"},
        )
    audit = registry.recent_audit(limit=1)[0]
    assert audit["outcome"] == "denied"
    assert audit["capability_name"] == "wos.review_bundle.build"
    assert audit.get("result_summary") is None


def test_capability_validation_failure_is_typed_and_audited(tmp_path: Path) -> None:
    registry = _build_registry(tmp_path)
    with pytest.raises(CapabilityValidationError):
        registry.invoke(
            name="wos.context_pack.build",
            mode="runtime",
            actor="runtime_turn_graph",
            payload={"query": "missing profile"},
        )
    audit = registry.recent_audit(limit=1)[0]
    assert audit["outcome"] == "error"
    assert audit.get("result_summary") is None


def test_transcript_read_capability_is_registered_and_invocable(tmp_path: Path) -> None:
    """Proves wos.transcript.read is registered and invocable even though it is not yet
    integrated into active workflows (aspirational capability documented in capabilities.py).

    Invoking with a missing run file must raise CapabilityInvocationError — an honest behavior
    that confirms the handler executes and surfaces the run_not_found error path.
    """
    registry = _build_registry(tmp_path)

    # Verify the capability is listed with correct modes
    capabilities = registry.list_capabilities()
    transcript_cap = next((cap for cap in capabilities if cap["name"] == "wos.transcript.read"), None)
    assert transcript_cap is not None
    assert "improvement" in transcript_cap["allowed_modes"]
    assert "runtime" in transcript_cap["allowed_modes"]
    assert "admin" in transcript_cap["allowed_modes"]

    # Invoke with a mode it allows; the run file does not exist so it raises CapabilityInvocationError
    with pytest.raises(CapabilityInvocationError) as exc_info:
        registry.invoke(
            name="wos.transcript.read",
            mode="improvement",
            actor="improvement:test",
            payload={"run_id": "nonexistent_run_00000"},
        )
    assert "run_not_found" in str(exc_info.value)

    # Confirm the invocation was audited
    audit = registry.recent_audit(limit=1)[0]
    assert audit["capability_name"] == "wos.transcript.read"
    assert audit["outcome"] == "error"


def test_runtime_context_pack_capability_returns_retrieval_payload(tmp_path: Path) -> None:
    registry = _build_registry(tmp_path)
    result = registry.invoke(
        name="wos.context_pack.build",
        mode="runtime",
        actor="runtime_turn_graph",
        payload={
            "domain": "runtime",
            "profile": "runtime_turn_support",
            "query": "god of carnage sample",
            "module_id": "god_of_carnage",
            "scene_id": "scene_1",
        },
    )

    assert "retrieval" in result
    assert result["retrieval"]["profile"] == "runtime_turn_support"
    assert "context_text" in result
    audit = registry.recent_audit(limit=1)[0]
    assert audit["outcome"] == "allowed"
    assert audit.get("result_summary") is not None
    assert audit["result_summary"]["kind"] == "context_pack"
    assert audit["result_summary"]["hit_count"] >= 0
    assert audit["result_summary"]["domain"] == "runtime"
    assert audit["result_summary"]["profile"] == "runtime_turn_support"


def test_review_bundle_audit_includes_evidence_source_count(tmp_path: Path) -> None:
    registry = _build_registry(tmp_path)
    registry.invoke(
        name="wos.review_bundle.build",
        mode="improvement",
        actor="improvement:test",
        payload={
            "module_id": "god_of_carnage",
            "summary": "[evidence:strong] test",
            "recommendations": ["r1"],
            "evidence_sources": ["content/a.md", "content/b.md"],
        },
    )
    audit = registry.recent_audit(limit=1)[0]
    assert audit["outcome"] == "allowed"
    summary = audit.get("result_summary")
    assert summary is not None
    assert summary["kind"] == "review_bundle"
    assert summary["evidence_source_count"] == 2
