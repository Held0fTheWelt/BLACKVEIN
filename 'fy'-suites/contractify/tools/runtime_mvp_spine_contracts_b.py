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


def _extend_slice_contracts_b_chunk_1(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="CTR-GOC-GATE-SCORING",
            title="GoC Gate Scoring Policy",
            summary="Gate/scoring policy for GoC evaluation, fallback classification, and experience acceptance evidence.",
            contract_type="gate_policy",
            layer="policy",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/MVPs/MVP_VSL_And_GoC_Contracts/GATE_SCORING_POLICY_GOC.md",
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:goc", "gate", "scoring"],
            owner_or_area="qa",
            scope="GoC gate scoring and evidence policy",
            validated_by=existing(repo, "tests/experience_scoring_cli/test_experience_score_matrix_cli.py"),
            documented_in=existing(
                repo,
                "docs/audit/gate_G9_experience_acceptance_baseline.md",
                "docs/audit/evidence_artifact_mapping_table.md",
            ),
            projected_as=existing(repo, "docs/goc_evidence_templates/README.md"),
        )
    )
    add(
        contract(
            cid="CTR-WRITERS-ROOM-PUBLISHING-FLOW",
            title="Writers’ Room and publishing flow",
            summary="Backend-first Writers’ Room review/publishing workflow with recommendation-only AI outputs until human publishing governance applies changes.",
            contract_type="content_workflow_contract",
            layer="workflow",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/technical/content/writers-room-and-publishing-flow.md",
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:publish_rag", "writers_room", "publishing"],
            owner_or_area="backend",
            scope="review and publishing governance",
            implemented_by=existing(repo, "backend/app/api/v1/writers_room_routes.py"),
            validated_by=existing(repo, "backend/tests/writers_room/test_writers_room_routes.py"),
            documented_in=existing(repo, "docs/admin/publishing-and-module-activation.md"),
            projected_as=existing(repo, "docs/admin/publishing-and-module-activation.md"),
        )
    )

def _extend_slice_contracts_b_chunk_2(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="CTR-RAG-GOVERNANCE",
            title="RAG governance",
            summary="Retrieval governance contract separating retrieved context from authored canon and committed runtime state.",
            contract_type="ai_retrieval_contract",
            layer="ai_machine",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/technical/ai/RAG.md",
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:publish_rag", "rag", "ai"],
            owner_or_area="ai_stack",
            scope="retrieval domains, governance lanes, and context assembly",
            implemented_by=existing(
                repo,
                "ai_stack/rag.py",
                "world-engine/app/story_runtime/manager.py",
            ),
            validated_by=existing(
                repo,
                "world-engine/tests/test_story_runtime_api.py",
                "ai_stack/tests/test_retrieval_governance_summary.py",
            ),
            documented_in=existing(
                repo,
                "docs/ai/ai_system_in_world_of_shadows.md",
                "docs/technical/integration/LangGraph.md",
                "docs/technical/integration/LangChain.md",
            ),
            projected_as=existing(repo, "docs/ai/ai_system_in_world_of_shadows.md"),
        )
    )

def _extend_slice_contracts_b_chunk_3(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS",
            title="World-Engine authoritative runtime and system interactions",
            summary="Canonical runtime interaction spine describing the play-service HTTP and WebSocket surfaces, story runtime, and backend integration boundaries.",
            contract_type="runtime_system_contract",
            layer="runtime",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
            precedence_tier=RUNTIME_AUTHORITY,
            tags=["family:runtime_authority", "family:websocket_runtime", "runtime", "play-service"],
            owner_or_area="world-engine",
            scope="play-service runtime surfaces and system interactions",
            implemented_by=existing(
                repo,
                "world-engine/app/api/http.py",
                "world-engine/app/api/ws.py",
                "world-engine/app/story_runtime/manager.py",
            ),
            validated_by=existing(
                repo,
                "world-engine/tests/test_story_runtime_api.py",
                "world-engine/tests/test_websocket.py",
            ),
            documented_in=existing(
                repo,
                adr0001(repo),
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/dev/architecture/runtime-authority-and-session-lifecycle.md",
                "docs/api/README.md",
            ),
            projected_as=existing(
                repo,
                "docs/start-here/how-world-of-shadows-works.md",
                "docs/start-here/system-map-services-and-data-stores.md",
                "docs/start-here/what-is-world-of-shadows.md",
                "docs/easy/world_engine_runbook_easy.md",
                "postman/WEBSOCKET_MANUAL.md",
            ),
        )
    )
    add(
        contract(
            cid="CTR-RUNTIME-NARRATIVE-COMMIT",
            title="World-Engine authoritative narrative commit semantics",
            summary="Binding scene progression commit semantics for StoryRuntimeManager, including candidate selection, legality, committed state, and bounded narrative_commit diagnostics.",
            contract_type="runtime_commit_contract",
            layer="runtime",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/technical/runtime/world_engine_authoritative_narrative_commit.md",
            precedence_tier=RUNTIME_AUTHORITY,
            tags=["family:runtime_commit", "runtime", "story_runtime"],
            owner_or_area="world-engine",
            scope="authoritative story narrative commit semantics",
            implemented_by=existing(
                repo,
                "world-engine/app/story_runtime/manager.py",
                "world-engine/app/story_runtime/commit_models.py",
            ),
            validated_by=existing(
                repo,
                "world-engine/tests/test_story_runtime_narrative_commit.py",
                "backend/tests/runtime/test_narrative_commit.py",
            ),
            documented_in=existing(
                repo,
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
                "docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md",
            ),
            projected_as=existing(repo, "docs/easy/world_engine_runbook_easy.md"),
        )
    )

def _extend_slice_contracts_b_chunk_4(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="CTR-AI-STORY-ROUTING-OBSERVATION",
            title="AI story routing and operator audit contract",
            summary="Cross-surface routing-evidence and operator-audit contract for runtime, Writers’ Room, and improvement orchestration surfaces.",
            contract_type="ai_routing_observation_contract",
            layer="architecture",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/technical/architecture/ai_story_contract.md",
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:routing_observability", "routing", "operator_audit", "ai"],
            owner_or_area="backend",
            scope="cross-surface AI routing and operator audit semantics",
            implemented_by=existing(
                repo,
                "backend/app/runtime/model_routing_contracts.py",
                "backend/app/runtime/model_routing_evidence.py",
                "backend/app/runtime/operator_audit.py",
            ),
            validated_by=existing(repo, "backend/tests/runtime/test_cross_surface_operator_audit_contract.py"),
            documented_in=existing(
                repo,
                "docs/audit/repo_evidence_index.md",
                "docs/testing-setup.md",
            ),
        )
    )
    add(
        contract(
            cid="CTR-EVIDENCE-BASELINE-GOVERNANCE",
            title="Evidence baseline and clone reproducibility governance",
            summary="Governance support contract for baseline/closure evidence mapping, tracked-vs-machine-local report handling, and gate summary interpretation.",
            contract_type="evidence_governance_contract",
            layer="governance",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/audit/gate_summary_matrix.md",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:evidence_baseline", "audit", "reproducibility"],
            owner_or_area="qa",
            scope="gate baseline and evidence reproducibility governance",
            documented_in=existing(
                repo,
                "docs/audit/repo_evidence_index.md",
                "docs/audit/evidence_artifact_mapping_table.md",
                "docs/audit/canonical_to_repo_mapping_table.md",
            ),
            validated_by=existing(repo, "tests/smoke/test_smoke_contracts.py"),
        )
    )

def _extend_slice_contracts_b_chunk_5(repo: Path, add: Callable[[ContractRecord], None], contract, existing, one_of, adr0001, adr0002, adr0003) -> None:
    add(
        contract(
            cid="CTR-TESTING-ORCHESTRATION",
            title="Test orchestration and suite runner",
            summary="Repository-level testing governance anchor describing orchestrated suite execution and environment preflight expectations.",
            contract_type="test_governance",
            layer="testing",
            authority_level="verification",
            anchor_kind="document",
            anchor_location="tests/TESTING.md",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:testing", "testing", "orchestration"],
            owner_or_area="qa",
            scope="repository-wide test orchestration",
            implemented_by=existing(repo, "tests/run_tests.py"),
            documented_in=existing(repo, "docs/dev/testing/test-pyramid-and-suite-map.md"),
            projected_as=existing(repo, "docs/testing/README.md"),
            notes="Verification governance anchor, not a product/runtime authority contract.",
        )
    )

def extend_slice_contracts_b(repo: Path, add: Callable[[ContractRecord], None], h: SpineHelpers) -> None:
    contract = h.contract
    existing = h.existing
    one_of = h.one_of
    adr0001 = h.adr0001
    adr0002 = h.adr0002
    adr0003 = h.adr0003
    _extend_slice_contracts_b_chunk_1(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_slice_contracts_b_chunk_2(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_slice_contracts_b_chunk_3(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_slice_contracts_b_chunk_4(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
    _extend_slice_contracts_b_chunk_5(repo, add, contract, existing, one_of, adr0001, adr0002, adr0003)
