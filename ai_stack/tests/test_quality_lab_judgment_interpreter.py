"""Tests for ``ai_stack.quality_lab.judgment_interpreter`` (ADR-0040 Phase 1).

Per ADR-0039: expected judge names, categories, and severity buckets are
derived from the canonical catalog (``WOS_CATEGORICAL_JUDGES_ORDER`` and
``docs/llm-as-a-judge/``) — never from hardcoded literals in this file.
"""

from __future__ import annotations

import pytest

from ai_stack.langfuse.langfuse_evaluator_catalog import WOS_CATEGORICAL_JUDGES_ORDER
from ai_stack.quality_lab.evaluator_catalog import (
    category_severity_bucket,
    evaluator_view,
    evaluator_views_for_scope,
    list_evaluator_views,
)
from ai_stack.quality_lab.judgment_interpreter import interpret_judgments


# ---------------------------------------------------------------------------
# Helpers (derive expectations from the canonical catalog)
# ---------------------------------------------------------------------------


def _first_category(judge_name: str, bucket: str) -> str:
    view = evaluator_view(judge_name)
    assert view is not None, judge_name
    members = sorted(view.severity_buckets.get(bucket) or ())
    assert members, f"{judge_name} has no {bucket} categories"
    return members[0]


def _pick_judge(scope: str, *, bucket: str) -> str:
    for view in evaluator_views_for_scope(scope):
        if view.severity_buckets.get(bucket):
            return view.name
    raise AssertionError(f"no {scope} judge has a {bucket} category")


# ---------------------------------------------------------------------------
# Catalog wrapper
# ---------------------------------------------------------------------------


def test_all_judges_have_views_loaded_from_canonical_directory():
    """Every catalog name must have a loadable EvaluatorView."""
    for name in WOS_CATEGORICAL_JUDGES_ORDER:
        view = evaluator_view(name)
        assert view is not None, name
        assert view.name == name
        assert view.categories, f"{name}: empty categories"
        assert view.group != "unknown", f"{name}: group missing from frontmatter"


def test_severity_buckets_only_reference_declared_categories():
    """Sanity: severity bucket contents must be a subset of the declared categories."""
    for view in list_evaluator_views():
        declared = set(view.categories)
        for bucket, members in view.severity_buckets.items():
            unknown = members - declared
            assert not unknown, (view.name, bucket, sorted(unknown))


def test_category_severity_bucket_returns_expected_label():
    judge = _pick_judge("turn_generation", bucket="failure")
    failure_cat = _first_category(judge, "failure")
    assert category_severity_bucket(judge, failure_cat) == "failure"
    positive_cat = _first_category(judge, "positive")
    assert category_severity_bucket(judge, positive_cat) == "positive"


def test_category_severity_bucket_handles_unknown_input():
    assert category_severity_bucket("not_a_real_judge", "anything") == "unknown"
    assert category_severity_bucket("beat_realization_judge", None) == "unknown"
    assert category_severity_bucket("beat_realization_judge", "nonsense_label") == "unknown"


# ---------------------------------------------------------------------------
# interpret_judgments
# ---------------------------------------------------------------------------


def test_empty_input_returns_decision_prompt_for_full_coverage_gap():
    result = interpret_judgments({})
    assert result["judge_interpretations"] == []
    assert result["missing_judges"]
    assert result["next_user_decision"] is not None
    decision = result["next_user_decision"]
    assert decision["requires_user_decision"] is True
    assert any(opt.get("recommended") for opt in decision["decision_options"])
    for option in decision["decision_options"]:
        assert option["ai_action"], "ai_action must be specific"


def test_positive_categories_produce_positive_severity_no_failure_cluster():
    judge = _pick_judge("turn_generation", bucket="positive")
    positive_cat = _first_category(judge, "positive")
    result = interpret_judgments({judge: {"category": positive_cat}}, is_opening=False)
    [entry] = result["judge_interpretations"]
    assert entry["severity"] == "positive"
    assert entry["suggested_repair_areas"] == []
    assert result["qualitative_issue_clusters"] == []
    assert result["improvement_candidates"] == []


def test_failure_category_creates_cluster_and_improvement_candidate():
    judge = _pick_judge("turn_generation", bucket="failure")
    failure_cat = _first_category(judge, "failure")
    result = interpret_judgments(
        {judge: {"category": failure_cat, "reasoning": "synthetic test failure"}},
        is_opening=False,
    )
    [entry] = result["judge_interpretations"]
    assert entry["severity"] == "failure"
    assert entry["suggested_repair_areas"], "failure must surface repair areas"
    clusters = result["qualitative_issue_clusters"]
    assert len(clusters) == 1
    cluster = clusters[0]
    assert judge in cluster["affected_judges"]
    assert cluster["frequency"] == 1
    [candidate] = result["improvement_candidates"]
    assert candidate["affected_judges"] == [judge]
    assert candidate["priority"] in {"urgent", "high"}


def test_failures_in_same_group_aggregate_into_one_cluster():
    failing_judges: list[tuple[str, str]] = []
    seen_groups: set[str] = set()
    target_group: str | None = None
    for view in evaluator_views_for_scope("turn_generation"):
        if not view.severity_buckets.get("failure"):
            continue
        failing_judges.append((view.name, sorted(view.severity_buckets["failure"])[0]))
        if view.group in seen_groups:
            target_group = view.group
            break
        seen_groups.add(view.group)
    assert target_group, "fixture assumption: at least two failure judges share a group"

    pair = [(n, c) for n, c in failing_judges if evaluator_view(n).group == target_group][:2]
    assert len(pair) == 2
    scores = {name: {"category": cat} for name, cat in pair}
    result = interpret_judgments(scores, is_opening=False)
    matching = [
        c for c in result["qualitative_issue_clusters"]
        if c["evaluator_group"] == target_group
    ]
    assert len(matching) == 1
    cluster = matching[0]
    assert cluster["frequency"] == 2
    assert cluster["severity"] == "high"
    assert set(cluster["affected_judges"]) == {n for n, _ in pair}


def test_missing_judges_uses_scope_to_filter_expected_set():
    judge = _pick_judge("opening_generation", bucket="positive")
    positive_cat = _first_category(judge, "positive")
    result = interpret_judgments({judge: {"category": positive_cat}}, is_opening=True)
    missing = set(result["missing_judges"])
    opening_names = {v.name for v in evaluator_views_for_scope("opening_generation")}
    turn_names = {v.name for v in evaluator_views_for_scope("turn_generation")}
    assert missing == opening_names - {judge}
    # Turn-only judges must NOT be flagged as missing on an opening trace.
    assert not (missing & (turn_names - opening_names))


def test_unknown_judges_are_surfaced_separately():
    result = interpret_judgments({"not_a_real_judge": {"category": "whatever"}})
    assert result["judge_interpretations"] == []
    assert result["unknown_judges"] == ["not_a_real_judge"]


def test_neutral_category_appears_in_coverage_gaps_not_failures():
    """``not_applicable`` is a coverage gap, never a failure."""
    judge_with_neutral = next(
        (v for v in list_evaluator_views() if v.severity_buckets.get("neutral")),
        None,
    )
    assert judge_with_neutral, "fixture: at least one judge has a neutral bucket"
    neutral_cat = sorted(judge_with_neutral.severity_buckets["neutral"])[0]
    result = interpret_judgments(
        {judge_with_neutral.name: {"category": neutral_cat}},
        is_opening=None,
    )
    [entry] = result["judge_interpretations"]
    assert entry["severity"] == "neutral"
    assert result["qualitative_issue_clusters"] == []
    assert result["coverage_gaps"], "neutral results should be coverage gaps"
    assert result["coverage_gaps"][0]["judge"] == judge_with_neutral.name


def test_repair_area_summary_ranks_areas_by_judge_count():
    pair: list[tuple[str, str]] = []
    seen: dict[str, str] = {}
    target_group: str | None = None
    for view in evaluator_views_for_scope("turn_generation"):
        if not view.severity_buckets.get("failure") or not view.suggested_repair_areas:
            continue
        if view.group in seen:
            target_group = view.group
            pair = [
                (seen[view.group], sorted(evaluator_view(seen[view.group]).severity_buckets["failure"])[0]),
                (view.name, sorted(view.severity_buckets["failure"])[0]),
            ]
            break
        seen[view.group] = view.name
    assert target_group, "fixture: two failure judges in same group with repair areas"
    scores = {name: {"category": cat} for name, cat in pair}
    result = interpret_judgments(scores, is_opening=False)
    top = result["repair_area_summary"]["top_repair_areas"]
    assert top, "expected at least one repair area ranking"
    assert top[0]["judge_count"] >= 1


def test_output_carries_authoritative_flags():
    result = interpret_judgments({})
    assert result["deterministic_gates_remain_authoritative"] is True
    assert result["canonical_evaluator_definition_doc"] == "docs/llm-as-a-judge/"
