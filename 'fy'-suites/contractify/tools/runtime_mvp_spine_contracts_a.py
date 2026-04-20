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


def _extend_authority_and_slice_contracts_a_chunk_1(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="CTR-ADR-0001-RUNTIME-AUTHORITY",
            title="ADR-0001: Runtime authority in world-engine",
            summary="Accepted runtime authority decision: world-engine owns authoritative live narrative execution.",
            contract_type="adr",
            layer="governance",
            authority_level="normative",
            anchor_kind="document",
            anchor_location=adr0001(repo),
            precedence_tier=RUNTIME_AUTHORITY,
            tags=["family:runtime_authority", "adr", "world-engine"],
            owner_or_area="architecture",
            scope="runtime authority boundary",
            implemented_by=existing(
                repo,
                "world-engine/app/story_runtime/manager.py",
                "world-engine/app/api/http.py",
            ),
            validated_by=existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=existing(
                repo,
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/dev/architecture/runtime-authority-and-session-lifecycle.md",
            ),
            projected_as=existing(repo, "docs/dev/onboarding.md"),
            notes="Authority record outranks slice-level contracts if host ownership claims conflict.",
        )
    )
    add(
        contract(
            cid="CTR-ADR-0002-BACKEND-SESSION-QUARANTINE",
            title="ADR-0002: Backend session / transitional runtime quarantine",
            summary="Accepted quarantine/retirement policy for backend-local session and runtime-shaped surfaces.",
            contract_type="adr",
            layer="governance",
            authority_level="normative",
            anchor_kind="document",
            anchor_location=adr0002(repo),
            precedence_tier=RUNTIME_AUTHORITY,
            tags=["family:runtime_authority", "adr", "backend", "transitional"],
            owner_or_area="architecture",
            scope="backend transitional session surfaces",
            implemented_by=existing(
                repo,
                "backend/app/api/v1/session_routes.py",
                "backend/app/runtime/session_store.py",
                "backend/app/services/session_service.py",
                "backend/app/api/v1/world_engine_console_routes.py",
            ),
            validated_by=existing(
                repo,
                "backend/tests/test_session_routes.py",
                "backend/tests/test_world_engine_console_routes.py",
            ),
            documented_in=existing(
                repo,
                "docs/technical/architecture/backend-runtime-classification.md",
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
            ),
            projected_as=existing(repo, "docs/dev/onboarding.md"),
            notes="Quarantine record governs compatibility and retirement, not live session authority.",
        )
    )

def _extend_authority_and_slice_contracts_a_chunk_2(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="CTR-ADR-0003-SCENE-IDENTITY",
            title="ADR-0003: Single canonical scene identity surface",
            summary="Accepted slice ADR choosing one owned GoC scene-identity surface across compile, AI guidance, and commit.",
            contract_type="adr",
            layer="governance",
            authority_level="normative",
            anchor_kind="document",
            anchor_location=adr0003(repo),
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:scene_identity", "adr", "goc"],
            owner_or_area="ai_stack",
            scope="GoC scene identity seam",
            implemented_by=existing(
                repo,
                "ai_stack/goc_scene_identity.py",
                "ai_stack/goc_yaml_authority.py",
            ),
            validated_by=existing(repo, "ai_stack/tests/test_goc_scene_identity.py"),
            documented_in=existing(
                repo,
                "docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md",
                "docs/ADR/README.md",
            ),
            notes="Slice-specific ADR below runtime authority tier.",
        )
    )

    # First-class normative docs.
    add(
        contract(
            cid="CTR-RUNTIME-AUTHORITY-STATE-FLOW",
            title="Runtime authority and state flow",
            summary="Consolidated runtime host/state progression contract for live play and transitional backend surfaces.",
            contract_type="runtime_contract",
            layer="runtime",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/technical/runtime/runtime-authority-and-state-flow.md",
            precedence_tier=RUNTIME_AUTHORITY,
            tags=["family:runtime_authority", "runtime", "world-engine"],
            owner_or_area="world-engine",
            scope="runtime lifecycle and state authority",
            derived_from=["CTR-ADR-0001-RUNTIME-AUTHORITY"],
            implemented_by=existing(
                repo,
                "world-engine/app/story_runtime/manager.py",
                "world-engine/app/api/http.py",
                "backend/app/runtime/session_store.py",
            ),
            validated_by=existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=existing(
                repo,
                adr0001(repo),
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
            ),
            projected_as=existing(
                repo,
                "docs/dev/onboarding.md",
                "docs/user/runtime-interactions-player-visible.md",
            ),
        )
    )

def _extend_authority_and_slice_contracts_a_chunk_3(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="CTR-BACKEND-RUNTIME-CLASSIFICATION",
            title="Backend runtime classification",
            summary="Classification contract separating backend-local volatile surfaces from authoritative runtime execution.",
            contract_type="runtime_boundary_contract",
            layer="architecture",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/technical/architecture/backend-runtime-classification.md",
            precedence_tier=RUNTIME_AUTHORITY,
            tags=["family:runtime_authority", "backend", "classification"],
            owner_or_area="backend",
            scope="backend transitional runtime boundaries",
            implemented_by=existing(
                repo,
                "backend/app/api/v1/session_routes.py",
                "backend/app/runtime/session_store.py",
                "backend/app/services/session_service.py",
                "backend/app/api/v1/world_engine_console_routes.py",
            ),
            validated_by=existing(
                repo,
                "backend/tests/test_session_routes.py",
                "backend/tests/test_world_engine_console_routes.py",
            ),
            documented_in=existing(
                repo,
                adr0001(repo),
                adr0002(repo),
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
            ),
            projected_as=existing(repo, "docs/technical/architecture/service-boundaries.md"),
        )
    )
    add(
        contract(
            cid="CTR-CANONICAL-RUNTIME-CONTRACT",
            title="Canonical Runtime Contract (Nested Run V1)",
            summary="Binding producer/consumer payload contract for play-service run create/detail/terminate envelopes.",
            contract_type="producer_consumer_contract",
            layer="api",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/technical/architecture/canonical_runtime_contract.md",
            precedence_tier=RUNTIME_AUTHORITY,
            tags=["family:runtime_authority", "api", "payload", "nested-run-v1"],
            owner_or_area="backend",
            scope="world-engine HTTP to backend consumer seam",
            implemented_by=existing(
                repo,
                "world-engine/app/api/http.py",
                "backend/app/services/game_service.py",
            ),
            validated_by=existing(
                repo,
                "backend/tests/test_world_engine_console_routes.py",
            ),
            documented_in=existing(
                repo,
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
            ),
        )
    )

def _extend_authority_and_slice_contracts_a_chunk_4(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="CTR-PLAYER-INPUT-INTERPRETATION",
            title="Player Input Interpretation Contract",
            summary="Structured interpretation contract for raw player text, explicit commands, ambiguity, and delivery hints.",
            contract_type="runtime_input_contract",
            layer="runtime",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/technical/runtime/player_input_interpretation_contract.md",
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:input_turn", "input", "runtime"],
            owner_or_area="story_runtime_core",
            scope="authoritative and preview interpretation of player input",
            implemented_by=existing(
                repo,
                "story_runtime_core/input_interpreter.py",
                "world-engine/app/story_runtime/manager.py",
                "backend/app/api/v1/session_routes.py",
            ),
            validated_by=existing(
                repo,
                "story_runtime_core/tests/test_input_interpreter.py",
                "world-engine/tests/test_story_runtime_api.py",
            ),
            documented_in=existing(
                repo,
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
                "docs/technical/architecture/architecture-overview.md",
            ),
            projected_as=existing(repo, "docs/start-here/how-ai-fits-the-platform.md"),
        )
    )
    add(
        contract(
            cid="CTR-GOC-VERTICAL-SLICE",
            title="GoC Vertical Slice Contract",
            summary="Primary MVP vertical-slice contract defining GoC scope, YAML authority, and runtime bridge expectations.",
            contract_type="slice_contract",
            layer="governance",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md",
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:goc", "slice", "mvp"],
            owner_or_area="product",
            scope="GoC MVP slice",
            implemented_by=existing(
                repo,
                "ai_stack/goc_yaml_authority.py",
                "ai_stack/goc_scene_identity.py",
            ),
            validated_by=existing(
                repo,
                "tests/experience_scoring_cli/test_experience_score_matrix_cli.py",
                "tests/smoke/test_repository_documented_paths_resolve.py",
            ),
            documented_in=existing(
                repo,
                "docs/dev/onboarding.md",
                "docs/user/god-of-carnage-player-guide.md",
            ),
            projected_as=existing(
                repo,
                "docs/ai/ai_system_in_world_of_shadows.md",
                "docs/admin/publishing-and-module-activation.md",
            ),
        )
    )

def _extend_authority_and_slice_contracts_a_chunk_5(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="CTR-GOC-CANONICAL-TURN",
            title="GoC Canonical Turn Contract",
            summary="Binding GoC turn envelope schema for validation, commit, diagnostics, and review.",
            contract_type="turn_contract",
            layer="runtime",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md",
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:goc", "turn", "mvp"],
            owner_or_area="world-engine",
            scope="GoC authoritative turn envelope",
            derived_from=["CTR-GOC-VERTICAL-SLICE"],
            implemented_by=existing(repo, "world-engine/app/story_runtime/manager.py"),
            validated_by=existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=existing(
                repo,
                "docs/user/god-of-carnage-player-guide.md",
                "docs/dev/onboarding.md",
            ),
            projected_as=existing(repo, "docs/ai/ai_system_in_world_of_shadows.md"),
        )
    )

def extend_authority_and_slice_contracts_a(repo: Path, add: Callable[[ContractRecord], None], h: SpineHelpers) -> None:
    contract = h.contract
    existing = h.existing
    one_of = h.one_of
    adr0001 = h.adr0001
    adr0002 = h.adr0002
    adr0003 = h.adr0003
    _extend_authority_and_slice_contracts_a_chunk_1(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_authority_and_slice_contracts_a_chunk_2(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_authority_and_slice_contracts_a_chunk_3(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_authority_and_slice_contracts_a_chunk_4(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_authority_and_slice_contracts_a_chunk_5(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
