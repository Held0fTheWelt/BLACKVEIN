"""Frozen G9 scenario ids stay aligned with evidence template."""

from __future__ import annotations

import json
from pathlib import Path

from ai_stack.goc_g9_roadmap_scenarios import (
    G9_ROADMAP_SCENARIOS,
    ROADMAP_SCENARIO_IDS,
    ROADMAP_SCENARIO_ID_RETRIEVAL_HEAVY,
    expected_failure_oriented_by_id,
)


def test_roadmap_scenario_count_and_order() -> None:
    assert len(G9_ROADMAP_SCENARIOS) == 6
    assert ROADMAP_SCENARIO_IDS[-1] == ROADMAP_SCENARIO_ID_RETRIEVAL_HEAVY


def test_failure_oriented_only_s5() -> None:
    m = expected_failure_oriented_by_id()
    assert sum(1 for v in m.values() if v) == 1
    assert m["goc_roadmap_s5_primary_failure_fallback"] is True


def test_template_json_matches_module_ids() -> None:
    root = Path(__file__).resolve().parents[2]
    template = root / "docs" / "goc_evidence_templates" / "g9_experience_score_matrix.template.json"
    doc = json.loads(template.read_text(encoding="utf-8"))
    ids = [row["scenario_id"] for row in doc["scenarios"]]
    assert tuple(ids) == ROADMAP_SCENARIO_IDS
