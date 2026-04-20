"""Named retrieval evaluation scenarios (closure harness).

Deterministic fixtures only; not imported by production runtime paths.
Each scenario documents expected governance, trace, and packing behavior for regression tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_stack.capabilities import RETRIEVAL_TRACE_SCHEMA_VERSION, build_retrieval_trace
from ai_stack.rag import (
    RETRIEVAL_POLICY_VERSION,
    ContextPackAssembler,
    ContextRetriever,
    RagIngestionPipeline,
    RetrievalDomain,
    RetrievalRequest,
    SourceEvidenceLane,
)
def _write_eval_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@dataclass(frozen=True, slots=True)
class RetrievalEvalScenario:
    """Stable evaluation case: setup files + request + explicit expectations."""

    id: str
    description: str
    files: tuple[tuple[str, str], ...]
    domain: RetrievalDomain
    profile: str
    query: str
    module_id: str | None
    max_chunks: int
    use_sparse_only: bool = True
    expect_min_hits: int = 1
    expect_top_path_substr: str | None = None
    expect_top_path_in: frozenset[str] | None = None
    forbid_path_substr: str | None = None
    expect_pack_section_substr: str | None = None
    expect_ranking_note_substr: str | None = None
    expect_first_hit_lane: str | None = None
    expect_trace_lane_mix: str | None = None
    expect_trace_lane_mix_in: frozenset[str] | None = None
    expect_trace_policy_hint: str | None = None
    expect_retrieval_route: str | None = None
    expect_dedup_in_trace: bool | None = None
    expect_first_hit_visibility: str | None = None
    expect_evidence_tier: str | None = None
    expect_top_pack_role: str | None = None
    expect_context_contains: str | None = None


def _apply_files(tmp_path: Path, files: tuple[tuple[str, str], ...]) -> None:
    for rel, body in files:
        _write_eval_file(tmp_path / rel, body)


def run_scenario(tmp_path: Path, scenario: RetrievalEvalScenario) -> tuple[Any, Any]:
    _apply_files(tmp_path, scenario.files)
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    assembler = ContextPackAssembler()
    req = RetrievalRequest(
        domain=scenario.domain,
        profile=scenario.profile,
        query=scenario.query,
        module_id=scenario.module_id,
        max_chunks=scenario.max_chunks,
        use_sparse_only=scenario.use_sparse_only,
    )
    result = retriever.retrieve(req)
    pack = assembler.assemble(result)
    return result, pack


def retrieval_dict_like_capability(pack: Any, result: Any) -> dict[str, Any]:
    """Mirror ``wos.context_pack.build`` retrieval dict shape for trace evaluation."""
    top_score = ""
    if pack.sources:
        top_score = str(pack.sources[0].get("score", ""))
    return {
        "domain": pack.domain,
        "profile": pack.profile,
        "status": pack.status,
        "hit_count": pack.hit_count,
        "sources": pack.sources,
        "ranking_notes": pack.ranking_notes,
        "index_version": pack.index_version,
        "corpus_fingerprint": pack.corpus_fingerprint,
        "storage_path": pack.storage_path,
        "retrieval_route": pack.retrieval_route,
        "embedding_model_id": pack.embedding_model_id,
        "top_hit_score": top_score,
        "degradation_mode": pack.degradation_mode,
        "dense_index_build_action": pack.dense_index_build_action,
        "dense_rebuild_reason": pack.dense_rebuild_reason,
        "dense_artifact_validity": pack.dense_artifact_validity,
        "embedding_reason_codes": list(pack.embedding_reason_codes),
        "embedding_index_version": pack.embedding_index_version,
        "embedding_cache_dir_identity": pack.embedding_cache_dir_identity,
        "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
    }


def assert_scenario(tmp_path: Path, scenario: RetrievalEvalScenario) -> None:
    result, pack = run_scenario(tmp_path, scenario)
    assert len(result.hits) >= scenario.expect_min_hits, (
        f"[{scenario.id}] expected at least {scenario.expect_min_hits} hits, got {len(result.hits)}"
    )
    if scenario.expect_top_path_substr:
        top = result.hits[0].source_path.replace("\\", "/")
        assert scenario.expect_top_path_substr in top, f"[{scenario.id}] top hit path {top!r}"
    if scenario.expect_top_path_in:
        top = result.hits[0].source_path.replace("\\", "/")
        assert any(x in top for x in scenario.expect_top_path_in), f"[{scenario.id}] top {top!r}"
    if scenario.forbid_path_substr:
        for h in result.hits:
            p = h.source_path.replace("\\", "/")
            assert scenario.forbid_path_substr not in p, f"[{scenario.id}] forbidden path {p!r}"
    if scenario.expect_pack_section_substr:
        assert scenario.expect_pack_section_substr in pack.compact_context, f"[{scenario.id}] pack text"
    if scenario.expect_ranking_note_substr:
        joined = " ".join(result.ranking_notes)
        assert scenario.expect_ranking_note_substr in joined, f"[{scenario.id}] ranking notes"
    if scenario.expect_first_hit_lane:
        assert result.hits[0].source_evidence_lane == scenario.expect_first_hit_lane, (
            f"[{scenario.id}] first lane {result.hits[0].source_evidence_lane!r}"
        )
    rdict = retrieval_dict_like_capability(pack, result)
    trace = build_retrieval_trace(rdict)
    if scenario.expect_trace_lane_mix:
        assert trace.get("evidence_lane_mix") == scenario.expect_trace_lane_mix, (
            f"[{scenario.id}] lane_mix={trace.get('evidence_lane_mix')!r}"
        )
    if scenario.expect_trace_lane_mix_in:
        assert trace.get("evidence_lane_mix") in scenario.expect_trace_lane_mix_in, (
            f"[{scenario.id}] lane_mix={trace.get('evidence_lane_mix')!r}"
        )
    if scenario.expect_trace_policy_hint:
        assert trace.get("policy_outcome_hint") == scenario.expect_trace_policy_hint, (
            f"[{scenario.id}] policy hint {trace.get('policy_outcome_hint')!r}"
        )
    assert trace.get("readiness_label"), f"[{scenario.id}] missing readiness_label"
    if scenario.expect_retrieval_route:
        assert rdict.get("retrieval_route") == scenario.expect_retrieval_route, (
            f"[{scenario.id}] route={rdict.get('retrieval_route')!r}"
        )
    if scenario.expect_dedup_in_trace is not None:
        assert trace.get("dedup_shaped_selection") is scenario.expect_dedup_in_trace, (
            f"[{scenario.id}] dedup_shaped_selection={trace.get('dedup_shaped_selection')!r}"
        )
    if scenario.expect_first_hit_visibility:
        assert result.hits[0].source_visibility_class == scenario.expect_first_hit_visibility, (
            f"[{scenario.id}] visibility {result.hits[0].source_visibility_class!r}"
        )
    if scenario.expect_evidence_tier:
        assert trace.get("evidence_tier") == scenario.expect_evidence_tier, (
            f"[{scenario.id}] tier={trace.get('evidence_tier')!r}"
        )
    if scenario.expect_top_pack_role:
        assert result.hits[0].pack_role == scenario.expect_top_pack_role, (
            f"[{scenario.id}] pack_role={result.hits[0].pack_role!r}"
        )
    if scenario.expect_context_contains:
        assert scenario.expect_context_contains in pack.compact_context, (
            f"[{scenario.id}] missing {scenario.expect_context_contains!r} in pack"
        )
    assert trace.get("retrieval_trace_schema_version") == RETRIEVAL_TRACE_SCHEMA_VERSION, (
        f"[{scenario.id}] schema {trace.get('retrieval_trace_schema_version')!r}"
    )
    assert trace.get("confidence_posture"), f"[{scenario.id}] missing confidence_posture"
    assert trace.get("retrieval_posture_summary"), f"[{scenario.id}] missing retrieval_posture_summary"


SHARED_KEYWORDS = (
    "dinner dispute families civility collapse chaos escalation unique eval scenario tokens."
)

RETRIEVAL_EVAL_SCENARIOS: tuple[RetrievalEvalScenario, ...] = (
    RetrievalEvalScenario(
        id="runtime_canonical_over_draft_when_both_in_pool",
        description="Runtime should rank published canonical above module draft for the same module.",
        files=(
            ("content/modules/rc_mod/draft.md", f"Draft rc_mod {SHARED_KEYWORDS}"),
            ("content/published/rc_mod/canon.md", f"Published rc_mod canon {SHARED_KEYWORDS}"),
        ),
        domain=RetrievalDomain.RUNTIME,
        profile="runtime_turn_support",
        query="rc_mod dinner dispute families civility collapse chaos escalation",
        module_id="rc_mod",
        max_chunks=2,
        expect_top_path_substr="content/published/rc_mod/",
        expect_pack_section_substr="Canonical evidence",
        expect_first_hit_lane=SourceEvidenceLane.CANONICAL.value,
        expect_trace_lane_mix="canonical_heavy",
    ),
    RetrievalEvalScenario(
        id="runtime_hides_evaluative_artifacts",
        description="Runtime domain must not return evaluation_artifact class chunks.",
        files=(
            ("docs/reports/runtime_eval_hidden.md", f"Evaluation artifact {SHARED_KEYWORDS} red flags."),
            ("content/published/hm/hid.md", f"Published hm {SHARED_KEYWORDS}"),
        ),
        domain=RetrievalDomain.RUNTIME,
        profile="runtime_turn_support",
        query="runtime_eval_hidden red flags evaluation artifact",
        module_id="hm",
        max_chunks=3,
        expect_min_hits=1,
        forbid_path_substr="docs/reports/runtime_eval_hidden",
        expect_top_path_substr="content/published/hm/",
        expect_first_hit_lane=SourceEvidenceLane.CANONICAL.value,
        expect_trace_lane_mix="canonical_heavy",
    ),
    RetrievalEvalScenario(
        id="writers_room_sees_review_notes",
        description="Writers-Room profile may retrieve review_note content excluded from runtime.",
        files=(
            ("docs/reports/wr_review_only.md", f"Review note remediation {SHARED_KEYWORDS} writers visibility."),
        ),
        domain=RetrievalDomain.WRITERS_ROOM,
        profile="writers_review",
        query="writers review note remediation unique eval scenario",
        module_id=None,
        max_chunks=2,
        expect_min_hits=1,
        expect_top_path_substr="docs/reports/wr_review_only",
        expect_pack_section_substr="Review context",
    ),
    RetrievalEvalScenario(
        id="improvement_surfaces_evaluative_lane",
        description="Improvement domain retrieves evaluation artifacts with evaluative lane metadata.",
        files=(
            ("docs/reports/imp_eval_surface.md", f"Acceptance evaluation metrics {SHARED_KEYWORDS} sandbox."),
            ("content/filler_noise.md", "Cooking recipe without evaluation metrics."),
        ),
        domain=RetrievalDomain.IMPROVEMENT,
        profile="improvement_eval",
        query="acceptance evaluation metrics sandbox unique eval scenario",
        module_id=None,
        max_chunks=2,
        expect_min_hits=1,
        expect_top_path_substr="docs/reports/imp_eval_surface",
        expect_pack_section_substr="Evaluative evidence",
        expect_trace_lane_mix_in=frozenset({"evaluative_present", "evaluative_mixed"}),
    ),
    RetrievalEvalScenario(
        id="duplicate_suppression_improvement",
        description="Near-duplicate bodies should collapse so only one consumes a hit slot.",
        files=(
            ("content/dup_a.md", "Unique evaluation trigger coverage sandbox variant metrics acceptance story."),
            ("content/dup_b.md", "Unique evaluation trigger coverage sandbox variant metrics acceptance story. "),
        ),
        domain=RetrievalDomain.IMPROVEMENT,
        profile="improvement_eval",
        query="evaluation trigger coverage sandbox variant metrics acceptance",
        module_id=None,
        max_chunks=3,
        expect_min_hits=1,
        expect_ranking_note_substr="dup_suppressed",
        expect_dedup_in_trace=True,
    ),
    RetrievalEvalScenario(
        id="sparse_route_recorded_for_operators",
        description="Sparse-only retrieval keeps explicit route in notes and trace.",
        files=(("content/sparse_only_body.md", f"Sparse route body {SHARED_KEYWORDS}"),),
        domain=RetrievalDomain.RUNTIME,
        profile="runtime_turn_support",
        query="sparse route body unique eval scenario",
        module_id=None,
        max_chunks=1,
        expect_ranking_note_substr="retrieval_route=sparse_fallback",
        expect_retrieval_route="sparse_fallback",
    ),
    RetrievalEvalScenario(
        id="runtime_hard_exclusion_when_published_canonical_present",
        description="Runtime hard gate removes same-module draft when published canonical is in pool.",
        files=(
            ("content/modules/gate_mod/draft.md", SHARED_KEYWORDS),
            ("content/published/gate_mod/canon.md", SHARED_KEYWORDS),
        ),
        domain=RetrievalDomain.RUNTIME,
        profile="runtime_turn_support",
        query="dinner dispute families civility collapse chaos escalation unique eval scenario gate",
        module_id="gate_mod",
        max_chunks=2,
        expect_ranking_note_substr="policy_hard_excluded_pool_count=",
        forbid_path_substr="content/modules/gate_mod/draft.md",
        expect_trace_policy_hint="hard_pool_exclusions_applied",
        expect_evidence_tier="moderate",
        expect_context_contains="pack_trace_summary:",
    ),
    RetrievalEvalScenario(
        id="writers_room_internal_review_lane_metadata",
        description="Writers-Room review_note chunks expose internal_review lane and writers_working visibility.",
        files=(
            ("docs/reports/wr_internal_note.md", f"Internal board note remediation {SHARED_KEYWORDS} visibility."),
        ),
        domain=RetrievalDomain.WRITERS_ROOM,
        profile="writers_review",
        query="internal board note remediation unique eval scenario",
        module_id=None,
        max_chunks=2,
        expect_min_hits=1,
        expect_top_path_substr="docs/reports/wr_internal_note",
        expect_first_hit_lane=SourceEvidenceLane.INTERNAL_REVIEW.value,
        expect_first_hit_visibility="writers_working",
        expect_pack_section_substr="Review context",
        expect_top_pack_role="review_context",
        expect_context_contains="pack_trace_summary:",
    ),
)


@dataclass(frozen=True, slots=True)
class RetrievalTraceEvalCase:
    """Deterministic ``build_retrieval_trace`` inputs (no corpus I/O)."""

    id: str
    description: str
    retrieval: dict[str, Any]
    expect_tier: str
    expect_confidence: str
    rationale_substr: str = ""


def assert_trace_eval_case(case: RetrievalTraceEvalCase) -> None:
    tr = build_retrieval_trace(case.retrieval)
    assert tr["evidence_tier"] == case.expect_tier, f"[{case.id}] tier={tr['evidence_tier']!r}"
    assert tr["confidence_posture"] == case.expect_confidence, f"[{case.id}] conf={tr['confidence_posture']!r}"
    assert tr.get("retrieval_posture_summary"), f"[{case.id}] missing posture summary"
    assert tr.get("lane_anchor_counts") is not None, f"[{case.id}] missing lane_anchor_counts"
    if case.rationale_substr:
        assert case.rationale_substr in tr["evidence_rationale"], (
            f"[{case.id}] rationale={tr['evidence_rationale']!r}"
        )
    assert tr["retrieval_trace_schema_version"] == RETRIEVAL_TRACE_SCHEMA_VERSION, f"[{case.id}] schema"


RETRIEVAL_TRACE_EVAL_CASES: tuple[RetrievalTraceEvalCase, ...] = (
    RetrievalTraceEvalCase(
        id="trace_degraded_path_caps_multi_hit_strong",
        description="Persisted degradation marker caps strong multi-hit hybrid tier.",
        retrieval={
            "hit_count": 4,
            "status": "ok",
            "retrieval_route": "hybrid",
            "top_hit_score": "9.0",
            "degradation_mode": "degraded_due_to_partial_persistence_problem",
            "sources": [{"source_evidence_lane": "canonical"}] * 4,
        },
        expect_tier="moderate",
        expect_confidence="low",
        rationale_substr="capped_degraded_path",
    ),
    RetrievalTraceEvalCase(
        id="trace_policy_hard_exclusion_caps_two_hit_strong",
        description="Hard pool exclusions reshape selection; tier must not read as uncapped strong.",
        retrieval={
            "hit_count": 2,
            "status": "ok",
            "retrieval_route": "hybrid",
            "top_hit_score": "8.0",
            "ranking_notes": ["policy_hard_excluded_pool_count=1"],
            "sources": [
                {"source_evidence_lane": "canonical"},
                {"source_evidence_lane": "canonical"},
            ],
        },
        expect_tier="moderate",
        expect_confidence="medium",
        rationale_substr="capped_policy_hard_pool_reshape",
    ),
    RetrievalTraceEvalCase(
        id="trace_sparse_multi_hit_supporting_scores_context_note",
        description="Sparse-only multi-hit adds context note in rationale without claiming strong-by-count.",
        retrieval={
            "hit_count": 3,
            "status": "ok",
            "retrieval_route": "sparse_fallback",
            "top_hit_score": "9.0",
            "sources": [
                {"source_evidence_lane": "supporting"},
                {"source_evidence_lane": "supporting"},
                {"source_evidence_lane": "supporting"},
            ],
        },
        expect_tier="moderate",
        expect_confidence="low",
        rationale_substr="sparse_route_multi_hit_context",
    ),
)
