"""Fail fast when high-visibility docs reference missing test modules (repository-truth guard)."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _must_exist(rel: str) -> Path:
    p = _REPO_ROOT.joinpath(*rel.split("/"))
    assert p.is_file(), f"missing documented path: {rel}"
    return p


@pytest.mark.parametrize(
    "rel",
    [
        # docs/MVPs/MVP_Research_Gate_And_Implementation/research_mvp_gate_closure.md — research + MCP parity command targets
        "ai_stack/tests/test_research_intake_golden.py",
        "ai_stack/tests/test_research_aspect_golden.py",
        "ai_stack/tests/test_research_exploration_golden.py",
        "ai_stack/tests/test_research_verification_golden.py",
        "ai_stack/tests/test_research_canon_improvement_golden.py",
        "ai_stack/tests/test_research_review_bundle_golden.py",
        "ai_stack/tests/test_research_contract_enforcement.py",
        "ai_stack/tests/test_capabilities.py",
        "tools/mcp_server/tests/test_research_mcp_contracts.py",
        "ai_stack/tests/test_mcp_canonical_surface.py",
        "tools/mcp_server/tests/test_registry.py",
        "tools/mcp_server/tests/test_tools_handlers.py",
        "tools/mcp_server/tests/test_mcp_operational_parity_and_registry.py",
        "administration-tool/tests/test_manage_inspector_suite.py",
        # README focused GoC / LangGraph example
        "ai_stack/tests/test_goc_frozen_vocab.py",
        "ai_stack/tests/test_goc_roadmap_semantic_surface.py",
        "ai_stack/tests/test_scene_direction_subdecision_matrix.py",
        "ai_stack/tests/test_goc_field_initialization_envelope.py",
        "ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py",
        "ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py",
        "ai_stack/tests/test_goc_multi_turn_experience_quality.py",
        "ai_stack/tests/test_goc_mvp_breadth_playability_regression.py",
        "ai_stack/tests/test_goc_closure_residuals.py",
        "ai_stack/tests/test_langgraph_runtime.py",
        # MCP closure report command targets
        "tools/mcp_server/tests/test_rpc.py",
        "backend/tests/runtime/test_mcp_enrichment.py",
        # docs/MVPs/MVP_Semantic_Dramatic_Planner/ROADMAP_MVP_SEMANTIC_DRAMATIC_PLANNER.md — current planner tests
        "ai_stack/tests/test_semantic_planner_contracts.py",
        "ai_stack/tests/test_character_mind_goc.py",
        "ai_stack/tests/test_social_state_goc.py",
        "ai_stack/tests/test_semantic_move_interpretation_goc.py",
        "ai_stack/tests/test_dramatic_effect_gate.py",
        "ai_stack/tests/test_semantic_planner_graph_authority.py",
        "ai_stack/tests/test_semantic_planner_golden_cases.py",
        # G9 validator CLI pytest + fixtures (repo_evidence_index)
        "tests/experience_scoring_cli/test_experience_score_matrix_cli.py",
        "tests/experience_scoring_cli/fixtures/g9_matrix_all_4_5.json",
    ],
)
def test_documented_module_path_exists(rel: str) -> None:
    _must_exist(rel)


def test_mcp_m1_closure_report_names_operational_parity_module() -> None:
    report = (_REPO_ROOT / "tests" / "reports" / "MCP_M1_CLOSURE_REPORT.md").read_text(encoding="utf-8")
    assert "test_mcp_operational_parity_and_registry.py" in report
    assert "test_mcp_m1_gates.py" not in report


def test_no_stale_mcp_gate_filename_in_active_mcp_readme() -> None:
    text = (_REPO_ROOT / "tools" / "mcp_server" / "README.md").read_text(encoding="utf-8")
    assert "test_mcp_m1_gates.py" not in text
