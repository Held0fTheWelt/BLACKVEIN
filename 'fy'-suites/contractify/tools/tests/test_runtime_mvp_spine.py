from __future__ import annotations

import contractify.tools.repo_paths as repo_paths
from contractify.tools.audit_pipeline import run_audit
from contractify.tools.conflicts import detect_all_conflicts
from contractify.tools.discovery import discover_contracts_and_projections
from contractify.tools.relations import extend_relations


def test_runtime_mvp_spine_promotes_mandatory_docs() -> None:
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
    }.issubset(ids)


def test_runtime_mvp_relations_cover_required_edges() -> None:
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
    }
    missing = expected - kinds
    assert not missing, f"missing curated runtime/MVP relations: {sorted(missing)}"


def test_runtime_mvp_audit_includes_precedence_and_manual_unresolved() -> None:
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


def test_governed_runtime_adr_overlap_no_longer_raises_normative_vocabulary_overlap() -> None:
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
