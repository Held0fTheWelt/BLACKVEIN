"""Tests for runtime mvp spine.

"""
from __future__ import annotations

import contractify.tools.repo_paths as repo_paths
from contractify.tools.audit_pipeline import run_audit
from contractify.tools.conflicts import detect_all_conflicts
from contractify.tools.discovery import discover_contracts_and_projections
from contractify.tools.relations import extend_relations


def test_runtime_mvp_spine_promotes_mandatory_docs() -> None:
    """Verify that runtime mvp spine promotes mandatory docs works as
    expected.
    """
    root = repo_paths.repo_root()
    contracts, _p, _r = discover_contracts_and_projections(root, max_contracts=60)
    ids = {c.id for c in contracts}
    assert {
        "CTR-RUNTIME-AUTHORITY-STATE-FLOW",
        "CTR-PLAYER-INPUT-INTERPRETATION",
        "CTR-GOC-VERTICAL-SLICE",
        "CTR-GOC-CANONICAL-TURN",
        "CTR-GOC-GATE-SCORING",
        "CTR-BACKEND-RUNTIME-CLASSIFICATION",
        "CTR-CANONICAL-RUNTIME-CONTRACT",
        "CTR-WRITERS-ROOM-PUBLISHING-FLOW",
        "CTR-RAG-GOVERNANCE",
        "CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS",
        "CTR-RUNTIME-NARRATIVE-COMMIT",
        "CTR-AI-STORY-ROUTING-OBSERVATION",
        "CTR-EVIDENCE-BASELINE-GOVERNANCE",
    }.issubset(ids)


def test_runtime_mvp_relations_cover_required_edges() -> None:
    """Verify that runtime mvp relations cover required edges works as
    expected.
    """
    root = repo_paths.repo_root()
    contracts, projections, base = discover_contracts_and_projections(root, max_contracts=60)
    conflicts = detect_all_conflicts(root, projections, contract_ids=frozenset(c.id for c in contracts), contracts=contracts)
    relations = extend_relations(root, contracts, projections, base, conflicts=conflicts)
    kinds = {(r.relation, r.source_id, r.target_id) for r in relations}
    expected = {
        ("refines", "CTR-RUNTIME-AUTHORITY-STATE-FLOW", "CTR-ADR-0001-RUNTIME-AUTHORITY"),
        ("refines", "CTR-BACKEND-RUNTIME-CLASSIFICATION", "CTR-ADR-0001-RUNTIME-AUTHORITY"),
        ("operationalizes", "CTR-BACKEND-RUNTIME-CLASSIFICATION", "CTR-ADR-0002-BACKEND-SESSION-QUARANTINE"),
        ("depends_on", "CTR-CANONICAL-RUNTIME-CONTRACT", "CTR-ADR-0001-RUNTIME-AUTHORITY"),
        ("implemented_by", "CTR-CANONICAL-RUNTIME-CONTRACT", "OBS-WE-HTTP-API"),
        ("implemented_by", "CTR-CANONICAL-RUNTIME-CONTRACT", "OBS-BE-GAME-SERVICE"),
        ("implemented_by", "CTR-PLAYER-INPUT-INTERPRETATION", "OBS-CORE-INPUT-INTERPRETER"),
        ("validated_by", "CTR-PLAYER-INPUT-INTERPRETATION", "VER-CORE-INPUT-INTERPRETER-TEST"),
        ("derives_from", "CTR-GOC-CANONICAL-TURN", "CTR-GOC-VERTICAL-SLICE"),
        ("depends_on", "CTR-GOC-GATE-SCORING", "CTR-GOC-CANONICAL-TURN"),
        ("depends_on", "CTR-GOC-GATE-SCORING", "CTR-GOC-VERTICAL-SLICE"),
        ("implemented_by", "CTR-ADR-0003-SCENE-IDENTITY", "OBS-AI-GOC-SCENE-IDENTITY"),
        ("validated_by", "CTR-ADR-0003-SCENE-IDENTITY", "VER-AI-GOC-SCENE-IDENTITY-TEST"),
        ("overlaps_with", "CTR-WRITERS-ROOM-PUBLISHING-FLOW", "CTR-RAG-GOVERNANCE"),
        ("implemented_by", "CTR-RAG-GOVERNANCE", "OBS-AI-RAG"),
        ("implemented_by", "CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS", "OBS-WE-WS-API"),
        ("implemented_by", "CTR-RUNTIME-NARRATIVE-COMMIT", "OBS-WE-COMMIT-MODELS"),
        ("implemented_by", "CTR-AI-STORY-ROUTING-OBSERVATION", "OBS-BE-OPERATOR-AUDIT"),
        ("validated_by", "CTR-AI-STORY-ROUTING-OBSERVATION", "VER-BE-CROSS-SURFACE-OPERATOR-AUDIT-TEST"),
    }
    missing = expected - kinds
    assert not missing, f"missing curated runtime/MVP relations: {sorted(missing)}"


def test_runtime_mvp_audit_includes_precedence_and_manual_unresolved() -> None:
    """Verify that runtime mvp audit includes precedence and manual
    unresolved works as expected.
    """
    root = repo_paths.repo_root()
    payload = run_audit(root, max_contracts=60)
    tiers = {row["tier"] for row in payload["precedence_rules"]}
    assert {
        "runtime_authority",
        "slice_normative",
        "implementation_evidence",
        "verification_evidence",
        "projection_low",
    } == tiers
    assert payload["manual_unresolved_areas"]
    assert payload["runtime_mvp_families"]["runtime_authority"]
    assert payload["runtime_mvp_families"]["routing_observability"]
    manual_ids = {row["id"] for row in payload["manual_unresolved_areas"]}
    assert "CNF-EVIDENCE-BASELINE-CLONE-REPRO" in manual_ids
    assert payload["adr_governance"]["canonical_dir"] == "docs/ADR"


def test_governed_runtime_adr_overlap_no_longer_raises_normative_vocabulary_overlap() -> None:
    """Verify that governed runtime adr overlap no longer raises normative
    vocabulary overlap works as expected.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.
    """
    root = repo_paths.repo_root()
    contracts, projections, _r = discover_contracts_and_projections(root, max_contracts=60)
    conflicts = detect_all_conflicts(root, projections, contract_ids=frozenset(c.id for c in contracts), contracts=contracts)
    governed = {
        "adr-0001-runtime-authority-in-world-engine.md",
        "adr-0002-backend-session-surface-quarantine.md",
    }
    for conflict in conflicts:
        if conflict.classification != "normative_vocabulary_overlap":
            continue
        assert not set(conflict.sources).issubset(governed)
