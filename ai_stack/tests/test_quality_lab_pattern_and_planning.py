"""Tests for Quality Lab Phase 4/5 pattern and planning interpreters."""

from __future__ import annotations

from ai_stack.quality_lab.evaluator_catalog import list_evaluator_views
from ai_stack.quality_lab.pattern_interpreter import (
    PATTERN_CLUSTER_FIELDS,
    QUALITY_LAB_PATTERN_TOOL_NAMES,
    find_patterns,
    suggest_investigation,
)
from ai_stack.quality_lab.planning_interpreter import (
    DEFAULT_REPAIR_CONSTRAINTS,
    QUALITY_LAB_PLANNING_TOOL_NAMES,
    plan_content_revision,
    plan_repair_wave,
    refine_judge_set,
)


def _view_with_categories():
    for view in list_evaluator_views():
        if view.categories:
            return view
    raise AssertionError("fixture requires at least one evaluator category")


def test_phase4_and_phase5_tool_constants_are_public():
    assert "runtime_area" in PATTERN_CLUSTER_FIELDS
    assert "wos.quality_lab.find_patterns" in QUALITY_LAB_PATTERN_TOOL_NAMES
    assert "wos.quality_lab.plan_repair_wave" in QUALITY_LAB_PLANNING_TOOL_NAMES
    assert DEFAULT_REPAIR_CONSTRAINTS["no_runtime_gate_weakening"] is True


def test_find_patterns_groups_repeated_runtime_area():
    trace_summaries = [
        {
            "trace_id": "lf-1",
            "improvement_candidates": [
                {"repair_area": "runtime_authority", "priority": "high", "rationale": "first"}
            ],
        },
        {
            "trace_id": "lf-2",
            "improvement_candidates": [
                {"repair_area": "runtime_authority", "priority": "medium", "rationale": "second"}
            ],
        },
    ]

    result = find_patterns(
        trace_summaries=trace_summaries,
        cluster_by=["runtime_area"],
        include_claude_context=True,
    )

    [pattern] = result["recurring_patterns"]
    assert pattern["cluster_by"] == "runtime_area"
    assert pattern["frequency"] == 2
    assert set(pattern["affected_traces"]) == {"lf-1", "lf-2"}
    assert result["top_improvement_targets"][0]["repair_area"] == "runtime_authority"
    assert result["claude_context_queries"]


def test_find_patterns_groups_repeated_judge_category_from_catalog_values():
    view = _view_with_categories()
    category = view.categories[0]
    judge_results = [
        {"judge_interpretations": [{"judge": view.name, "category": category}]},
        {"judge_interpretations": [{"judge": view.name, "category": category}]},
    ]

    result = find_patterns(judge_results=judge_results, cluster_by=["judge", "category"])

    grouped = {(p["cluster_by"], p["cluster_value"]) for p in result["recurring_patterns"]}
    assert ("judge", view.name) in grouped
    assert ("category", category) in grouped


def test_suggest_investigation_builds_steps_tools_and_decision_prompt():
    cluster = {
        "cluster_id": "pattern_1",
        "title": "Recurring runtime authority",
        "affected_areas": ["runtime_authority"],
        "affected_judges": [_view_with_categories().name],
        "affected_traces": ["lf-1", "lf-2"],
        "likely_causes": ["actor-lane or authority-boundary regression"],
        "severity": "high",
        "frequency": 2,
    }

    result = suggest_investigation(
        problem_cluster=cluster,
        available_context={"mcp_exchange_available": True},
        include_claude_context=True,
    )

    assert result["hypotheses"]
    assert result["investigation_steps"]
    assert "wos.quality_lab.review_trace" in result["mcp_followup_tools"]
    assert result["claude_context_queries"]
    recommended = [o for o in result["user_decision"]["decision_options"] if o["recommended"]]
    assert len(recommended) == 1


def test_plan_repair_wave_orders_high_priority_candidates_first():
    result = plan_repair_wave(
        improvement_candidates=[
            {"candidate_id": "low", "repair_area": "content_gap", "priority": "low"},
            {"candidate_id": "high", "repair_area": "runtime_authority", "priority": "high"},
        ]
    )

    assert result["repair_waves"][0]["wave_id"] == "wave_1"
    assert "high" in result["repair_waves"][0]["candidates"]
    assert result["risks"]
    assert result["tests_to_add"]
    assert "ADR-0033 deterministic runtime gate semantics" in result["do_not_change"]


def test_plan_repair_wave_preserves_explicit_constraints():
    result = plan_repair_wave(
        improvement_candidates=[],
        constraints={"no_hardcoded_content": False},
    )

    assert result["constraints"]["no_runtime_gate_weakening"] is True
    assert result["constraints"]["no_hardcoded_content"] is False


def test_refine_judge_set_proposes_prompt_review_for_known_judge_failures():
    view = _view_with_categories()
    result = refine_judge_set(
        judge_names=[view.name],
        observed_failures=[{"judge": view.name, "affected_area": view.group}],
        examples=[{"input": "fixture", "output": "fixture"}],
    )

    assert result["prompt_delta_proposals"]
    assert result["prompt_delta_proposals"][0]["judge"] == view.name
    assert result["requires_user_review"] is True


def test_refine_judge_set_flags_unknown_judge_without_mutation():
    result = refine_judge_set(judge_names=["not_a_catalogued_judge"], mode="analysis_only")

    findings = {f["finding"] for f in result["judge_maintenance_findings"]}
    assert "unknown_judge" in findings
    assert result["deterministic_gates_remain_authoritative"] is True


def test_refine_judge_set_suggests_new_candidate_for_repeated_uncovered_area():
    result = refine_judge_set(
        judge_names=[],
        observed_failures=[
            {"affected_area": "relationship_content"},
            {"affected_area": "relationship_content"},
        ],
    )

    assert result["new_judge_candidates"]
    assert "relationship_content" in result["new_judge_candidates"][0]["candidate"]


def test_plan_content_revision_builds_governed_tasks_and_queries():
    result = plan_content_revision(
        content_module="god_of_carnage",
        quality_findings=[
            {
                "source": "content",
                "affected_area": "relationship_pressure",
                "interpretation": "relationship pressure was missing",
            }
        ],
        scene_or_context="living room opening",
        include_claude_context=True,
    )

    assert result["content_gap_hypotheses"]
    assert result["content_revision_tasks"]
    assert result["content_questions_for_user"]
    assert result["claude_context_queries"]
    assert result["scene_or_context"] == "living room opening"


def test_phase4_and_phase5_outputs_carry_authoritative_flags():
    patterns = find_patterns()
    repair = plan_repair_wave()
    content = plan_content_revision()

    for result in (patterns, repair, content):
        assert result["deterministic_gates_remain_authoritative"] is True
        assert result["canonical_evaluator_definition_doc"] == "docs/llm-as-a-judge/"
