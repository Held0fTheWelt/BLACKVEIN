from __future__ import annotations

from pathlib import Path
from typing import Callable

from contractify.tools.models import ContractRecord
from contractify.tools.runtime_mvp_spine_support import (
    IMPLEMENTATION_EVIDENCE,
    RUNTIME_AUTHORITY,
    SLICE_NORMATIVE,
    VERIFICATION_EVIDENCE,
    SpineHelpers,
)


def _extend_evidence_contracts_d_chunk_1(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="OBS-BE-GAME-SERVICE",
            title="Backend game service seam",
            summary="Observed backend consumer/proxy seam for world-engine run and story-session APIs.",
            contract_type="implementation_surface",
            layer="api",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="backend/app/services/game_service.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:runtime_authority", "implementation", "backend", "consumer"],
            owner_or_area="backend",
            scope="world-engine consumer bridge",
            documented_in=existing(
                repo,
                "docs/technical/architecture/canonical_runtime_contract.md",
                "docs/technical/architecture/backend-runtime-classification.md",
            ),
        )
    )

    add(
        contract(
            cid="OBS-WE-WS-API",
            title="World-engine WebSocket API surface",
            summary="Observed WebSocket runtime surface for ticket-authenticated live play commands, state updates, and isolation behavior.",
            contract_type="implementation_surface",
            layer="api",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="world-engine/app/api/ws.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:websocket_runtime", "implementation", "world-engine"],
            owner_or_area="world-engine",
            scope="play-service websocket runtime",
            validated_by=existing(
                repo,
                "world-engine/tests/test_websocket.py",
                "world-engine/tests/test_ws_auth.py",
            ),
            documented_in=existing(
                repo,
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
                "docs/api/README.md",
            ),
        )
    )

def _extend_evidence_contracts_d_chunk_2(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="OBS-WE-COMMIT-MODELS",
            title="Story runtime narrative commit models surface",
            summary="Observed bounded commit record models used to persist authoritative narrative_commit truth in the story runtime.",
            contract_type="implementation_surface",
            layer="runtime",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="world-engine/app/story_runtime/commit_models.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:runtime_commit", "implementation", "world-engine"],
            owner_or_area="world-engine",
            scope="story runtime commit record models",
            validated_by=existing(repo, "world-engine/tests/test_story_runtime_narrative_commit.py"),
            documented_in=existing(repo, "docs/technical/runtime/world_engine_authoritative_narrative_commit.md"),
        )
    )
    add(
        contract(
            cid="OBS-BE-MODEL-ROUTING-CONTRACTS",
            title="Backend model routing contracts surface",
            summary="Observed backend routing contract types and reason-code vocabulary used across staged runtime and operator surfaces.",
            contract_type="implementation_surface",
            layer="implementation",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="backend/app/runtime/model_routing_contracts.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:routing_observability", "implementation", "backend"],
            owner_or_area="backend",
            scope="routing contract types and reason codes",
            documented_in=existing(repo, "docs/technical/architecture/ai_story_contract.md"),
        )
    )

def _extend_evidence_contracts_d_chunk_3(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="OBS-BE-OPERATOR-AUDIT",
            title="Backend operator audit surface",
            summary="Observed deterministic operator-audit assembly surface derived from routing evidence and stage traces.",
            contract_type="implementation_surface",
            layer="implementation",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="backend/app/runtime/operator_audit.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:routing_observability", "implementation", "backend", "operator_audit"],
            owner_or_area="backend",
            scope="cross-surface operator audit generation",
            validated_by=existing(repo, "backend/tests/runtime/test_cross_surface_operator_audit_contract.py"),
            documented_in=existing(repo, "docs/technical/architecture/ai_story_contract.md"),
        )
    )

    add(
        contract(
            cid="VER-TEST-RUNNER-CLI",
            title="Repository pytest runner implementation",
            summary="Observed multi-suite pytest orchestrator used as the root verification launcher.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="tests/run_tests.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:testing", "verification", "runner"],
            owner_or_area="qa",
            scope="test orchestration code",
            documented_in=existing(repo, "tests/TESTING.md"),
        )
    )

def _extend_evidence_contracts_d_chunk_4(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="VER-AI-GOC-SCENE-IDENTITY-TEST",
            title="GoC scene identity contract tests",
            summary="Verification suite asserting canonical scene-id mapping and duplicate-definition protection for ADR-0003.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="ai_stack/tests/test_goc_scene_identity.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:scene_identity", "verification", "pytest"],
            owner_or_area="ai_stack",
            scope="scene identity verification",
            documented_in=existing(
                repo,
                adr0003(repo),
                "docs/audit/repo_evidence_index.md",
            ),
        )
    )
    add(
        contract(
            cid="VER-CORE-INPUT-INTERPRETER-TEST",
            title="Input interpreter contract tests",
            summary="Verification suite covering structured kind selection and runtime delivery hints for player input interpretation.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="story_runtime_core/tests/test_input_interpreter.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:input_turn", "verification", "pytest"],
            owner_or_area="story_runtime_core",
            scope="input interpretation verification",
            documented_in=existing(repo, "docs/technical/runtime/player_input_interpretation_contract.md"),
        )
    )

def _extend_evidence_contracts_d_chunk_5(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="VER-GOC-EXPERIENCE-SCORE-CLI-TEST",
            title="Experience score matrix CLI tests",
            summary="Verification suite for the G9 threshold validator and canonical six-scenario GoC experience matrix ordering/rules.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="tests/experience_scoring_cli/test_experience_score_matrix_cli.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:goc", "verification", "g9"],
            owner_or_area="qa",
            scope="GoC gate scoring verification",
            documented_in=existing(
                repo,
                "docs/audit/repo_evidence_index.md",
                "docs/audit/gate_G9_experience_acceptance_baseline.md",
            ),
        )
    )
    add(
        contract(
            cid="VER-SMOKE-DOCUMENTED-PATHS",
            title="Repository documented paths smoke test",
            summary="Verification guard asserting high-visibility documented module/test paths resolve on disk.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="tests/smoke/test_repository_documented_paths_resolve.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:testing", "verification", "smoke"],
            owner_or_area="qa",
            scope="documented path existence guard",
            documented_in=existing(repo, "docs/audit/repo_evidence_index.md"),
        )
    )

def _extend_evidence_contracts_d_chunk_6(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="VER-BE-WORLD-ENGINE-CONSOLE-ROUTES-TEST",
            title="Backend world-engine console route tests",
            summary="Verification suite for admin console proxy authorization and world-engine bridge route behavior.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="backend/tests/test_world_engine_console_routes.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:runtime_authority", "verification", "backend"],
            owner_or_area="backend",
            scope="admin proxy verification",
            documented_in=existing(repo, "tests/TESTING.md"),
        )
    )
    add(
        contract(
            cid="VER-WE-STORY-RUNTIME-API-TEST",
            title="World-engine story runtime API tests",
            summary="Verification suite for story-session lifecycle, retrieval fields, and interpreted-input behavior.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="world-engine/tests/test_story_runtime_api.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:runtime_authority", "verification", "world-engine"],
            owner_or_area="world-engine",
            scope="story runtime API verification",
            documented_in=existing(repo, "tests/TESTING.md"),
        )
    )

def _extend_evidence_contracts_d_chunk_7(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="VER-AI-RETRIEVAL-GOVERNANCE-SUMMARY-TEST",
            title="Retrieval governance summary tests",
            summary="Verification suite asserting retrieval governance summary fields, lanes, visibility classes, and policy version handling.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="ai_stack/tests/test_retrieval_governance_summary.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:publish_rag", "verification", "ai_stack", "rag"],
            owner_or_area="ai_stack",
            scope="retrieval governance verification",
            documented_in=existing(repo, "docs/technical/ai/RAG.md", "tests/TESTING.md"),
        )
    )
    add(
        contract(
            cid="VER-BE-WRITERS-ROOM-ROUTES-TEST",
            title="Writers’ Room route tests",
            summary="Verification suite for backend Writers’ Room review route behavior, JWT requirements, retrieval flow, and recommendation-only review semantics.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="backend/tests/writers_room/test_writers_room_routes.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:publish_rag", "verification", "backend", "writers_room"],
            owner_or_area="backend",
            scope="writers-room workflow verification",
            documented_in=existing(repo, "docs/technical/content/writers-room-and-publishing-flow.md", "tests/TESTING.md"),
        )
    )

def _extend_evidence_contracts_d_chunk_8(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="VER-WE-NARRATIVE-COMMIT-TEST",
            title="World-engine narrative commit tests",
            summary="Verification suite for bounded narrative_commit records, legality checks, and committed story-session state exposure.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="world-engine/tests/test_story_runtime_narrative_commit.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:runtime_commit", "verification", "world-engine"],
            owner_or_area="world-engine",
            scope="story runtime narrative commit verification",
            documented_in=existing(repo, "docs/technical/runtime/world_engine_authoritative_narrative_commit.md", "tests/TESTING.md"),
        )
    )
    add(
        contract(
            cid="VER-WE-WS-TEST",
            title="World-engine WebSocket contract tests",
            summary="Verification suite for ticket-gated WebSocket connection, command rejection, and live runtime message behavior.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="world-engine/tests/test_websocket.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:websocket_runtime", "verification", "world-engine"],
            owner_or_area="world-engine",
            scope="play-service websocket verification",
            documented_in=existing(repo, "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md", "tests/TESTING.md"),
        )
    )

def _extend_evidence_contracts_d_chunk_9(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="VER-BE-CROSS-SURFACE-OPERATOR-AUDIT-TEST",
            title="Cross-surface operator audit contract tests",
            summary="Verification suite for additive operator_audit and routing_evidence contracts across runtime and governance surfaces.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="backend/tests/runtime/test_cross_surface_operator_audit_contract.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:routing_observability", "verification", "backend"],
            owner_or_area="backend",
            scope="routing evidence and operator audit verification",
            documented_in=existing(repo, "docs/technical/architecture/ai_story_contract.md", "docs/audit/repo_evidence_index.md", "tests/TESTING.md"),
        )
    )


def extend_evidence_contracts_d(repo: Path, add: Callable[[ContractRecord], None], h: SpineHelpers) -> None:
    contract = h.contract
    existing = h.existing
    one_of = h.one_of
    adr0001 = h.adr0001
    adr0002 = h.adr0002
    adr0003 = h.adr0003
    _extend_evidence_contracts_d_chunk_1(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_evidence_contracts_d_chunk_2(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_evidence_contracts_d_chunk_3(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_evidence_contracts_d_chunk_4(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_evidence_contracts_d_chunk_5(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_evidence_contracts_d_chunk_6(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_evidence_contracts_d_chunk_7(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_evidence_contracts_d_chunk_8(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_evidence_contracts_d_chunk_9(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
