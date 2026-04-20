from __future__ import annotations

from contractify.tools.models import RelationEdge


def _relation_chunk_1() -> list[RelationEdge]:
    return [
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
    ]


def _relation_chunk_2() -> list[RelationEdge]:
    return [
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
    ]


def _relation_chunk_3() -> list[RelationEdge]:
    return [
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
    ]


def _relation_chunk_4() -> list[RelationEdge]:
    return [
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
    ]


def _relation_chunk_5() -> list[RelationEdge]:
    return [
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
    ]


def _relation_chunk_6() -> list[RelationEdge]:
    return [
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


def build_relation_edges() -> list[RelationEdge]:
    relations: list[RelationEdge] = []
    relations.extend(_relation_chunk_1())
    relations.extend(_relation_chunk_2())
    relations.extend(_relation_chunk_3())
    relations.extend(_relation_chunk_4())
    relations.extend(_relation_chunk_5())
    relations.extend(_relation_chunk_6())
    return relations
