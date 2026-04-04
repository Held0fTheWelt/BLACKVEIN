from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
try:
    from enum import StrEnum
except ImportError:
    # Python < 3.11 fallback
    from enum import Enum
    class StrEnum(str, Enum):
        def __str__(self) -> str:
            return self.value
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from wos_ai_stack.rag import ContextPackAssembler, ContextRetriever, RetrievalDomain, RetrievalRequest


class CapabilityKind(StrEnum):
    RETRIEVAL = "retrieval"
    ACTION = "action"


class CapabilityAccessDeniedError(PermissionError):
    def __init__(self, capability_name: str, mode: str) -> None:
        super().__init__(f"Capability '{capability_name}' denied for mode '{mode}'")
        self.capability_name = capability_name
        self.mode = mode


class CapabilityValidationError(ValueError):
    def __init__(self, capability_name: str, field_name: str) -> None:
        super().__init__(f"Capability '{capability_name}' missing required field '{field_name}'")
        self.capability_name = capability_name
        self.field_name = field_name


class CapabilityInvocationError(RuntimeError):
    def __init__(self, capability_name: str, detail: str) -> None:
        super().__init__(f"Capability '{capability_name}' failed: {detail}")
        self.capability_name = capability_name
        self.detail = detail


@dataclass(slots=True)
class CapabilityDefinition:
    name: str
    kind: CapabilityKind
    input_schema: dict[str, Any]
    result_schema: dict[str, Any]
    allowed_modes: set[str]
    audit_required: bool
    failure_semantics: str
    handler: Callable[[dict[str, Any]], dict[str, Any]]


class CapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities: dict[str, CapabilityDefinition] = {}
        self._audit_log: list[dict[str, Any]] = []

    def register(self, definition: CapabilityDefinition) -> None:
        self._capabilities[definition.name] = definition

    def list_capabilities(self) -> list[dict[str, Any]]:
        return [
            {
                "name": definition.name,
                "kind": definition.kind.value,
                "input_schema": definition.input_schema,
                "result_schema": definition.result_schema,
                "allowed_modes": sorted(definition.allowed_modes),
                "audit_required": definition.audit_required,
                "failure_semantics": definition.failure_semantics,
            }
            for definition in self._capabilities.values()
        ]

    def recent_audit(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return self._audit_log[-limit:]

    def invoke(
        self,
        *,
        name: str,
        mode: str,
        actor: str,
        payload: dict[str, Any],
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        definition = self._capabilities.get(name)
        if not definition:
            raise CapabilityInvocationError(name, "unknown_capability")
        audit_id = trace_id or uuid4().hex
        try:
            if mode not in definition.allowed_modes:
                raise CapabilityAccessDeniedError(name, mode)
            self._validate_payload(definition, payload)
            result = definition.handler(payload)
            self._append_audit(
                capability_name=name,
                mode=mode,
                actor=actor,
                outcome="allowed",
                trace_id=audit_id,
                error=None,
            )
            return result
        except CapabilityAccessDeniedError as exc:
            self._append_audit(
                capability_name=name,
                mode=mode,
                actor=actor,
                outcome="denied",
                trace_id=audit_id,
                error=str(exc),
            )
            raise
        except Exception as exc:
            self._append_audit(
                capability_name=name,
                mode=mode,
                actor=actor,
                outcome="error",
                trace_id=audit_id,
                error=str(exc),
            )
            if isinstance(exc, (CapabilityValidationError, CapabilityInvocationError)):
                raise
            raise CapabilityInvocationError(name, str(exc)) from exc

    def _validate_payload(self, definition: CapabilityDefinition, payload: dict[str, Any]) -> None:
        required = definition.input_schema.get("required", [])
        for field_name in required:
            if field_name not in payload:
                raise CapabilityValidationError(definition.name, field_name)

    def _append_audit(
        self,
        *,
        capability_name: str,
        mode: str,
        actor: str,
        outcome: str,
        trace_id: str,
        error: str | None,
    ) -> None:
        self._audit_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "capability_name": capability_name,
                "mode": mode,
                "actor": actor,
                "outcome": outcome,
                "trace_id": trace_id,
                "error": error,
            }
        )
        if len(self._audit_log) > 2000:
            self._audit_log[:] = self._audit_log[-2000:]


def create_default_capability_registry(
    *,
    retriever: ContextRetriever,
    assembler: ContextPackAssembler,
    repo_root: Path,
) -> CapabilityRegistry:
    registry = CapabilityRegistry()

    def context_pack_handler(payload: dict[str, Any]) -> dict[str, Any]:
        domain = RetrievalDomain(payload.get("domain", RetrievalDomain.RUNTIME.value))
        request = RetrievalRequest(
            domain=domain,
            profile=payload["profile"],
            query=payload["query"],
            module_id=payload.get("module_id"),
            scene_id=payload.get("scene_id"),
            max_chunks=int(payload.get("max_chunks", 4)),
        )
        retrieval_result = retriever.retrieve(request)
        context_pack = assembler.assemble(retrieval_result)
        return {
            "retrieval": {
                "domain": context_pack.domain,
                "profile": context_pack.profile,
                "status": context_pack.status,
                "hit_count": context_pack.hit_count,
                "sources": context_pack.sources,
                "ranking_notes": context_pack.ranking_notes,
            },
            "context_text": context_pack.compact_context,
        }

    def transcript_read_handler(payload: dict[str, Any]) -> dict[str, Any]:
        run_id = payload["run_id"]
        run_file = repo_root / "world-engine" / "app" / "var" / "runs" / f"{run_id}.json"
        if not run_file.exists():
            raise CapabilityInvocationError("wos.transcript.read", "run_not_found")
        return {"run_id": run_id, "content": run_file.read_text(encoding="utf-8", errors="ignore")[:10000]}

    def review_bundle_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "bundle_id": uuid4().hex,
            "module_id": payload["module_id"],
            "summary": payload.get("summary", ""),
            "recommendations": payload.get("recommendations", []),
            "evidence_sources": payload.get("evidence_sources", []),
            "status": "recommendation_only",
        }

    registry.register(
        CapabilityDefinition(
            name="wos.context_pack.build",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "profile": {"type": "string"},
                    "query": {"type": "string"},
                    "module_id": {"type": "string"},
                    "scene_id": {"type": "string"},
                    "max_chunks": {"type": "integer"},
                },
                "required": ["profile", "query"],
            },
            result_schema={
                "type": "object",
                "properties": {"retrieval": {"type": "object"}, "context_text": {"type": "string"}},
                "required": ["retrieval", "context_text"],
            },
            allowed_modes={"runtime", "writers_room", "improvement"},
            audit_required=True,
            failure_semantics="returns capability error and emits audit event",
            handler=context_pack_handler,
        )
    )
    # wos.transcript.read: registered for future improvement loop usage.
    # Not currently invoked in active workflows (aspirational capability).
    # Allowed modes: runtime, improvement, admin.
    registry.register(
        CapabilityDefinition(
            name="wos.transcript.read",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
            },
            result_schema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}, "content": {"type": "string"}},
                "required": ["run_id", "content"],
            },
            allowed_modes={"runtime", "improvement", "admin"},
            audit_required=True,
            failure_semantics="raises run_not_found error with audited trace",
            handler=transcript_read_handler,
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.review_bundle.build",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {
                    "module_id": {"type": "string"},
                    "summary": {"type": "string"},
                    "recommendations": {"type": "array"},
                    "evidence_sources": {"type": "array"},
                },
                "required": ["module_id"],
            },
            result_schema={
                "type": "object",
                "properties": {
                    "bundle_id": {"type": "string"},
                    "module_id": {"type": "string"},
                    "status": {"type": "string"},
                },
                "required": ["bundle_id", "module_id", "status"],
            },
            allowed_modes={"writers_room", "improvement", "admin"},
            audit_required=True,
            failure_semantics="returns recommendation-only bundle metadata",
            handler=review_bundle_handler,
        )
    )
    return registry


def capability_catalog() -> list[dict[str, Any]]:
    return [
        {
            "name": "wos.context_pack.build",
            "kind": CapabilityKind.RETRIEVAL.value,
            "allowed_modes": ["runtime", "writers_room", "improvement"],
        },
        {
            "name": "wos.transcript.read",
            "kind": CapabilityKind.RETRIEVAL.value,
            "allowed_modes": ["runtime", "improvement", "admin"],
        },
        {
            "name": "wos.review_bundle.build",
            "kind": CapabilityKind.ACTION.value,
            "allowed_modes": ["writers_room", "improvement", "admin"],
        },
    ]
