"""Area 2 — explicit routing/registry authority classification (convergence closure).

**Task 2 binding (minimal):** Each canonical execution surface (Runtime, Writers-Room,
Improvement bounded enrichment) has exactly **one primary operational authority** for
Task 2A routing—*who applies routing policy* and *where specs come from* on that path.
Translation, compatibility, and non-authoritative support layers may coexist **only**
when they are **explicit, bounded, and non-competing** with that primary line (no hidden
second routing policy for the same canonical HTTP/in-process path).

``AREA2_AUTHORITY_REGISTRY`` below is the single importable map of those layers.
``AUTHORITY_SOURCE_RUNTIME`` / ``AUTHORITY_SOURCE_WRITERS_ROOM`` /
``AUTHORITY_SOURCE_IMPROVEMENT`` name the spec source strings used in operator truth
for each surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AuthorityLayer(str, Enum):
    """Exactly one layer per registered Area 2 seam."""

    authoritative = "authoritative"
    translation_layer = "translation_layer"
    compatibility_layer = "compatibility_layer"
    non_authoritative_support = "non_authoritative_support"


class CanonicalSurface(str, Enum):
    """Product surfaces that use Task 2A routing in the backend."""

    runtime = "runtime"
    writers_room = "writers_room"
    improvement_bounded = "improvement_bounded"


@dataclass(frozen=True, slots=True)
class Area2AuthorityEntry:
    """One classifiable routing/registry line."""

    component_id: str
    layer: AuthorityLayer
    module_path: str
    description: str
    canonical_for_task2a_paths: frozenset[CanonicalSurface]


# Registry of every Area 2 line referenced by architecture/tests. Each appears once.
AREA2_AUTHORITY_REGISTRY: tuple[Area2AuthorityEntry, ...] = (
    Area2AuthorityEntry(
        component_id="task2a_route_model",
        layer=AuthorityLayer.authoritative,
        module_path="app.runtime.model_routing.route_model",
        description="Deterministic Task 2A routing policy; selects adapter name from specs.",
        canonical_for_task2a_paths=frozenset(CanonicalSurface),
    ),
    Area2AuthorityEntry(
        component_id="task2a_adapter_registry",
        layer=AuthorityLayer.authoritative,
        module_path="app.runtime.adapter_registry",
        description="Global spec store and adapter instances for Runtime when specs=None.",
        canonical_for_task2a_paths=frozenset({CanonicalSurface.runtime}),
    ),
    Area2AuthorityEntry(
        component_id="task2a_contracts",
        layer=AuthorityLayer.authoritative,
        module_path="app.runtime.model_routing_contracts",
        description="Bounded enums, AdapterModelSpec, RoutingRequest, RoutingDecision.",
        canonical_for_task2a_paths=frozenset(CanonicalSurface),
    ),
    Area2AuthorityEntry(
        component_id="writers_room_model_spec_translation",
        layer=AuthorityLayer.translation_layer,
        module_path="app.services.writers_room_model_routing",
        description="Maps story_runtime_core.ModelSpec rows to AdapterModelSpec; same builder for WR and Improvement.",
        canonical_for_task2a_paths=frozenset(
            {CanonicalSurface.writers_room, CanonicalSurface.improvement_bounded}
        ),
    ),
    Area2AuthorityEntry(
        component_id="story_runtime_core_model_registry",
        layer=AuthorityLayer.translation_layer,
        module_path="story_runtime_core.model_registry",
        description="Source ModelSpec rows consumed by writers_room_model_routing (not Task 2A policy).",
        canonical_for_task2a_paths=frozenset(
            {CanonicalSurface.writers_room, CanonicalSurface.improvement_bounded}
        ),
    ),
    Area2AuthorityEntry(
        component_id="routing_registry_bootstrap",
        layer=AuthorityLayer.non_authoritative_support,
        module_path="app.runtime.routing_registry_bootstrap",
        description="Registers in-repo MockStoryAIAdapter + spec when enabled; does not alter route_model.",
        canonical_for_task2a_paths=frozenset({CanonicalSurface.runtime}),
    ),
    Area2AuthorityEntry(
        component_id="model_inventory_contract",
        layer=AuthorityLayer.non_authoritative_support,
        module_path="app.runtime.model_inventory_contract",
        description="Required routing tuples per surface; coverage validation only.",
        canonical_for_task2a_paths=frozenset(CanonicalSurface),
    ),
    Area2AuthorityEntry(
        component_id="model_inventory_report",
        layer=AuthorityLayer.non_authoritative_support,
        module_path="app.runtime.model_inventory_report",
        description="Registry snapshots, validate_surface_coverage, legacy setup classifiers.",
        canonical_for_task2a_paths=frozenset(CanonicalSurface),
    ),
    Area2AuthorityEntry(
        component_id="model_routing_evidence",
        layer=AuthorityLayer.non_authoritative_support,
        module_path="app.runtime.model_routing_evidence",
        description="Normalized routing_evidence attachment; derived from routing decisions.",
        canonical_for_task2a_paths=frozenset(CanonicalSurface),
    ),
    Area2AuthorityEntry(
        component_id="operator_audit",
        layer=AuthorityLayer.non_authoritative_support,
        module_path="app.runtime.operator_audit",
        description="Deterministic operator views from existing traces; no new policy.",
        canonical_for_task2a_paths=frozenset(CanonicalSurface),
    ),
    Area2AuthorityEntry(
        component_id="area2_operator_truth",
        layer=AuthorityLayer.non_authoritative_support,
        module_path="app.runtime.area2_operator_truth",
        description="Derived operator legibility and cross-surface truth from existing traces; no new telemetry.",
        canonical_for_task2a_paths=frozenset(CanonicalSurface),
    ),
    Area2AuthorityEntry(
        component_id="area2_startup_profiles",
        layer=AuthorityLayer.non_authoritative_support,
        module_path="app.runtime.area2_startup_profiles",
        description="Named startup profiles and expected bootstrap/registry facts for docs and gates.",
        canonical_for_task2a_paths=frozenset(CanonicalSurface),
    ),
    Area2AuthorityEntry(
        component_id="runtime_ai_stages",
        layer=AuthorityLayer.non_authoritative_support,
        module_path="app.runtime.runtime_ai_stages",
        description="Composes multiple route_model calls for staged Runtime; does not replace route_model.",
        canonical_for_task2a_paths=frozenset({CanonicalSurface.runtime}),
    ),
    Area2AuthorityEntry(
        component_id="ai_turn_executor",
        layer=AuthorityLayer.non_authoritative_support,
        module_path="app.runtime.ai_turn_executor",
        description="Orchestrates execute_turn_with_ai; delegates routing to route_model / staged stages.",
        canonical_for_task2a_paths=frozenset({CanonicalSurface.runtime}),
    ),
    Area2AuthorityEntry(
        component_id="improvement_task2a_routing",
        layer=AuthorityLayer.non_authoritative_support,
        module_path="app.services.improvement_task2a_routing",
        description="Bounded enrichment calls route_model with explicit WR-derived specs.",
        canonical_for_task2a_paths=frozenset({CanonicalSurface.improvement_bounded}),
    ),
    Area2AuthorityEntry(
        component_id="writers_room_service",
        layer=AuthorityLayer.non_authoritative_support,
        module_path="app.services.writers_room_service",
        description="Writers-Room workflow; uses route_model with explicit specs from translation layer.",
        canonical_for_task2a_paths=frozenset({CanonicalSurface.writers_room}),
    ),
    Area2AuthorityEntry(
        component_id="langgraph_runtime_routing_policy",
        layer=AuthorityLayer.compatibility_layer,
        module_path="ai_stack.langgraph_runtime",
        description="Uses story_runtime_core.RoutingPolicy.choose(); not Task 2A route_model — parallel graph stack only.",
        canonical_for_task2a_paths=frozenset(),
    ),
    Area2AuthorityEntry(
        component_id="story_runtime_core_routing_policy_legacy",
        layer=AuthorityLayer.compatibility_layer,
        module_path="story_runtime_core.model_registry.RoutingPolicy",
        description="Legacy choose() API used by ai_stack LangGraph; Writers-Room canonical HTTP path uses route_model instead.",
        canonical_for_task2a_paths=frozenset(),
    ),
)


def authority_entries_for_surface(surface: CanonicalSurface) -> tuple[Area2AuthorityEntry, ...]:
    """Return entries that participate in the given canonical Task 2A surface."""
    return tuple(e for e in AREA2_AUTHORITY_REGISTRY if surface in e.canonical_for_task2a_paths)


def assert_routing_policy_entry_is_unique_authoritative_policy() -> None:
    """G-CONV-01: ``route_model`` is the only authoritative routing *policy* entry."""
    policies = [e for e in AREA2_AUTHORITY_REGISTRY if e.component_id == "task2a_route_model"]
    assert len(policies) == 1
    assert policies[0].layer == AuthorityLayer.authoritative


def assert_langgraph_not_canonical_for_task2a() -> None:
    """G-CONV-01: LangGraph routing must not claim canonical Task 2A surfaces."""
    lg = next(e for e in AREA2_AUTHORITY_REGISTRY if e.component_id == "langgraph_runtime_routing_policy")
    assert lg.canonical_for_task2a_paths == frozenset(), (
        "ai_stack LangGraph RoutingPolicy must not be listed as canonical for Task 2A HTTP paths"
    )


AUTHORITY_SOURCE_RUNTIME = "adapter_registry.iter_model_specs"
AUTHORITY_SOURCE_WRITERS_ROOM = "build_writers_room_model_route_specs"
AUTHORITY_SOURCE_IMPROVEMENT = "build_writers_room_model_route_specs"
