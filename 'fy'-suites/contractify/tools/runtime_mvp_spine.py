"""Curated runtime/MVP contract spine attachments for World of Shadows.

This module promotes the high-value runtime/MVP contract family into explicit,
related, evidence-attached Contractify records without broad repository mining.
The inventory is intentionally bounded to avoid graph explosion.
"""
from __future__ import annotations

from pathlib import Path

from contractify.tools.adr_governance import first_existing_relative
from contractify.tools.models import ConflictFinding, ContractRecord, ProjectionRecord, RelationEdge


RUNTIME_AUTHORITY = "runtime_authority"
SLICE_NORMATIVE = "slice_normative"
IMPLEMENTATION_EVIDENCE = "implementation_evidence"
VERIFICATION_EVIDENCE = "verification_evidence"
PROJECTION_LOW = "projection_low"


PRECEDENCE_RULES: list[dict[str, object]] = [
    {
        "tier": RUNTIME_AUTHORITY,
        "rank": 1,
        "summary": "Highest-order runtime authority and boundary contracts. These outrank slice detail, implementation observations, and projections when authority clashes are reviewed.",
    },
    {
        "tier": SLICE_NORMATIVE,
        "rank": 2,
        "summary": "Binding MVP / slice contracts and accepted slice-scoped ADRs. These govern GoC behavior beneath the runtime authority layer.",
    },
    {
        "tier": IMPLEMENTATION_EVIDENCE,
        "rank": 3,
        "summary": "Observed code surfaces that embody or operationalize contracts but do not replace normative authority.",
    },
    {
        "tier": VERIFICATION_EVIDENCE,
        "rank": 4,
        "summary": "Test and verification surfaces that support claims about implementation and documented paths.",
    },
    {
        "tier": PROJECTION_LOW,
        "rank": 5,
        "summary": "Lower-weight audience projections and convenience summaries. Useful for navigation, never equal to runtime authority or slice contracts.",
    },
]


def _existing(repo: Path, *rels: str) -> list[str]:
    out: list[str] = []
    for rel in rels:
        rel = rel.replace("\\", "/")
        if (repo / rel).is_file():
            out.append(rel)
    return out


def _one_of(repo: Path, *rels: str) -> list[str]:
    rel = first_existing_relative(repo, *rels)
    return [rel] if rel else []


def _adr0001(repo: Path) -> str:
    return first_existing_relative(
        repo,
        "docs/ADR/adr-0001-runtime-authority-in-world-engine.md",
    )


def _adr0002(repo: Path) -> str:
    return first_existing_relative(
        repo,
        "docs/ADR/adr-0002-backend-session-surface-quarantine.md",
    )


def _adr0003(repo: Path) -> str:
    return first_existing_relative(
        repo,
        "docs/ADR/adr-0003-scene-identity-canonical-surface.md",
    )


def _contract(
    *,
    cid: str,
    title: str,
    summary: str,
    contract_type: str,
    layer: str,
    authority_level: str,
    anchor_kind: str,
    anchor_location: str,
    precedence_tier: str,
    tags: list[str],
    owner_or_area: str,
    scope: str,
    source_of_truth: bool = True,
    status: str = "active",
    version: str = "unversioned",
    confidence: float = 0.95,
    derived_from: list[str] | None = None,
    implemented_by: list[str] | None = None,
    validated_by: list[str] | None = None,
    documented_in: list[str] | None = None,
    projected_as: list[str] | None = None,
    notes: str = "",
) -> ContractRecord:
    return ContractRecord(
        id=cid,
        title=title,
        summary=summary,
        contract_type=contract_type,
        layer=layer,
        status=status,
        version=version,
        authority_level=authority_level,
        anchor_kind=anchor_kind,
        anchor_location=anchor_location,
        source_of_truth=source_of_truth,
        derived_from=derived_from or [],
        implemented_by=implemented_by or [],
        validated_by=validated_by or [],
        documented_in=documented_in or [],
        projected_as=projected_as or [],
        audiences=["developer", "architect"],
        modes=["specialist"],
        scope=scope,
        owner_or_area=owner_or_area,
        confidence=confidence,
        drift_signals=[],
        notes=notes,
        last_verified="",
        change_risk="unknown",
        tags=tags,
        discovery_reason="Curated runtime/MVP spine attachment inventory.",
        precedence_tier=precedence_tier,
    )


def _projection(
    *,
    pid: str,
    title: str,
    path: str,
    source_contract_id: str,
    audience: str,
    mode: str,
    evidence: str,
    anchor_location: str,
    confidence: float = 0.82,
) -> ProjectionRecord:
    return ProjectionRecord(
        id=pid,
        title=title,
        path=path,
        audience=audience,
        mode=mode,
        source_contract_id=source_contract_id,
        anchor_location=anchor_location,
        authoritative=False,
        confidence=confidence,
        evidence=evidence,
        precedence_tier=PROJECTION_LOW,
    )


def _path_target_id(path_to_id: dict[str, str], rel: str) -> str:
    rel = rel.replace("\\", "/")
    return path_to_id.get(rel, f"ART:{rel}")


def _field_edges(records: list[ContractRecord], path_to_id: dict[str, str]) -> list[RelationEdge]:
    out: list[RelationEdge] = []
    for rec in records:
        for dep in rec.derived_from:
            out.append(
                RelationEdge(
                    relation="derives_from",
                    source_id=rec.id,
                    target_id=dep,
                    evidence=f"{rec.anchor_location} declares derived_from={dep} in curated runtime/MVP spine metadata.",
                    confidence=0.96,
                )
            )
        for rel in rec.implemented_by:
            tid = _path_target_id(path_to_id, rel)
            out.append(
                RelationEdge(
                    relation="implemented_by",
                    source_id=rec.id,
                    target_id=tid,
                    evidence=f"Curated attachment links {rec.anchor_location} to implementation surface {rel}.",
                    confidence=0.93,
                )
            )
            out.append(
                RelationEdge(
                    relation="implements",
                    source_id=tid,
                    target_id=rec.id,
                    evidence=f"Implementation surface {rel} materially embodies {rec.anchor_location}.",
                    confidence=0.93,
                )
            )
        for rel in rec.validated_by:
            tid = _path_target_id(path_to_id, rel)
            out.append(
                RelationEdge(
                    relation="validated_by",
                    source_id=rec.id,
                    target_id=tid,
                    evidence=f"Curated attachment links {rec.anchor_location} to verification surface {rel}.",
                    confidence=0.91,
                )
            )
            out.append(
                RelationEdge(
                    relation="validates",
                    source_id=tid,
                    target_id=rec.id,
                    evidence=f"Verification surface {rel} is cited as direct evidence for {rec.anchor_location}.",
                    confidence=0.91,
                )
            )
        for rel in rec.documented_in:
            tid = _path_target_id(path_to_id, rel)
            out.append(
                RelationEdge(
                    relation="documented_in",
                    source_id=rec.id,
                    target_id=tid,
                    evidence=f"Curated attachment records {rel} as supporting documentation for {rec.anchor_location}.",
                    confidence=0.86,
                )
            )
        for rel in rec.projected_as:
            out.append(
                RelationEdge(
                    relation="projected_as",
                    source_id=rec.id,
                    target_id=f"PRJPATH:{rel}",
                    evidence=f"Curated attachment records {rel} as a lower-weight projection of {rec.anchor_location}.",
                    confidence=0.8,
                )
            )
    return out


def build_runtime_mvp_spine(
    repo: Path,
) -> tuple[list[ContractRecord], list[ProjectionRecord], list[RelationEdge], list[ConflictFinding], dict[str, list[str]]]:
    repo = repo.resolve()
    contracts: list[ContractRecord] = []
    path_to_id: dict[str, str] = {}

    def add(rec: ContractRecord) -> None:
        if not (repo / rec.anchor_location).is_file():
            return
        contracts.append(rec)
        path_to_id[rec.anchor_location] = rec.id

    # High-order runtime authority + ADRs.
    add(
        _contract(
            cid="CTR-ADR-0001-RUNTIME-AUTHORITY",
            title="ADR-0001: Runtime authority in world-engine",
            summary="Accepted runtime authority decision: world-engine owns authoritative live narrative execution.",
            contract_type="adr",
            layer="governance",
            authority_level="normative",
            anchor_kind="document",
            anchor_location=_adr0001(repo),
            precedence_tier=RUNTIME_AUTHORITY,
            tags=["family:runtime_authority", "adr", "world-engine"],
            owner_or_area="architecture",
            scope="runtime authority boundary",
            implemented_by=_existing(
                repo,
                "world-engine/app/story_runtime/manager.py",
                "world-engine/app/api/http.py",
            ),
            validated_by=_existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=_existing(
                repo,
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/dev/architecture/runtime-authority-and-session-lifecycle.md",
            ),
            projected_as=_existing(repo, "docs/dev/onboarding.md"),
            notes="Authority record outranks slice-level contracts if host ownership claims conflict.",
        )
    )
    add(
        _contract(
            cid="CTR-ADR-0002-BACKEND-SESSION-QUARANTINE",
            title="ADR-0002: Backend session / transitional runtime quarantine",
            summary="Accepted quarantine/retirement policy for backend-local session and runtime-shaped surfaces.",
            contract_type="adr",
            layer="governance",
            authority_level="normative",
            anchor_kind="document",
            anchor_location=_adr0002(repo),
            precedence_tier=RUNTIME_AUTHORITY,
            tags=["family:runtime_authority", "adr", "backend", "transitional"],
            owner_or_area="architecture",
            scope="backend transitional session surfaces",
            implemented_by=_existing(
                repo,
                "backend/app/api/v1/session_routes.py",
                "backend/app/runtime/session_store.py",
                "backend/app/services/session_service.py",
                "backend/app/api/v1/world_engine_console_routes.py",
            ),
            validated_by=_existing(
                repo,
                "backend/tests/test_session_routes.py",
                "backend/tests/test_world_engine_console_routes.py",
            ),
            documented_in=_existing(
                repo,
                "docs/technical/architecture/backend-runtime-classification.md",
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
            ),
            projected_as=_existing(repo, "docs/dev/onboarding.md"),
            notes="Quarantine record governs compatibility and retirement, not live session authority.",
        )
    )
    add(
        _contract(
            cid="CTR-ADR-0003-SCENE-IDENTITY",
            title="ADR-0003: Single canonical scene identity surface",
            summary="Accepted slice ADR choosing one owned GoC scene-identity surface across compile, AI guidance, and commit.",
            contract_type="adr",
            layer="governance",
            authority_level="normative",
            anchor_kind="document",
            anchor_location=_adr0003(repo),
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:scene_identity", "adr", "goc"],
            owner_or_area="ai_stack",
            scope="GoC scene identity seam",
            implemented_by=_existing(
                repo,
                "ai_stack/goc_scene_identity.py",
                "ai_stack/goc_yaml_authority.py",
            ),
            validated_by=_existing(repo, "ai_stack/tests/test_goc_scene_identity.py"),
            documented_in=_existing(
                repo,
                "docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md",
                "docs/ADR/README.md",
            ),
            notes="Slice-specific ADR below runtime authority tier.",
        )
    )

    # First-class normative docs.
    add(
        _contract(
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
            implemented_by=_existing(
                repo,
                "world-engine/app/story_runtime/manager.py",
                "world-engine/app/api/http.py",
                "backend/app/runtime/session_store.py",
            ),
            validated_by=_existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=_existing(
                repo,
                _adr0001(repo),
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
            ),
            projected_as=_existing(
                repo,
                "docs/dev/onboarding.md",
                "docs/user/runtime-interactions-player-visible.md",
            ),
        )
    )
    add(
        _contract(
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
            implemented_by=_existing(
                repo,
                "backend/app/api/v1/session_routes.py",
                "backend/app/runtime/session_store.py",
                "backend/app/services/session_service.py",
                "backend/app/api/v1/world_engine_console_routes.py",
            ),
            validated_by=_existing(
                repo,
                "backend/tests/test_session_routes.py",
                "backend/tests/test_world_engine_console_routes.py",
            ),
            documented_in=_existing(
                repo,
                _adr0001(repo),
                _adr0002(repo),
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
            ),
            projected_as=_existing(repo, "docs/technical/architecture/service-boundaries.md"),
        )
    )
    add(
        _contract(
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
            implemented_by=_existing(
                repo,
                "world-engine/app/api/http.py",
                "backend/app/services/game_service.py",
            ),
            validated_by=_existing(
                repo,
                "backend/tests/test_world_engine_console_routes.py",
            ),
            documented_in=_existing(
                repo,
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
            ),
        )
    )
    add(
        _contract(
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
            implemented_by=_existing(
                repo,
                "story_runtime_core/input_interpreter.py",
                "world-engine/app/story_runtime/manager.py",
                "backend/app/api/v1/session_routes.py",
            ),
            validated_by=_existing(
                repo,
                "story_runtime_core/tests/test_input_interpreter.py",
                "world-engine/tests/test_story_runtime_api.py",
            ),
            documented_in=_existing(
                repo,
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
                "docs/technical/architecture/architecture-overview.md",
            ),
            projected_as=_existing(repo, "docs/start-here/how-ai-fits-the-platform.md"),
        )
    )
    add(
        _contract(
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
            implemented_by=_existing(
                repo,
                "ai_stack/goc_yaml_authority.py",
                "ai_stack/goc_scene_identity.py",
            ),
            validated_by=_existing(
                repo,
                "tests/experience_scoring_cli/test_experience_score_matrix_cli.py",
                "tests/smoke/test_repository_documented_paths_resolve.py",
            ),
            documented_in=_existing(
                repo,
                "docs/dev/onboarding.md",
                "docs/user/god-of-carnage-player-guide.md",
            ),
            projected_as=_existing(
                repo,
                "docs/ai/ai_system_in_world_of_shadows.md",
                "docs/admin/publishing-and-module-activation.md",
            ),
        )
    )
    add(
        _contract(
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
            implemented_by=_existing(repo, "world-engine/app/story_runtime/manager.py"),
            validated_by=_existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=_existing(
                repo,
                "docs/user/god-of-carnage-player-guide.md",
                "docs/dev/onboarding.md",
            ),
            projected_as=_existing(repo, "docs/ai/ai_system_in_world_of_shadows.md"),
        )
    )
    add(
        _contract(
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
            validated_by=_existing(repo, "tests/experience_scoring_cli/test_experience_score_matrix_cli.py"),
            documented_in=_existing(
                repo,
                "docs/audit/gate_G9_experience_acceptance_baseline.md",
                "docs/audit/evidence_artifact_mapping_table.md",
            ),
            projected_as=_existing(repo, "docs/goc_evidence_templates/README.md"),
        )
    )
    add(
        _contract(
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
            implemented_by=_existing(repo, "backend/app/api/v1/writers_room_routes.py"),
            validated_by=_existing(repo, "backend/tests/writers_room/test_writers_room_routes.py"),
            documented_in=_existing(repo, "docs/admin/publishing-and-module-activation.md"),
            projected_as=_existing(repo, "docs/admin/publishing-and-module-activation.md"),
        )
    )
    add(
        _contract(
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
            implemented_by=_existing(
                repo,
                "ai_stack/rag.py",
                "world-engine/app/story_runtime/manager.py",
            ),
            validated_by=_existing(
                repo,
                "world-engine/tests/test_story_runtime_api.py",
                "ai_stack/tests/test_retrieval_governance_summary.py",
            ),
            documented_in=_existing(
                repo,
                "docs/ai/ai_system_in_world_of_shadows.md",
                "docs/technical/integration/LangGraph.md",
                "docs/technical/integration/LangChain.md",
            ),
            projected_as=_existing(repo, "docs/ai/ai_system_in_world_of_shadows.md"),
        )
    )

    add(
        _contract(
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
            implemented_by=_existing(
                repo,
                "world-engine/app/api/http.py",
                "world-engine/app/api/ws.py",
                "world-engine/app/story_runtime/manager.py",
            ),
            validated_by=_existing(
                repo,
                "world-engine/tests/test_story_runtime_api.py",
                "world-engine/tests/test_websocket.py",
            ),
            documented_in=_existing(
                repo,
                _adr0001(repo),
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/dev/architecture/runtime-authority-and-session-lifecycle.md",
                "docs/api/README.md",
            ),
            projected_as=_existing(
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
        _contract(
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
            implemented_by=_existing(
                repo,
                "world-engine/app/story_runtime/manager.py",
                "world-engine/app/story_runtime/commit_models.py",
            ),
            validated_by=_existing(
                repo,
                "world-engine/tests/test_story_runtime_narrative_commit.py",
                "backend/tests/runtime/test_narrative_commit.py",
            ),
            documented_in=_existing(
                repo,
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
                "docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md",
            ),
            projected_as=_existing(repo, "docs/easy/world_engine_runbook_easy.md"),
        )
    )
    add(
        _contract(
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
            implemented_by=_existing(
                repo,
                "backend/app/runtime/model_routing_contracts.py",
                "backend/app/runtime/model_routing_evidence.py",
                "backend/app/runtime/operator_audit.py",
            ),
            validated_by=_existing(repo, "backend/tests/runtime/test_cross_surface_operator_audit_contract.py"),
            documented_in=_existing(
                repo,
                "docs/audit/repo_evidence_index.md",
                "docs/testing-setup.md",
            ),
        )
    )
    add(
        _contract(
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
            documented_in=_existing(
                repo,
                "docs/audit/repo_evidence_index.md",
                "docs/audit/evidence_artifact_mapping_table.md",
                "docs/audit/canonical_to_repo_mapping_table.md",
            ),
            validated_by=_existing(repo, "tests/smoke/test_smoke_contracts.py"),
        )
    )

    add(
        _contract(
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
            implemented_by=_existing(repo, "tests/run_tests.py"),
            documented_in=_existing(repo, "docs/dev/testing/test-pyramid-and-suite-map.md"),
            projected_as=_existing(repo, "docs/testing/README.md"),
            notes="Verification governance anchor, not a product/runtime authority contract.",
        )
    )

    # Mandatory implementation / evidence surfaces.
    add(
        _contract(
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
            validated_by=_existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=_existing(
                repo,
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/technical/ai/RAG.md",
            ),
        )
    )
    add(
        _contract(
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
            validated_by=_existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=_existing(
                repo,
                "docs/technical/architecture/canonical_runtime_contract.md",
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
            ),
        )
    )
    add(
        _contract(
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
            validated_by=_existing(repo, "backend/tests/test_session_routes.py"),
            documented_in=_existing(
                repo,
                "docs/technical/architecture/backend-runtime-classification.md",
                _adr0002(repo),
            ),
        )
    )
    add(
        _contract(
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
            documented_in=_existing(
                repo,
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/technical/architecture/backend-runtime-classification.md",
                _adr0002(repo),
            ),
        )
    )
    add(
        _contract(
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
            documented_in=_existing(
                repo,
                "docs/technical/architecture/backend-runtime-classification.md",
                _adr0002(repo),
            ),
        )
    )
    add(
        _contract(
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
            validated_by=_existing(repo, "backend/tests/test_world_engine_console_routes.py"),
            documented_in=_existing(
                repo,
                "docs/technical/architecture/backend-runtime-classification.md",
                _adr0002(repo),
            ),
        )
    )
    add(
        _contract(
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
            documented_in=_existing(repo, "docs/technical/content/writers-room-and-publishing-flow.md"),
        )
    )
    add(
        _contract(
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
            validated_by=_existing(
                repo,
                "story_runtime_core/tests/test_input_interpreter.py",
                "world-engine/tests/test_story_runtime_api.py",
            ),
            documented_in=_existing(repo, "docs/technical/runtime/player_input_interpretation_contract.md"),
        )
    )
    add(
        _contract(
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
            validated_by=_existing(repo, "ai_stack/tests/test_goc_scene_identity.py"),
            documented_in=_existing(repo, _adr0003(repo)),
        )
    )
    add(
        _contract(
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
            validated_by=_existing(repo, "ai_stack/tests/test_goc_scene_identity.py"),
            documented_in=_existing(
                repo,
                _adr0003(repo),
                "docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md",
            ),
        )
    )
    add(
        _contract(
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
            validated_by=_existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=_existing(repo, "docs/technical/ai/RAG.md"),
        )
    )
    add(
        _contract(
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
            documented_in=_existing(
                repo,
                "docs/technical/architecture/canonical_runtime_contract.md",
                "docs/technical/architecture/backend-runtime-classification.md",
            ),
        )
    )

    add(
        _contract(
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
            validated_by=_existing(
                repo,
                "world-engine/tests/test_websocket.py",
                "world-engine/tests/test_ws_auth.py",
            ),
            documented_in=_existing(
                repo,
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
                "docs/api/README.md",
            ),
        )
    )
    add(
        _contract(
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
            validated_by=_existing(repo, "world-engine/tests/test_story_runtime_narrative_commit.py"),
            documented_in=_existing(repo, "docs/technical/runtime/world_engine_authoritative_narrative_commit.md"),
        )
    )
    add(
        _contract(
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
            documented_in=_existing(repo, "docs/technical/architecture/ai_story_contract.md"),
        )
    )
    add(
        _contract(
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
            validated_by=_existing(repo, "backend/tests/runtime/test_cross_surface_operator_audit_contract.py"),
            documented_in=_existing(repo, "docs/technical/architecture/ai_story_contract.md"),
        )
    )

    add(
        _contract(
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
            documented_in=_existing(repo, "tests/TESTING.md"),
        )
    )
    add(
        _contract(
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
            documented_in=_existing(
                repo,
                _adr0003(repo),
                "docs/audit/repo_evidence_index.md",
            ),
        )
    )
    add(
        _contract(
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
            documented_in=_existing(repo, "docs/technical/runtime/player_input_interpretation_contract.md"),
        )
    )
    add(
        _contract(
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
            documented_in=_existing(
                repo,
                "docs/audit/repo_evidence_index.md",
                "docs/audit/gate_G9_experience_acceptance_baseline.md",
            ),
        )
    )
    add(
        _contract(
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
            documented_in=_existing(repo, "docs/audit/repo_evidence_index.md"),
        )
    )
    add(
        _contract(
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
            documented_in=_existing(repo, "tests/TESTING.md"),
        )
    )
    add(
        _contract(
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
            documented_in=_existing(repo, "tests/TESTING.md"),
        )
    )

    add(
        _contract(
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
            documented_in=_existing(repo, "docs/technical/ai/RAG.md", "tests/TESTING.md"),
        )
    )
    add(
        _contract(
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
            documented_in=_existing(repo, "docs/technical/content/writers-room-and-publishing-flow.md", "tests/TESTING.md"),
        )
    )

    add(
        _contract(
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
            documented_in=_existing(repo, "docs/technical/runtime/world_engine_authoritative_narrative_commit.md", "tests/TESTING.md"),
        )
    )
    add(
        _contract(
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
            documented_in=_existing(repo, "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md", "tests/TESTING.md"),
        )
    )
    add(
        _contract(
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
            documented_in=_existing(repo, "docs/technical/architecture/ai_story_contract.md", "docs/audit/repo_evidence_index.md", "tests/TESTING.md"),
        )
    )


    projections = [
        _projection(
            pid="PRJ-RUNTIME-AUTH-ONBOARDING",
            title="Developer onboarding runtime authority summary",
            path="docs/dev/onboarding.md",
            source_contract_id="CTR-RUNTIME-AUTHORITY-STATE-FLOW",
            audience="developer",
            mode="easy",
            evidence="Onboarding links runtime authority and GoC contract family as navigation surface.",
            anchor_location="docs/technical/runtime/runtime-authority-and-state-flow.md",
        )
        if (repo / "docs/dev/onboarding.md").is_file()
        else None,
        _projection(
            pid="PRJ-GOC-PLAYER-GUIDE",
            title="Player-facing GoC guide",
            path="docs/user/god-of-carnage-player-guide.md",
            source_contract_id="CTR-GOC-VERTICAL-SLICE",
            audience="user",
            mode="easy",
            evidence="Player guide summarizes the slice and turn contract family for a non-authority audience.",
            anchor_location="docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md",
        )
        if (repo / "docs/user/god-of-carnage-player-guide.md").is_file()
        else None,
        _projection(
            pid="PRJ-PUBLISHING-ADMIN-GUIDE",
            title="Admin publishing guide",
            path="docs/admin/publishing-and-module-activation.md",
            source_contract_id="CTR-WRITERS-ROOM-PUBLISHING-FLOW",
            audience="operator",
            mode="easy",
            evidence="Admin guide summarizes Writers’ Room / publishing flow for operational consumers.",
            anchor_location="docs/technical/content/writers-room-and-publishing-flow.md",
        )
        if (repo / "docs/admin/publishing-and-module-activation.md").is_file()
        else None,
        _projection(
            pid="PRJ-AI-SYSTEM-RAG-SUMMARY",
            title="AI system overview RAG summary",
            path="docs/ai/ai_system_in_world_of_shadows.md",
            source_contract_id="CTR-RAG-GOVERNANCE",
            audience="developer",
            mode="easy",
            evidence="AI system overview re-presents RAG and runtime authority concepts for cross-system navigation.",
            anchor_location="docs/technical/ai/RAG.md",
        )
        if (repo / "docs/ai/ai_system_in_world_of_shadows.md").is_file()
        else None,
        _projection(
            pid="PRJ-RUNTIME-SESSION-LIFECYCLE",
            title="Developer runtime authority and session lifecycle seam note",
            path="docs/dev/architecture/runtime-authority-and-session-lifecycle.md",
            source_contract_id="CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS",
            audience="developer",
            mode="specialist",
            evidence="Developer seam note restates runtime/session boundaries beneath the authoritative interaction spine.",
            anchor_location="docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
        )
        if (repo / "docs/dev/architecture/runtime-authority-and-session-lifecycle.md").is_file()
        else None,
        _projection(
            pid="PRJ-API-README",
            title="API documentation overview",
            path="docs/api/README.md",
            source_contract_id="CTR-API-OPENAPI-001",
            audience="developer",
            mode="specialist",
            evidence="API README summarizes machine-readable OpenAPI and linked play-service endpoints for human navigation.",
            anchor_location="docs/api/openapi.yaml",
        )
        if (repo / "docs/api/README.md").is_file()
        else None,
        _projection(
            pid="PRJ-API-REFERENCE",
            title="API reference examples",
            path="docs/api/REFERENCE.md",
            source_contract_id="CTR-API-OPENAPI-001",
            audience="developer",
            mode="specialist",
            evidence="REFERENCE.md provides human-readable request/response examples derived from the API surface.",
            anchor_location="docs/api/openapi.yaml",
        )
        if (repo / "docs/api/REFERENCE.md").is_file()
        else None,
        _projection(
            pid="PRJ-API-POSTMAN-GUIDE",
            title="Historical Postman alignment guide",
            path="docs/api/POSTMAN_COLLECTION.md",
            source_contract_id="CTR-API-OPENAPI-001",
            audience="developer",
            mode="specialist",
            evidence="POSTMAN_COLLECTION.md is an explicitly historical guide subordinate to generated Postman assets.",
            anchor_location="docs/api/openapi.yaml",
        )
        if (repo / "docs/api/POSTMAN_COLLECTION.md").is_file()
        else None,
        _projection(
            pid="PRJ-POSTMAN-README",
            title="Generated Postman suite overview",
            path="postman/README.md",
            source_contract_id="CTR-API-OPENAPI-001",
            audience="developer",
            mode="specialist",
            evidence="postman/README.md explains generated collections as projections of the OpenAPI surface.",
            anchor_location="docs/api/openapi.yaml",
        )
        if (repo / "postman/README.md").is_file()
        else None,
        _projection(
            pid="PRJ-POSTMAN-WS-MANUAL",
            title="Manual WebSocket validation guide",
            path="postman/WEBSOCKET_MANUAL.md",
            source_contract_id="CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS",
            audience="operator",
            mode="specialist",
            evidence="WebSocket manual stays a lower-weight validation aid beneath the authoritative runtime interaction contract.",
            anchor_location="docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
        )
        if (repo / "postman/WEBSOCKET_MANUAL.md").is_file()
        else None,
    ]
    projections = [p for p in projections if p is not None]

    for prj in projections:
        path_to_id[prj.path] = prj.id

    relations = _field_edges(contracts, path_to_id)
    relations.extend(
        [
            RelationEdge(
                relation="refines",
                source_id="CTR-RUNTIME-AUTHORITY-STATE-FLOW",
                target_id="CTR-ADR-0001-RUNTIME-AUTHORITY",
                evidence="The technical runtime authority page expands ADR-0001 into an operational ownership matrix and lifecycle narrative.",
                confidence=0.97,
            ),
            RelationEdge(
                relation="refines",
                source_id="CTR-BACKEND-RUNTIME-CLASSIFICATION",
                target_id="CTR-ADR-0001-RUNTIME-AUTHORITY",
                evidence="The backend classification page clarifies what ADR-0001 forbids inside Flask as live runtime authority.",
                confidence=0.95,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="CTR-BACKEND-RUNTIME-CLASSIFICATION",
                target_id="CTR-ADR-0002-BACKEND-SESSION-QUARANTINE",
                evidence="The classification document turns ADR-0002 quarantine language into concrete package/module labels.",
                confidence=0.96,
            ),
            RelationEdge(
                relation="depends_on",
                source_id="CTR-CANONICAL-RUNTIME-CONTRACT",
                target_id="CTR-ADR-0001-RUNTIME-AUTHORITY",
                evidence="The nested-run producer/consumer contract assumes a single authoritative run host chosen by ADR-0001.",
                confidence=0.95,
            ),
            RelationEdge(
                relation="depends_on",
                source_id="CTR-CANONICAL-RUNTIME-CONTRACT",
                target_id="CTR-ADR-0002-BACKEND-SESSION-QUARANTINE",
                evidence="The backend consumer rules in Nested Run V1 sit beside ADR-0002’s prohibition on treating backend-local session surfaces as equivalent runtime truth.",
                confidence=0.86,
            ),
            RelationEdge(
                relation="depends_on",
                source_id="CTR-GOC-GATE-SCORING",
                target_id="CTR-GOC-CANONICAL-TURN",
                evidence="Gate scoring references turn-envelope semantics and preview/productive classification from the canonical turn contract.",
                confidence=0.95,
            ),
            RelationEdge(
                relation="depends_on",
                source_id="CTR-GOC-GATE-SCORING",
                target_id="CTR-GOC-VERTICAL-SLICE",
                evidence="Gate scoring depends on the slice’s scope, vocabulary, and failure-mode boundaries.",
                confidence=0.95,
            ),
            RelationEdge(
                relation="overlaps_with",
                source_id="CTR-WRITERS-ROOM-PUBLISHING-FLOW",
                target_id="CTR-RAG-GOVERNANCE",
                evidence="The Writers’ Room workflow explicitly invokes context pack building and retrieval analysis, but the publishing flow keeps human/backend publishing authority separate from retrieval output.",
                confidence=0.9,
            ),
            RelationEdge(
                relation="overlaps_with",
                source_id="CTR-RAG-GOVERNANCE",
                target_id="CTR-WRITERS-ROOM-PUBLISHING-FLOW",
                evidence="RAG defines a Writers’ Room retrieval domain/profile while remaining subordinate to the human publishing workflow.",
                confidence=0.9,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="OBS-WE-STORY-RUNTIME-MANAGER",
                target_id="CTR-RUNTIME-AUTHORITY-STATE-FLOW",
                evidence="StoryRuntimeManager is named as the first code anchor on the runtime-authority page and wires runtime sessions, retrieval, and turn execution.",
                confidence=0.94,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="OBS-BE-SESSION-ROUTES",
                target_id="CTR-BACKEND-RUNTIME-CLASSIFICATION",
                evidence="Session routes embody the backend-local quarantine by returning warnings and bridging to the world-engine for authoritative turns.",
                confidence=0.93,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="OBS-BE-WORLD-ENGINE-CONSOLE-ROUTES",
                target_id="CTR-ADR-0002-BACKEND-SESSION-QUARANTINE",
                evidence="Admin console routes are the documented compat/operator surface in ADR-0002 Appendix A.",
                confidence=0.92,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="OBS-BE-WRITERS-ROOM-ROUTES",
                target_id="CTR-WRITERS-ROOM-PUBLISHING-FLOW",
                evidence="Writers’ Room review/decision routes expose the backend-first workflow described in the publishing-flow document.",
                confidence=0.93,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="OBS-AI-RAG",
                target_id="CTR-RAG-GOVERNANCE",
                evidence="ai_stack/rag.py is the primary implementation anchor listed in RAG.md.",
                confidence=0.95,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-RUNTIME-AUTH-ONBOARDING",
                target_id="CTR-RUNTIME-AUTHORITY-STATE-FLOW",
                evidence="Onboarding doc condenses the runtime authority contract for navigation.",
                confidence=0.83,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-GOC-PLAYER-GUIDE",
                target_id="CTR-GOC-VERTICAL-SLICE",
                evidence="Player guide summarizes GoC slice rules and canonical turn semantics for a lower-authority audience.",
                confidence=0.82,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-PUBLISHING-ADMIN-GUIDE",
                target_id="CTR-WRITERS-ROOM-PUBLISHING-FLOW",
                evidence="Admin publishing guide restates the backend-first publishing path.",
                confidence=0.83,
            ),
            RelationEdge(
                relation="depends_on",
                source_id="CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS",
                target_id="CTR-ADR-0001-RUNTIME-AUTHORITY",
                evidence="The runtime interactions spine assumes ADR-0001 as the single live-runtime host authority decision.",
                confidence=0.96,
            ),
            RelationEdge(
                relation="depends_on",
                source_id="CTR-RUNTIME-NARRATIVE-COMMIT",
                target_id="CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS",
                evidence="Narrative commit semantics sit inside the broader authoritative runtime interaction surface.",
                confidence=0.95,
            ),
            RelationEdge(
                relation="depends_on",
                source_id="CTR-RUNTIME-NARRATIVE-COMMIT",
                target_id="CTR-GOC-CANONICAL-TURN",
                evidence="Narrative commit semantics are the bounded authoritative commit realization for the GoC canonical turn path.",
                confidence=0.9,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="OBS-WE-WS-API",
                target_id="CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS",
                evidence="The WebSocket router is the code surface named by the interactions spine for live ticket-gated runtime commands.",
                confidence=0.94,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="OBS-WE-COMMIT-MODELS",
                target_id="CTR-RUNTIME-NARRATIVE-COMMIT",
                evidence="Commit models define the bounded narrative_commit payload described in the authoritative narrative commit document.",
                confidence=0.94,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="OBS-BE-MODEL-ROUTING-CONTRACTS",
                target_id="CTR-AI-STORY-ROUTING-OBSERVATION",
                evidence="Routing contract types provide the bounded reason-code and request vocabulary described by the AI story contract.",
                confidence=0.93,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="OBS-BE-OPERATOR-AUDIT",
                target_id="CTR-AI-STORY-ROUTING-OBSERVATION",
                evidence="operator_audit.py materially assembles the cross-surface operator audit shell defined in the AI story contract.",
                confidence=0.93,
            ),
            RelationEdge(
                relation="validated_by",
                source_id="CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS",
                target_id="VER-WE-WS-TEST",
                evidence="WebSocket tests directly validate the live runtime interaction surface named in the interactions document.",
                confidence=0.91,
            ),
            RelationEdge(
                relation="validated_by",
                source_id="CTR-RUNTIME-NARRATIVE-COMMIT",
                target_id="VER-WE-NARRATIVE-COMMIT-TEST",
                evidence="Narrative commit tests assert the bounded commit semantics described in the authoritative narrative commit page.",
                confidence=0.91,
            ),
            RelationEdge(
                relation="validated_by",
                source_id="CTR-AI-STORY-ROUTING-OBSERVATION",
                target_id="VER-BE-CROSS-SURFACE-OPERATOR-AUDIT-TEST",
                evidence="Cross-surface operator audit tests assert the additive routing_evidence/operator_audit contract family described in ai_story_contract.md.",
                confidence=0.91,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-AI-SYSTEM-RAG-SUMMARY",
                target_id="CTR-RAG-GOVERNANCE",
                evidence="AI system overview reuses RAG governance as a summarized system map.",
                confidence=0.82,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-RUNTIME-SESSION-LIFECYCLE",
                target_id="CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS",
                evidence="Developer seam note condenses the authoritative runtime interaction contract for implementers.",
                confidence=0.82,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-API-README",
                target_id="CTR-API-OPENAPI-001",
                evidence="API README is a lower-weight human-readable projection of the machine-readable OpenAPI surface.",
                confidence=0.82,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-API-REFERENCE",
                target_id="CTR-API-OPENAPI-001",
                evidence="REFERENCE.md provides examples and prose beneath the authoritative OpenAPI anchor.",
                confidence=0.82,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-API-POSTMAN-GUIDE",
                target_id="CTR-API-OPENAPI-001",
                evidence="Historical Postman guide now explicitly points back to generated OpenAPI-derived assets.",
                confidence=0.8,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-POSTMAN-README",
                target_id="CTR-API-OPENAPI-001",
                evidence="Postman README documents collections as generated projections of OpenAPI.",
                confidence=0.83,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-POSTMAN-WS-MANUAL",
                target_id="CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS",
                evidence="The manual WebSocket validation guide is a lower-weight operational projection of the authoritative runtime interaction contract.",
                confidence=0.81,
            ),
        ]
    )

    unresolved = [
        ConflictFinding(
            id="CNF-RUNTIME-SPINE-TRANSITIONAL-RETIREMENT",
            conflict_type="intentional_unresolved_transition_boundary",
            summary="Backend transitional session surfaces are now attached and weighted, but the actual retirement timeline remains intentionally unresolved.",
            sources=[
                _adr0002(repo),
                "docs/technical/architecture/backend-runtime-classification.md",
                "backend/app/api/v1/session_routes.py",
                "backend/app/runtime/session_store.py",
                "backend/app/services/session_service.py",
            ],
            confidence=0.84,
            requires_human_review=True,
            notes="Governed as quarantine/compat today; removal timing still needs explicit decision-log entries.",
            classification="runtime_transition_retirement_open",
            normative_sources=[
                _adr0002(repo),
                "docs/technical/architecture/backend-runtime-classification.md",
            ],
            observed_or_projection_sources=[
                "backend/app/api/v1/session_routes.py",
                "backend/app/runtime/session_store.py",
                "backend/app/services/session_service.py",
            ],
            kind="intentional_unresolved_boundary",
            severity="medium",
            normative_candidates=[
                _adr0002(repo),
                "docs/technical/architecture/backend-runtime-classification.md",
            ],
            observed_candidates=[
                "backend/app/api/v1/session_routes.py",
                "backend/app/runtime/session_store.py",
                "backend/app/services/session_service.py",
            ],
        ),
        ConflictFinding(
            id="CNF-EVIDENCE-BASELINE-CLONE-REPRO",
            conflict_type="intentional_clone_reproducibility_boundary",
            summary="Audit docs intentionally cite machine-local tests/reports evidence paths while clone reproducibility only guarantees the tracked subset; this boundary must stay explicit in governance review.",
            sources=[
                "docs/audit/gate_summary_matrix.md",
                "docs/audit/repo_evidence_index.md",
                ".gitignore",
                "tests/reports",
            ],
            confidence=0.83,
            requires_human_review=True,
            notes="This is an honest reproducibility boundary, not a reason to treat machine-local evidence trees as clone-guaranteed truth.",
            classification="clone_reproducibility_boundary",
            normative_sources=[
                "docs/audit/gate_summary_matrix.md",
                "docs/audit/repo_evidence_index.md",
            ],
            observed_or_projection_sources=[
                ".gitignore",
                "tests/reports",
            ],
            kind="reviewable_reproducibility_boundary",
            severity="medium",
            normative_candidates=[
                "docs/audit/gate_summary_matrix.md",
                "docs/audit/repo_evidence_index.md",
            ],
            observed_candidates=[
                ".gitignore",
                "tests/reports",
            ],
        ),
        ConflictFinding(
            id="CNF-RUNTIME-SPINE-WRITERS-RAG-OVERLAP",
            conflict_type="intentional_overlap_boundary",
            summary="Writers’ Room workflow and RAG governance intentionally overlap at retrieval/context-pack assembly, but publishing authority and runtime truth remain distinct and should stay explicitly reviewed.",
            sources=[
                "docs/technical/content/writers-room-and-publishing-flow.md",
                "docs/technical/ai/RAG.md",
                "backend/app/api/v1/writers_room_routes.py",
                "ai_stack/rag.py",
            ],
            confidence=0.8,
            requires_human_review=True,
            notes="Not a contradiction today; keep reviewable so future retrieval write-backs do not flatten authority boundaries.",
            classification="intentional_overlap_boundary",
            normative_sources=[
                "docs/technical/content/writers-room-and-publishing-flow.md",
                "docs/technical/ai/RAG.md",
            ],
            observed_or_projection_sources=[
                "backend/app/api/v1/writers_room_routes.py",
                "ai_stack/rag.py",
            ],
            kind="reviewable_overlap",
            severity="medium",
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

    return contracts, projections, relations, unresolved, families
