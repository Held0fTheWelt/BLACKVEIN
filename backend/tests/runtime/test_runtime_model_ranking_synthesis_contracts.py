"""Runtime ranking and synthesis: canonical staged ranking contracts (G-CANON-RANK-01 … G-CANON-RANK-08).

Each test documents pass condition and failure meaning for one canonical gate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.content.module_models import ContentModule, ModuleMetadata
from app.runtime.adapter_registry import clear_registry, register_adapter_model
from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.ai_turn_executor import execute_turn_with_ai
from app.runtime.model_inventory_contract import RUNTIME_STAGED_REQUIRED, RequiredRoutingTuple
from app.runtime.model_routing_contracts import TaskKind, WorkflowPhase
from app.runtime.operator_audit import RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS
from app.runtime.runtime_ai_stages import (
    RANKING_SLM_ONLY_SKIP_REASON,
    RankingStageOutput,
    RuntimeStageId,
    SignalStageOutput,
    build_ranking_routing_request,
    build_synthesis_routing_request,
    compute_synthesis_gate_after_ranking,
    parse_ranking_payload,
)
from app.runtime.runtime_models import SessionState

from .doc_test_paths import architecture_style_doc
from .test_runtime_staged_orchestration import StagedRecordingAdapter, _llm_spec, _slm_spec


REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_STRAT = architecture_style_doc("llm_slm_role_stratification.md")
DOCS_CONTRACT = architecture_style_doc("ai_story_contract.md")
DOCS_CLOSURE = architecture_style_doc("area2_runtime_ranking_closure_report.md")


def _assert_compact_ranking_operator_equality(*, audit: dict, summary: dict) -> None:
    """G-CANON-RANK-04: both audit_summary and legibility.runtime_ranking_summary mirror orchestration."""
    aus = audit.get("audit_summary") or {}
    for k in RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS:
        assert k in aus, f"audit_summary missing compact ranking field {k}"
        assert k in summary, f"orchestration summary missing {k} (source of truth)"
        assert aus[k] == summary[k]
    truth = audit.get("area2_operator_truth") or {}
    rr = (truth.get("legibility") or {}).get("runtime_ranking_summary")
    assert isinstance(rr, dict), "legibility.runtime_ranking_summary must be a dict for staged runtime"
    for k in RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS:
        assert rr.get(k) == summary.get(k)


def _assert_canonical_ranking_truth_surfaces(log: object) -> None:
    """Ranking must be first-class in traces, summary, and legacy rollup (G-CANON-RANK-03 / -05)."""
    traces = getattr(log, "runtime_stage_traces", None) or []
    summary = getattr(log, "runtime_orchestration_summary", None) or {}
    rollup = getattr(log, "model_routing_trace", None) or {}
    ids = [t.get("stage_id") for t in traces if isinstance(t, dict)]
    assert "ranking" in ids
    assert "ranking_effect" in summary
    rc = rollup.get("ranking_context")
    assert isinstance(rc, dict), "model_routing_trace must include ranking_context dict"


@pytest.fixture
def minimal_module() -> ContentModule:
    meta = ModuleMetadata(
        module_id="m1",
        title="T",
        version="1",
        contract_version="1.0.0",
    )
    return ContentModule(metadata=meta, scenes={}, characters={})


def test_runtime_ranking_stage_id_is_canonical():
    """G-CANON-RANK-01: Ranking is an explicit canonical Runtime stage in the staged flow.

    Pass: ``RuntimeStageId.ranking`` exists with value ``ranking``.
    Fail: Ranking missing or aliased to another stage id.
    """

    assert hasattr(RuntimeStageId, "ranking")
    assert RuntimeStageId.ranking.value == "ranking"


@pytest.mark.asyncio
async def test_runtime_ranking_follows_signal_before_synthesis_in_stages(minimal_module: ContentModule):
    """G-CANON-RANK-01: In canonical staged execution, ranking follows signal and precedes synthesis trace rows."""

    clear_registry()
    ad = StagedRecordingAdapter("canon01", slm_sufficient=False)
    llm = StagedRecordingAdapter("canon01_llm", slm_sufficient=False)
    register_adapter_model(_slm_spec("canon01"), ad)
    register_adapter_model(_llm_spec("canon01_llm"), llm)
    session = SessionState(
        session_id="canon01",
        execution_mode="ai",
        adapter_name="canon01",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}
    await execute_turn_with_ai(session, 1, ad, minimal_module)
    log = (session.metadata.get("ai_decision_logs") or [])[-1]
    ids = [t.get("stage_id") for t in log.runtime_stage_traces or [] if isinstance(t, dict)]
    assert ids.count("ranking") == 1
    si = ids.index("signal_consistency")
    ri = ids.index("ranking")
    assert ri > si
    if "synthesis" in ids:
        assert ids.index("synthesis") > ri
    clear_registry()


def test_runtime_ranking_signal_and_synthesis_routing_contracts_distinct():
    """G-CANON-RANK-02: Signal, ranking, and synthesis are semantically distinct contracts and routes.

    Pass: Distinct runtime_stage labels; signal holds coarse gate; ranking is interpretation narrowing;
    synthesis routing uses generation phase and narrative formulation (not ranking task kind).
    Fail: Contracts or builders collapse stages or reuse the wrong phase/task_kind.
    """

    assert SignalStageOutput.model_fields["runtime_stage"].default == "signal_consistency"
    assert RankingStageOutput.model_fields["runtime_stage"].default == "ranking"
    assert "scene_interpretation" not in RankingStageOutput.model_fields

    session = SessionState(
        session_id="c2",
        execution_mode="ai",
        adapter_name="x",
        module_id="m1",
        module_version="1",
        current_scene_id="s1",
    )
    session.canonical_state = {}
    rk = build_ranking_routing_request(session, extra_hints=[])
    syn = build_synthesis_routing_request(session)
    assert rk.workflow_phase == WorkflowPhase.interpretation
    assert rk.task_kind == TaskKind.ranking
    assert syn.workflow_phase == WorkflowPhase.generation
    assert syn.task_kind == TaskKind.narrative_formulation

    ok, err = parse_ranking_payload(
        {
            "runtime_stage": "ranking",
            "ranked_hypotheses": ["a"],
            "preferred_hypothesis_index": 0,
            "recommend_skip_synthesis": True,
            "skip_synthesis_after_ranking_reason": "clear_single_read",
            "synthesis_recommended": False,
            "ambiguity_residual": 0.1,
            "ranking_confidence": 0.9,
            "ranking_notes": [],
        }
    )
    assert ok is not None and not err

    bad, err2 = parse_ranking_payload({"runtime_stage": "ranking", "recommend_skip_synthesis": True})
    assert bad is None and err2


@pytest.mark.asyncio
async def test_runtime_ranking_surfaces_in_traces_summary_rollup_and_audit(minimal_module: ContentModule):
    """G-CANON-RANK-03: Ranking appears in traces, orchestration summary, rollup, and audit timeline.

    Pass: ``ranking`` stage_id row; ``ranking_effect`` in summary; ``ranking_context`` on rollup;
    audit timeline includes ``stage_key`` ranking.
    Fail: Ranking only in deep traces while missing summary, rollup, or audit.
    """

    clear_registry()
    ad = StagedRecordingAdapter("c3", slm_sufficient=True)
    register_adapter_model(_slm_spec("c3"), ad)
    session = SessionState(
        session_id="c3",
        execution_mode="ai",
        adapter_name="c3",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}
    await execute_turn_with_ai(session, 1, ad, minimal_module)
    log = (session.metadata.get("ai_decision_logs") or [])[-1]
    _assert_canonical_ranking_truth_surfaces(log)
    timeline = (log.operator_audit or {}).get("audit_timeline") or []
    assert any(e.get("stage_key") == "ranking" for e in timeline)
    clear_registry()


@pytest.mark.asyncio
async def test_runtime_ranking_compact_operator_truth_matches_orchestration_summary(minimal_module: ContentModule):
    """G-CANON-RANK-04: Compact operator truth exposes ranking in audit_summary and legibility.

    Pass: Both surfaces include all ``RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS`` matching orchestration summary.
    Fail: Ranking inferable only from synthesis skip or only one compact surface populated.
    """

    clear_registry()
    ad = StagedRecordingAdapter("c4", slm_sufficient=True)
    register_adapter_model(_slm_spec("c4"), ad)
    session = SessionState(
        session_id="c4",
        execution_mode="ai",
        adapter_name="c4",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}
    await execute_turn_with_ai(session, 1, ad, minimal_module)
    log = (session.metadata.get("ai_decision_logs") or [])[-1]
    audit = log.operator_audit or {}
    summary = log.runtime_orchestration_summary or {}
    _assert_compact_ranking_operator_equality(audit=audit, summary=summary)
    clear_registry()


@pytest.mark.asyncio
async def test_runtime_ranking_surfaces_preserved_across_path_variants(minimal_module: ContentModule):
    """G-CANON-RANK-05: Important staged paths do not treat ranking as second-class (trace + summary + rollup).

    Pass: SLM-only suppression, ranked-then-LLM, ranked-skip, and degraded ranking parse each retain
    canonical ranking surfaces.
    Fail: Ranking logically present but omitted from summary, rollup, or stage traces on these paths.
    """

    clear_registry()
    skip_ad = StagedRecordingAdapter("c5_skip", slm_sufficient=False, rank_recommend_skip=True)
    register_adapter_model(_slm_spec("c5_skip"), skip_ad)
    register_adapter_model(_llm_spec("c5_skip_llm"), StagedRecordingAdapter("c5_skip_llm"))
    session = SessionState(
        session_id="c5-skip",
        execution_mode="ai",
        adapter_name="c5_skip",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}
    await execute_turn_with_ai(session, 1, skip_ad, minimal_module)
    log_skip = (session.metadata.get("ai_decision_logs") or [])[-1]
    _assert_canonical_ranking_truth_surfaces(log_skip)
    _assert_compact_ranking_operator_equality(
        audit=log_skip.operator_audit or {}, summary=log_skip.runtime_orchestration_summary or {}
    )

    clear_registry()
    keep_ad = StagedRecordingAdapter("c5_keep", slm_sufficient=False, rank_recommend_skip=False)
    llm_keep = StagedRecordingAdapter("c5_keep_llm", slm_sufficient=False)
    register_adapter_model(_slm_spec("c5_keep"), keep_ad)
    register_adapter_model(_llm_spec("c5_keep_llm"), llm_keep)
    session2 = SessionState(
        session_id="c5-keep",
        execution_mode="ai",
        adapter_name="c5_keep",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session2.canonical_state = {}
    await execute_turn_with_ai(session2, 1, keep_ad, minimal_module)
    log_keep = (session2.metadata.get("ai_decision_logs") or [])[-1]
    _assert_canonical_ranking_truth_surfaces(log_keep)
    _assert_compact_ranking_operator_equality(
        audit=log_keep.operator_audit or {}, summary=log_keep.runtime_orchestration_summary or {}
    )

    clear_registry()
    ad_slm = StagedRecordingAdapter("c5_slm", slm_sufficient=True)
    register_adapter_model(_slm_spec("c5_slm"), ad_slm)
    session3 = SessionState(
        session_id="c5-slm",
        execution_mode="ai",
        adapter_name="c5_slm",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session3.canonical_state = {}
    await execute_turn_with_ai(session3, 1, ad_slm, minimal_module)
    log_slm = (session3.metadata.get("ai_decision_logs") or [])[-1]
    _assert_canonical_ranking_truth_surfaces(log_slm)
    _assert_compact_ranking_operator_equality(
        audit=log_slm.operator_audit or {}, summary=log_slm.runtime_orchestration_summary or {}
    )

    clear_registry()

    class BadRankingGoodSignalAdapter(StoryAIAdapter):
        @property
        def adapter_name(self) -> str:
            return "c5_bad_rank"

        def generate(self, request: AdapterRequest) -> AdapterResponse:
            stage = (request.metadata or {}).get("runtime_stage") or ""
            if stage == "preflight":
                pl = {
                    "runtime_stage": "preflight",
                    "ambiguity_score": 0.1,
                    "trigger_signals": [],
                    "repetition_risk": "low",
                    "classification_label": "x",
                    "preflight_ok": True,
                }
            elif stage == "signal_consistency":
                pl = {
                    "runtime_stage": "signal_consistency",
                    "needs_llm_synthesis": True,
                    "narrative_summary": "n",
                    "consistency_notes": "",
                    "consistency_flags": [],
                }
            elif stage == "ranking":
                pl = {"runtime_stage": "ranking", "recommend_skip_synthesis": "not_bool"}
            else:
                pl = {"scene_interpretation": "x", "detected_triggers": [], "proposed_state_deltas": []}
            return AdapterResponse(raw_output=json.dumps(pl), structured_payload=pl, error=None)

    bad_ad = BadRankingGoodSignalAdapter()
    llm_deg = StagedRecordingAdapter("c5_bad_llm", slm_sufficient=False)
    register_adapter_model(_slm_spec("c5_bad_rank"), bad_ad)
    register_adapter_model(_llm_spec("c5_bad_llm"), llm_deg)
    session4 = SessionState(
        session_id="c5-deg",
        execution_mode="ai",
        adapter_name="c5_bad_rank",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session4.canonical_state = {}
    await execute_turn_with_ai(session4, 1, bad_ad, minimal_module)
    log_deg = (session4.metadata.get("ai_decision_logs") or [])[-1]
    _assert_canonical_ranking_truth_surfaces(log_deg)
    _assert_compact_ranking_operator_equality(
        audit=log_deg.operator_audit or {}, summary=log_deg.runtime_orchestration_summary or {}
    )
    clear_registry()


def test_runtime_ranking_required_in_staged_inventory_and_closure_doc():
    """G-CANON-RANK-06: Runtime staged inventory requires ranking; docs remain aligned.

    Pass: Exactly one ``(interpretation, ranking)`` tuple in ``RUNTIME_STAGED_REQUIRED``.
    Fail: Inventory or staged contract omits ranking as a required routing shape.
    """

    ranking_tuples = [
        t
        for t in RUNTIME_STAGED_REQUIRED
        if t.task_kind == TaskKind.ranking and t.workflow_phase == WorkflowPhase.interpretation
    ]
    assert len(ranking_tuples) == 1
    assert isinstance(ranking_tuples[0], RequiredRoutingTuple)
    assert "build_ranking_routing_request" in DOCS_CLOSURE.read_text(encoding="utf-8")


def test_runtime_ranking_documentation_lists_canonical_gate_ids():
    """G-CANON-RANK-07: Architecture docs and closure report describe canonical ranking (Task 1B gates).

    Pass: Stratification, story contract, and closure report reference ranking and G-CANON-RANK identifiers.
    Fail: Documentation drift from implemented canonical staged truth.
    """

    assert DOCS_STRAT.is_file()
    assert DOCS_CONTRACT.is_file()
    assert DOCS_CLOSURE.is_file()
    text = DOCS_STRAT.read_text(encoding="utf-8") + DOCS_CONTRACT.read_text(encoding="utf-8")
    assert "ranking" in text.lower()
    closure = DOCS_CLOSURE.read_text(encoding="utf-8")
    assert "G-CANON-RANK-01" in closure
    assert "non-canonical" in closure.lower() or "second-class" in closure.lower()


@pytest.mark.asyncio
async def test_runtime_ranking_paths_complete_with_guard_outcomes(minimal_module: ContentModule):
    """G-CANON-RANK-08: Canonicalizing ranking does not break execute_turn authority (guards / success).

    Pass: Ranked-skip and ranked-then-LLM paths complete with success and populated guard outcome.
    Fail: Guard, commit, or reject semantics regress on ranking-heavy paths.
    """

    import asyncio

    clear_registry()
    ad = StagedRecordingAdapter("c8a", slm_sufficient=False, rank_recommend_skip=True)
    register_adapter_model(_slm_spec("c8a"), ad)
    register_adapter_model(_llm_spec("c8a_llm"), StagedRecordingAdapter("c8a_llm"))
    session = SessionState(
        session_id="c8a",
        execution_mode="ai",
        adapter_name="c8a",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}
    r1 = await asyncio.wait_for(execute_turn_with_ai(session, 1, ad, minimal_module), timeout=30.0)
    assert r1.execution_status == "success"
    assert r1.guard_outcome is not None

    clear_registry()
    keep = StagedRecordingAdapter("c8b", slm_sufficient=False, rank_recommend_skip=False)
    llm = StagedRecordingAdapter("c8b_llm", slm_sufficient=False)
    register_adapter_model(_slm_spec("c8b"), keep)
    register_adapter_model(_llm_spec("c8b_llm"), llm)
    session2 = SessionState(
        session_id="c8b",
        execution_mode="ai",
        adapter_name="c8b",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session2.canonical_state = {}
    r2 = await asyncio.wait_for(execute_turn_with_ai(session2, 1, keep, minimal_module), timeout=30.0)
    assert r2.execution_status == "success"
    assert r2.guard_outcome is not None
    clear_registry()


@pytest.mark.asyncio
async def test_runtime_ranking_orchestration_effects_on_ranked_paths(minimal_module: ContentModule):
    """Material synthesis gate effects (ranked-skip, ranked-then-LLM, degraded ranking parse)."""

    clear_registry()
    skip_ad = StagedRecordingAdapter("orch_skip", slm_sufficient=False, rank_recommend_skip=True)
    register_adapter_model(_slm_spec("orch_skip"), skip_ad)
    register_adapter_model(_llm_spec("orch_skip_llm"), StagedRecordingAdapter("orch_skip_llm"))
    session = SessionState(
        session_id="orch-skip",
        execution_mode="ai",
        adapter_name="orch_skip",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}
    await execute_turn_with_ai(session, 1, skip_ad, minimal_module)
    log = (session.metadata.get("ai_decision_logs") or [])[-1]
    assert log.runtime_orchestration_summary.get("final_path") == "ranked_slm_only"
    assert log.runtime_orchestration_summary.get("synthesis_gate_reason") == "ranking_skip_synthesis"
    assert "synthesis" not in skip_ad.stages_seen

    clear_registry()
    keep_ad = StagedRecordingAdapter("orch_keep", slm_sufficient=False, rank_recommend_skip=False)
    llm_keep = StagedRecordingAdapter("orch_keep_llm", slm_sufficient=False)
    register_adapter_model(_slm_spec("orch_keep"), keep_ad)
    register_adapter_model(_llm_spec("orch_keep_llm"), llm_keep)
    session2 = SessionState(
        session_id="orch-keep",
        execution_mode="ai",
        adapter_name="orch_keep",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session2.canonical_state = {}
    await execute_turn_with_ai(session2, 1, keep_ad, minimal_module)
    log2 = (session2.metadata.get("ai_decision_logs") or [])[-1]
    assert log2.runtime_orchestration_summary.get("final_path") == "ranked_then_llm"
    assert "synthesis" in llm_keep.stages_seen

    clear_registry()

    class BadRankingGoodSignalAdapter(StoryAIAdapter):
        @property
        def adapter_name(self) -> str:
            return "orch_bad_rank"

        def generate(self, request: AdapterRequest) -> AdapterResponse:
            stage = (request.metadata or {}).get("runtime_stage") or ""
            if stage == "preflight":
                pl = {
                    "runtime_stage": "preflight",
                    "ambiguity_score": 0.1,
                    "trigger_signals": [],
                    "repetition_risk": "low",
                    "classification_label": "x",
                    "preflight_ok": True,
                }
            elif stage == "signal_consistency":
                pl = {
                    "runtime_stage": "signal_consistency",
                    "needs_llm_synthesis": True,
                    "narrative_summary": "n",
                    "consistency_notes": "",
                    "consistency_flags": [],
                }
            elif stage == "ranking":
                pl = {"runtime_stage": "ranking", "recommend_skip_synthesis": "not_bool"}
            else:
                pl = {"scene_interpretation": "x", "detected_triggers": [], "proposed_state_deltas": []}
            return AdapterResponse(raw_output=json.dumps(pl), structured_payload=pl, error=None)

    bad_ad = BadRankingGoodSignalAdapter()
    llm_deg = StagedRecordingAdapter("orch_bad_llm", slm_sufficient=False)
    register_adapter_model(_slm_spec("orch_bad_rank"), bad_ad)
    register_adapter_model(_llm_spec("orch_bad_llm"), llm_deg)
    session3 = SessionState(
        session_id="orch-deg",
        execution_mode="ai",
        adapter_name="orch_bad_rank",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session3.canonical_state = {}
    await execute_turn_with_ai(session3, 1, bad_ad, minimal_module)
    log3 = (session3.metadata.get("ai_decision_logs") or [])[-1]
    assert (
        log3.runtime_orchestration_summary.get("synthesis_gate_reason")
        == "degraded_ranking_parse_forcing_synthesis"
    )
    assert log3.runtime_orchestration_summary.get("final_path") == "degraded_ranking_parse_forcing_synthesis"
    clear_registry()


@pytest.mark.asyncio
async def test_runtime_ranking_slm_only_skip_traced_without_bounded_call(minimal_module: ContentModule):
    """SLM-only path: ranking row is traced without route_model or bounded call (binding interpretation)."""

    clear_registry()
    ad = StagedRecordingAdapter("slm_rk", slm_sufficient=True)
    register_adapter_model(_slm_spec("slm_rk"), ad)
    session = SessionState(
        session_id="slm_rk",
        execution_mode="ai",
        adapter_name="slm_rk",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}
    await execute_turn_with_ai(session, 1, ad, minimal_module)
    log = (session.metadata.get("ai_decision_logs") or [])[-1]
    rk = next(t for t in log.runtime_stage_traces or [] if t.get("stage_id") == "ranking")
    assert rk.get("skip_reason") == RANKING_SLM_ONLY_SKIP_REASON
    assert rk.get("decision") is None
    assert rk.get("bounded_model_call") is False
    clear_registry()


def test_compute_synthesis_gate_after_ranking_no_eligible_fallback():
    """No-eligible ranking adapter falls back to the base signal synthesis gate (deterministic merge)."""

    sig = SignalStageOutput(
        needs_llm_synthesis=True,
        narrative_summary="n",
        consistency_notes="",
        consistency_flags=[],
    )
    needs, reason, effect = compute_synthesis_gate_after_ranking(
        base_needs_llm=True,
        base_reason="signal_requested_synthesis",
        signal=sig,
        signal_parse_ok=True,
        ranking_out=None,
        ranking_parse_ok=False,
        ranking_bounded_ran=False,
        ranking_no_eligible_adapter=True,
    )
    assert needs is True
    assert reason == "degraded_ranking_no_eligible_adapter_fallback_to_signal_gate"
    assert effect == "degraded_no_eligible_fallback"
