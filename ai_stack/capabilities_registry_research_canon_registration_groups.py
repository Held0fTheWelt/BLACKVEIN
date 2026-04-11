"""Gruppierte Capability-Registrierungen Research/Canon (Feinsplit von capabilities_registry_research_canon_impl)."""

from __future__ import annotations

from functools import partial
from typing import Any

from ai_stack.capabilities import CapabilityDefinition, CapabilityKind, CapabilityRegistry
from ai_stack.capabilities_registry_research_canon_handlers import (
    canon_improvement_preview_handler,
    canon_improvement_propose_handler,
    canon_issue_inspect_handler,
    research_aspect_extract_handler,
    research_bundle_build_handler,
    research_claim_list_handler,
    research_exploration_graph_handler,
    research_explore_handler,
    research_run_get_handler,
    research_source_inspect_handler,
    research_validate_handler,
)


def register_research_source_and_aspect_capabilities(registry: CapabilityRegistry, research_store: Any) -> None:
    registry.register(
        CapabilityDefinition(
            name="wos.research.source.inspect",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {"source_id": {"type": "string"}},
                "required": ["source_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns source_not_found when unknown",
            handler=partial(research_source_inspect_handler, research_store),
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.research.aspect.extract",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {"source_id": {"type": "string"}},
                "required": ["source_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns stored deterministic aspect rows",
            handler=partial(research_aspect_extract_handler, research_store),
        )
    )


def register_research_claim_run_graph_capabilities(registry: CapabilityRegistry, research_store: Any) -> None:
    registry.register(
        CapabilityDefinition(
            name="wos.research.claim.list",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {"work_id": {"type": "string"}},
                "required": [],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns deterministic claim listing",
            handler=partial(research_claim_list_handler, research_store),
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.research.run.get",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns run_not_found when unknown",
            handler=partial(research_run_get_handler, research_store),
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.research.exploration.graph",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns bounded run graph",
            handler=partial(research_exploration_graph_handler, research_store),
        )
    )


def register_canon_inspect_and_research_actions(registry: CapabilityRegistry, research_store: Any) -> None:
    registry.register(
        CapabilityDefinition(
            name="wos.canon.issue.inspect",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {"module_id": {"type": "string"}},
                "required": [],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns deterministic issue listing",
            handler=partial(canon_issue_inspect_handler, research_store),
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.research.explore",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {
                    "work_id": {"type": "string"},
                    "module_id": {"type": "string"},
                    "seed_question": {"type": "string"},
                    "source_inputs": {"type": "array"},
                    "budget": {"type": "object"},
                },
                "required": ["work_id", "module_id", "source_inputs", "budget"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="fails if budget object is missing or invalid",
            handler=partial(research_explore_handler, research_store),
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.research.validate",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="validates run outputs in deterministic flow",
            handler=partial(research_validate_handler, research_store),
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.research.bundle.build",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns review-safe bundle only",
            handler=partial(research_bundle_build_handler, research_store),
        )
    )


def register_canon_improvement_actions(registry: CapabilityRegistry, research_store: Any) -> None:
    registry.register(
        CapabilityDefinition(
            name="wos.canon.improvement.propose",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {"module_id": {"type": "string"}},
                "required": ["module_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns taxonomy-constrained issues and proposals",
            handler=partial(canon_improvement_propose_handler, research_store),
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.canon.improvement.preview",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {"module_id": {"type": "string"}},
                "required": ["module_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns preview payloads, no mutation",
            handler=partial(canon_improvement_preview_handler, research_store),
        )
    )
