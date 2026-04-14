"""Tests for research domain strategic governance payloads."""

from __future__ import annotations

from app.services.research_domain_governance_service import (
    LAYER_IDS,
    build_research_domain_overview,
    build_research_layer_payload,
    governance_principles,
)


def test_governance_principles_many_findings_one_canonical():
    p = governance_principles()
    assert p["many_candidate_findings_allowed"] is True
    assert p["single_promoted_canonical_truth_per_governed_module"] is True
    assert "findings_candidates" in p["layer_order"]
    assert p["layer_order"].index("canonical_truth") > p["layer_order"].index("findings_candidates")


def test_overview_payload_shape(app):
    with app.app_context():
        data = build_research_domain_overview()
    assert data["domain"] == "research_governance"
    assert "governance_version" in data
    assert data["operational_state"] in ("healthy", "degraded", "blocked")
    assert "status_semantics" in data
    layers = data["layers"]
    for lid in LAYER_IDS:
        assert lid in layers
        assert layers[lid]["layer_id"] == lid
    assert any("path" in d for d in data["drill_down"])


def test_layer_payloads_distinct_keys(app):
    with app.app_context():
        src = build_research_layer_payload("source_intake")
        find = build_research_layer_payload("findings_candidates")
        canon = build_research_layer_payload("canonical_truth")
    assert src["layer"]["layer_id"] == "source_intake"
    assert "repository_footprint_available" in (src["layer"].get("summary") or {})
    assert find["layer"]["is_canonical_layer"] is False
    assert canon["layer"]["is_canonical_layer"] is True
    assert "promoted_modules" in canon["layer"]


def test_findings_layer_has_conflict_and_candidate_fields(app):
    with app.app_context():
        f = build_research_layer_payload("findings_candidates")["layer"]
    assert "review_status_counts" in f
    assert "pending_conflict_count" in f
    assert "sample_candidates" in f
