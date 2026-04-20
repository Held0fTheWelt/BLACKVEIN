from __future__ import annotations

from pathlib import Path

import pytest

from ai_stack import (
    RETRIEVAL_TRACE_SCHEMA_VERSION,
    CapabilityAccessDeniedError,
    CapabilityInvocationError,
    CapabilityValidationError,
    ContextPackAssembler,
    ContextRetriever,
    RagIngestionPipeline,
    build_retrieval_trace,
    create_default_capability_registry,
)


def test_build_retrieval_trace_evidence_tier_uses_hit_count_and_top_score() -> None:
    assert build_retrieval_trace({"hit_count": 0, "status": "ok"})["evidence_tier"] == "none"
    assert build_retrieval_trace({"hit_count": 1, "status": "ok", "top_hit_score": "3.0"})["evidence_tier"] == "weak"
    assert build_retrieval_trace({"hit_count": 1, "status": "ok", "top_hit_score": "9.0"})["evidence_tier"] == "strong"
    assert build_retrieval_trace({"hit_count": 2, "status": "ok", "top_hit_score": "5.0"})["evidence_tier"] == "moderate"
    assert build_retrieval_trace({"hit_count": 2, "status": "ok", "top_hit_score": "8.0"})["evidence_tier"] == "strong"
    # Task 4: multi-hit is not strong from count alone without hybrid backing signals.
    assert build_retrieval_trace({"hit_count": 4, "status": "ok"})["evidence_tier"] == "moderate"
    canon_row = {"source_evidence_lane": "canonical"}
    sup_row = {"source_evidence_lane": "supporting"}
    thin = build_retrieval_trace(
        {
            "hit_count": 4,
            "status": "ok",
            "retrieval_route": "hybrid",
            "top_hit_score": "7.5",
            "sources": [canon_row, sup_row, sup_row, sup_row],
        }
    )
    assert thin["evidence_tier"] == "moderate"
    assert "capped_thin_canonical_anchor_density" in thin["evidence_rationale"]
    assert (
        build_retrieval_trace(
            {
                "hit_count": 4,
                "status": "ok",
                "retrieval_route": "hybrid",
                "top_hit_score": "7.5",
                "sources": [canon_row, canon_row, canon_row, canon_row],
            }
        )["evidence_tier"]
        == "strong"
    )
    sparse_many = build_retrieval_trace(
        {
            "hit_count": 3,
            "status": "ok",
            "retrieval_route": "sparse_fallback",
            "top_hit_score": "9.0",
            "sources": [sup_row, sup_row, sup_row],
        }
    )
    assert sparse_many["evidence_tier"] == "moderate"
    assert "sparse_route_multi_hit_context" in sparse_many["evidence_rationale"]
    degraded_cap = build_retrieval_trace(
        {
            "hit_count": 4,
            "status": "ok",
            "retrieval_route": "hybrid",
            "top_hit_score": "9.0",
            "degradation_mode": "degraded_due_to_partial_persistence_problem",
            "sources": [canon_row, canon_row, canon_row, canon_row],
        }
    )
    assert degraded_cap["evidence_tier"] == "moderate"
    assert "capped_degraded_path" in degraded_cap["evidence_rationale"]
    trace = build_retrieval_trace(None)
    assert trace["evidence_strength"] == trace["evidence_tier"] == "none"
    assert trace.get("evidence_rationale")
    assert trace.get("retrieval_trace_schema_version") == RETRIEVAL_TRACE_SCHEMA_VERSION
    assert trace.get("evidence_lane_mix") == "unknown"


def test_build_retrieval_trace_compact_governance_hints() -> None:
    t = build_retrieval_trace(
        {
            "hit_count": 2,
            "status": "ok",
            "top_hit_score": "8.0",
            "retrieval_route": "sparse_fallback",
            "ranking_notes": ["policy_hard_excluded_pool_count=2", "dup_suppressed chunk_id=x (test)"],
            "sources": [
                {"source_evidence_lane": "canonical"},
                {"source_evidence_lane": "canonical"},
            ],
        }
    )
    assert t["policy_outcome_hint"] == "hard_pool_exclusions_applied"
    assert t["hard_policy_exclusion_count"] == 2
    assert t["dedup_shaped_selection"] is True
    assert t["evidence_lane_mix"] == "canonical_heavy"
    assert "sparse_signal_path" in t["retrieval_quality_hint"]
    assert t["evidence_tier"] == "moderate"
    assert "capped_policy_hard_pool_reshape" in t["evidence_rationale"]
    assert t["confidence_posture"] == "low"
    assert t.get("retrieval_posture_summary")
    assert t["readiness_label"].startswith("confidence=")


def test_build_retrieval_trace_passthrough_retrieval_governance_summary() -> None:
    from ai_stack.retrieval_governance_summary import summarize_retrieval_governance_from_hit_rows

    sources = [
        {
            "chunk_id": "z1",
            "source_path": "x.md",
            "source_evidence_lane": "canonical",
            "source_visibility_class": "runtime_safe",
            "content_class": "authored_module",
        }
    ]
    summary = summarize_retrieval_governance_from_hit_rows(sources)
    retrieval = {
        "hit_count": 1,
        "status": "ok",
        "sources": sources,
        "retrieval_governance_summary": summary,
    }
    trace = build_retrieval_trace(retrieval)
    assert trace.get("retrieval_governance_summary") is summary


def test_context_pack_audit_summary_includes_tier_and_transcript_impact(tmp_path: Path) -> None:
    registry = _build_registry(tmp_path)
    registry.invoke(
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
    audit = registry.recent_audit(limit=1)[0]
    summary = audit.get("result_summary") or {}
    assert summary.get("evidence_tier") in {"none", "weak", "moderate", "strong"}
    assert summary.get("evidence_rationale")
    assert summary.get("retrieval_trace_schema_version") == RETRIEVAL_TRACE_SCHEMA_VERSION
    assert summary.get("evidence_lane_mix") in {
        None,
        "unknown",
        "canonical_heavy",
        "mixed",
        "supporting_heavy",
        "evaluative_present",
        "evaluative_mixed",
    }

    with pytest.raises(CapabilityInvocationError):
        registry.invoke(
            name="wos.transcript.read",
            mode="improvement",
            actor="improvement:test",
            payload={"run_id": "synthetic_run"},
        )
    t_audits = [a for a in registry.recent_audit(limit=10) if a["capability_name"] == "wos.transcript.read"]
    assert t_audits[-1]["outcome"] == "error"


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
    """``wos.transcript.read`` is registered for improvement (and other) modes.

    A missing run file must raise ``CapabilityInvocationError`` with ``run_not_found``.
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
    if result["retrieval"].get("hit_count", 0) > 0:
        src0 = result["retrieval"]["sources"][0]
        assert "pack_role" in src0
        assert "why_selected" in src0
        assert result["retrieval"].get("retrieval_policy_version")
        assert src0.get("source_evidence_lane")
        assert src0.get("policy_note")


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
    assert summary.get("workflow_impact") == "feeds_governance_review_package"


def test_transcript_read_success_audit_records_parsed_turn_counts(tmp_path: Path) -> None:
    run_id = "fixture_run"
    run_path = tmp_path / "world-engine" / "app" / "var" / "runs" / f"{run_id}.json"
    run_path.parent.mkdir(parents=True, exist_ok=True)
    run_path.write_text(
        '{"transcript":[{"player_input":"hello","repetition_flag":false},{"player_input":"again","repetition_flag":true}]}',
        encoding="utf-8",
    )
    registry = _build_registry(tmp_path)
    registry.invoke(
        name="wos.transcript.read",
        mode="improvement",
        actor="improvement:test",
        payload={"run_id": run_id},
    )
    audit = registry.recent_audit(limit=1)[0]
    assert audit["outcome"] == "allowed"
    assert audit["result_summary"]["transcript_turn_count"] == 2
    assert audit["result_summary"]["repetition_turn_count"] == 1
    assert audit["result_summary"]["workflow_impact"] == "drives_improvement_recommendation_suffix"


def test_research_explore_capability_requires_valid_budget(tmp_path: Path) -> None:
    registry = _build_registry(tmp_path)
    with pytest.raises(CapabilityInvocationError):
        registry.invoke(
            name="wos.research.explore",
            mode="improvement",
            actor="improvement:test",
            payload={
                "work_id": "god_of_carnage",
                "module_id": "god_of_carnage",
                "source_inputs": [
                    {
                        "source_type": "scene_note",
                        "title": "fixture",
                        "raw_text": "scene pressure rises with tactic shift",
                        "provenance": {"origin": "test"},
                        "visibility": "internal",
                        "copyright_posture": "internal_approved",
                        "metadata": {"fixture": "cap-neg"},
                    }
                ],
                "seed_question": "where is escalation weak",
                "budget": {},
            },
        )
