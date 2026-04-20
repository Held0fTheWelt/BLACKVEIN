from __future__ import annotations

from pathlib import Path

from contractify.tools.models import ProjectionRecord
from contractify.tools.runtime_mvp_spine_support import SpineHelpers


def _projection_chunk_1(repo: Path, path_target_id, projection, path_to_id: dict[str, str]) -> list[ProjectionRecord | None]:
    return [
        projection(
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
        projection(
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
        projection(
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
    ]

def _projection_chunk_2(repo: Path, path_target_id, projection, path_to_id: dict[str, str]) -> list[ProjectionRecord | None]:
    return [
        projection(
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
        projection(
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
        projection(
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
    ]

def _projection_chunk_3(repo: Path, path_target_id, projection, path_to_id: dict[str, str]) -> list[ProjectionRecord | None]:
    return [
        projection(
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
        projection(
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
        projection(
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
    ]

def _projection_chunk_4(repo: Path, path_target_id, projection, path_to_id: dict[str, str]) -> list[ProjectionRecord | None]:
    return [
        projection(
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

def build_projection_records(repo: Path, path_to_id: dict[str, str], h: SpineHelpers) -> list[ProjectionRecord]:
    projection = h.projection
    path_target_id = h.path_target_id
    projections: list[ProjectionRecord | None] = []
    projections.extend(_projection_chunk_1(repo, path_target_id, projection, path_to_id))
    projections.extend(_projection_chunk_2(repo, path_target_id, projection, path_to_id))
    projections.extend(_projection_chunk_3(repo, path_target_id, projection, path_to_id))
    projections.extend(_projection_chunk_4(repo, path_target_id, projection, path_to_id))
    return [p for p in projections if p is not None]
