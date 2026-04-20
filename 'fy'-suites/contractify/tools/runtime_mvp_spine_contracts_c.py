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


def _extend_evidence_contracts_c_chunk_1(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="OBS-WE-STORY-RUNTIME-MANAGER",
            title="StoryRuntimeManager implementation surface",
            summary="Observed authoritative runtime manager for story sessions, turn execution, retrieval wiring, and diagnostics.",
            contract_type="implementation_surface",
            layer="runtime",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="world-engine/app/story_runtime/manager.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:runtime_authority", "implementation", "world-engine"],
            owner_or_area="world-engine",
            scope="story runtime manager code",
            validated_by=existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=existing(
                repo,
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/technical/ai/RAG.md",
            ),
        )
    )
    add(
        contract(
            cid="OBS-WE-HTTP-API",
            title="World-engine HTTP API surface",
            summary="Observed FastAPI play-service surface for runs and story sessions.",
            contract_type="implementation_surface",
            layer="api",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="world-engine/app/api/http.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:runtime_authority", "implementation", "api"],
            owner_or_area="world-engine",
            scope="play-service API code",
            validated_by=existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=existing(
                repo,
                "docs/technical/architecture/canonical_runtime_contract.md",
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
            ),
        )
    )

def _extend_evidence_contracts_c_chunk_2(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="OBS-BE-SESSION-ROUTES",
            title="Backend session routes surface",
            summary="Observed backend session API surface explicitly labeled non-authoritative and partly world-engine-bridged.",
            contract_type="implementation_surface",
            layer="api",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="backend/app/api/v1/session_routes.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:runtime_authority", "implementation", "backend"],
            owner_or_area="backend",
            scope="backend transitional session routes",
            validated_by=existing(repo, "backend/tests/test_session_routes.py"),
            documented_in=existing(
                repo,
                "docs/technical/architecture/backend-runtime-classification.md",
                adr0002(repo),
            ),
        )
    )
    add(
        contract(
            cid="OBS-BE-SESSION-STORE",
            title="Backend session store surface",
            summary="Observed volatile in-memory runtime session registry retained for tests, MCP, and transitional operator flows.",
            contract_type="implementation_surface",
            layer="runtime",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="backend/app/runtime/session_store.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:runtime_authority", "implementation", "backend", "transitional"],
            owner_or_area="backend",
            scope="backend volatile session registry",
            documented_in=existing(
                repo,
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/technical/architecture/backend-runtime-classification.md",
                adr0002(repo),
            ),
        )
    )

def _extend_evidence_contracts_c_chunk_3(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="OBS-BE-SESSION-SERVICE",
            title="Backend session service surface",
            summary="Observed session service bridge for backend-local SessionState bootstrap and deferred W3.2 behavior.",
            contract_type="implementation_surface",
            layer="implementation",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="backend/app/services/session_service.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:runtime_authority", "implementation", "backend", "transitional"],
            owner_or_area="backend",
            scope="backend session service bridge",
            documented_in=existing(
                repo,
                "docs/technical/architecture/backend-runtime-classification.md",
                adr0002(repo),
            ),
        )
    )
    add(
        contract(
            cid="OBS-BE-WORLD-ENGINE-CONSOLE-ROUTES",
            title="Backend world-engine console routes",
            summary="Observed admin/JWT proxy surface for controlled play-service observation and operations.",
            contract_type="implementation_surface",
            layer="api",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="backend/app/api/v1/world_engine_console_routes.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:runtime_authority", "implementation", "backend", "admin"],
            owner_or_area="backend",
            scope="admin world-engine console routes",
            validated_by=existing(repo, "backend/tests/test_world_engine_console_routes.py"),
            documented_in=existing(
                repo,
                "docs/technical/architecture/backend-runtime-classification.md",
                adr0002(repo),
            ),
        )
    )

def _extend_evidence_contracts_c_chunk_4(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="OBS-BE-WRITERS-ROOM-ROUTES",
            title="Backend Writers’ Room routes",
            summary="Observed backend review/decision route surface for Writers’ Room workflow execution.",
            contract_type="implementation_surface",
            layer="workflow",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="backend/app/api/v1/writers_room_routes.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:publish_rag", "implementation", "backend"],
            owner_or_area="backend",
            scope="writers-room review routes",
            documented_in=existing(repo, "docs/technical/content/writers-room-and-publishing-flow.md"),
        )
    )
    add(
        contract(
            cid="OBS-CORE-INPUT-INTERPRETER",
            title="Shared input interpreter surface",
            summary="Observed implementation of structured natural-language and command interpretation.",
            contract_type="implementation_surface",
            layer="runtime",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="story_runtime_core/input_interpreter.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:input_turn", "implementation", "core"],
            owner_or_area="story_runtime_core",
            scope="input interpretation logic",
            validated_by=existing(
                repo,
                "story_runtime_core/tests/test_input_interpreter.py",
                "world-engine/tests/test_story_runtime_api.py",
            ),
            documented_in=existing(repo, "docs/technical/runtime/player_input_interpretation_contract.md"),
        )
    )

def _extend_evidence_contracts_c_chunk_5(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="OBS-AI-GOC-SCENE-IDENTITY",
            title="GoC scene identity implementation surface",
            summary="Observed single owned scene identity mapping for GoC guidance and escalation vocabulary.",
            contract_type="implementation_surface",
            layer="ai_machine",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="ai_stack/goc_scene_identity.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:scene_identity", "implementation", "ai_stack"],
            owner_or_area="ai_stack",
            scope="GoC scene identity mapping",
            validated_by=existing(repo, "ai_stack/tests/test_goc_scene_identity.py"),
            documented_in=existing(repo, adr0003(repo)),
        )
    )
    add(
        contract(
            cid="OBS-AI-GOC-YAML-AUTHORITY",
            title="GoC YAML authority surface",
            summary="Observed YAML authority loader/re-export surface consuming the canonical scene identity module.",
            contract_type="implementation_surface",
            layer="ai_machine",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="ai_stack/goc_yaml_authority.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:scene_identity", "implementation", "ai_stack"],
            owner_or_area="ai_stack",
            scope="GoC YAML authority helpers",
            validated_by=existing(repo, "ai_stack/tests/test_goc_scene_identity.py"),
            documented_in=existing(
                repo,
                adr0003(repo),
                "docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md",
            ),
        )
    )

def _extend_evidence_contracts_c_chunk_6(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="OBS-AI-RAG",
            title="RAG implementation surface",
            summary="Observed retrieval corpus, request, ranking, and governance implementation for runtime and Writers’ Room callers.",
            contract_type="implementation_surface",
            layer="ai_machine",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="ai_stack/rag.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:publish_rag", "implementation", "ai_stack", "rag"],
            owner_or_area="ai_stack",
            scope="retrieval implementation",
            validated_by=existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=existing(repo, "docs/technical/ai/RAG.md"),
        )
    )

def extend_evidence_contracts_c(repo: Path, add: Callable[[ContractRecord], None], h: SpineHelpers) -> None:
    contract = h.contract
    existing = h.existing
    one_of = h.one_of
    adr0001 = h.adr0001
    adr0002 = h.adr0002
    adr0003 = h.adr0003
    _extend_evidence_contracts_c_chunk_1(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_evidence_contracts_c_chunk_2(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_evidence_contracts_c_chunk_3(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_evidence_contracts_c_chunk_4(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_evidence_contracts_c_chunk_5(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_evidence_contracts_c_chunk_6(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
