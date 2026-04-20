
from __future__ import annotations

from pathlib import Path

from contractify.tools.models import ConflictFinding
from contractify.tools.runtime_mvp_spine_support import SpineHelpers


def _build_unresolved_candidates(repo: Path, make_review_conflict, adr0001, adr0002, adr0003) -> list[ConflictFinding]:
    unresolved_candidates = [
        make_review_conflict(
            repo=repo,
            conflict_id="CNF-RUNTIME-SPINE-TRANSITIONAL-RETIREMENT",
            conflict_type="intentional_unresolved_transition_boundary",
            summary="Backend transitional session surfaces are now attached and weighted, but the actual retirement timeline remains intentionally unresolved.",
            notes="Governed as quarantine/compat today; removal timing still needs explicit decision-log entries.",
            classification="runtime_transition_retirement_open",
            kind="intentional_unresolved_boundary",
            severity="medium",
            confidence=0.84,
            normative_candidates=[
                adr0002(repo),
                "docs/technical/architecture/backend-runtime-classification.md",
            ],
            observed_candidates=[
                "backend/app/api/v1/session_routes.py",
                "backend/app/runtime/session_store.py",
                "backend/app/services/session_service.py",
            ],
        ),
        make_review_conflict(
            repo=repo,
            conflict_id="CNF-EVIDENCE-BASELINE-CLONE-REPRO",
            conflict_type="intentional_clone_reproducibility_boundary",
            summary="Audit docs intentionally cite machine-local tests/reports evidence paths while clone reproducibility only guarantees the tracked subset; this boundary must stay explicit in governance review.",
            notes="This is an honest reproducibility boundary, not a reason to treat machine-local evidence trees as clone-guaranteed truth.",
            classification="clone_reproducibility_boundary",
            kind="reviewable_reproducibility_boundary",
            severity="medium",
            confidence=0.83,
            normative_candidates=[
                "docs/audit/gate_summary_matrix.md",
                "docs/audit/repo_evidence_index.md",
            ],
            observed_candidates=[".gitignore", "tests/reports"],
        ),
        make_review_conflict(
            repo=repo,
            conflict_id="CNF-RUNTIME-SPINE-WRITERS-RAG-OVERLAP",
            conflict_type="intentional_overlap_boundary",
            summary="Writers’ Room workflow and RAG governance intentionally overlap at retrieval/context-pack assembly, but publishing authority and runtime truth remain distinct and should stay explicitly reviewed.",
            notes="Not a contradiction today; keep reviewable so future retrieval write-backs do not flatten authority boundaries.",
            classification="intentional_overlap_boundary",
            kind="reviewable_overlap",
            severity="medium",
            confidence=0.8,
            normative_candidates=[
                "docs/technical/content/writers-room-and-publishing-flow.md",
                "docs/technical/ai/RAG.md",
            ],
            observed_candidates=[
                "backend/app/api/v1/writers_room_routes.py",
                "ai_stack/rag.py",
            ],
        ),
    ]
    return [item for item in unresolved_candidates if item is not None]



def _families_map() -> dict[str, list[str]]:
    families = {
        "runtime_authority": [
            "CTR-ADR-0001-RUNTIME-AUTHORITY",
            "CTR-ADR-0002-BACKEND-SESSION-QUARANTINE",
            "CTR-RUNTIME-AUTHORITY-STATE-FLOW",
            "CTR-BACKEND-RUNTIME-CLASSIFICATION",
            "CTR-CANONICAL-RUNTIME-CONTRACT",
            "CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS",
            "CTR-RUNTIME-NARRATIVE-COMMIT",
            "OBS-WE-WS-API",
            "OBS-WE-COMMIT-MODELS",
            "VER-WE-WS-TEST",
            "VER-WE-NARRATIVE-COMMIT-TEST",
        ],
        "input_turn": [
            "CTR-PLAYER-INPUT-INTERPRETATION",
            "OBS-CORE-INPUT-INTERPRETER",
            "VER-CORE-INPUT-INTERPRETER-TEST",
        ],
        "goc": [
            "CTR-GOC-VERTICAL-SLICE",
            "CTR-GOC-CANONICAL-TURN",
            "CTR-GOC-GATE-SCORING",
            "VER-GOC-EXPERIENCE-SCORE-CLI-TEST",
        ],
        "scene_identity": [
            "CTR-ADR-0003-SCENE-IDENTITY",
            "OBS-AI-GOC-SCENE-IDENTITY",
            "OBS-AI-GOC-YAML-AUTHORITY",
            "VER-AI-GOC-SCENE-IDENTITY-TEST",
        ],
        "publish_rag": [
            "CTR-WRITERS-ROOM-PUBLISHING-FLOW",
            "CTR-RAG-GOVERNANCE",
            "OBS-BE-WRITERS-ROOM-ROUTES",
            "OBS-AI-RAG",
            "VER-BE-WRITERS-ROOM-ROUTES-TEST",
            "VER-AI-RETRIEVAL-GOVERNANCE-SUMMARY-TEST",
        ],
        "routing_observability": [
            "CTR-AI-STORY-ROUTING-OBSERVATION",
            "OBS-BE-MODEL-ROUTING-CONTRACTS",
            "OBS-BE-OPERATOR-AUDIT",
            "VER-BE-CROSS-SURFACE-OPERATOR-AUDIT-TEST",
        ],
        "evidence_baseline": [
            "CTR-EVIDENCE-BASELINE-GOVERNANCE",
            "VER-SMOKE-DOCUMENTED-PATHS",
        ],
        "testing": [
            "CTR-TESTING-ORCHESTRATION",
            "VER-TEST-RUNNER-CLI",
            "VER-SMOKE-DOCUMENTED-PATHS",
        ],
    }
    return families


def build_unresolved_and_families(repo: Path, h: SpineHelpers) -> tuple[list[ConflictFinding], dict[str, list[str]]]:
    unresolved = _build_unresolved_candidates(repo, h.make_review_conflict, h.adr0001, h.adr0002, h.adr0003)
    return unresolved, _families_map()
