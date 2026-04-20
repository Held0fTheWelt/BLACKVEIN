"""MCP M1 — single canonical descriptor strand for the external MCP tool surface.

Registry entries in ``tools.mcp_server`` are derived from ``CANONICAL_MCP_TOOL_DESCRIPTORS``.
Capability-facing truth is mirrored only through ``wos.capabilities.catalog`` via
:func:`capability_records_for_mcp` (built on :func:`ai_stack.capabilities.capability_catalog`).

Strict translation (no parallel MCP-only capability names):
- Internal capabilities are listed by name only inside enriched catalog records.
- MCP does not expose :class:`ai_stack.capabilities.CapabilityRegistry` ``invoke``; no shortcut
  around runtime guard/commit/reject or review/publish authority.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Final

from ai_stack.capabilities import CapabilityKind, capability_catalog

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum as _Enum

    class StrEnum(str, _Enum):
        def __str__(self) -> str:
            return str(self.value)


class McpToolClass(StrEnum):
    read_only = "read_only"
    review_bound = "review_bound"
    write_capable = "write_capable"


class McpOperatingProfile(StrEnum):
    healthy = "healthy"
    review_safe = "review_safe"
    test_isolated = "test_isolated"
    degraded = "degraded"


class McpImplementationStatus(StrEnum):
    implemented = "implemented"
    deferred_stub = "deferred_stub"


MCP_OPERATOR_TRUTH_GRAMMAR_VERSION: Final[str] = "mcp_operator_truth_v1"

MCP_CATALOG_CAPABILITY_NAMES: Final[tuple[str, ...]] = tuple(
    sorted(row["name"] for row in capability_catalog())
)


def resolve_mcp_operating_profile() -> McpOperatingProfile:
    raw = (os.environ.get("WOS_MCP_OPERATING_PROFILE") or "healthy").strip().lower()
    try:
        return McpOperatingProfile(raw)
    except ValueError:
        return McpOperatingProfile.degraded


def operating_profile_allows_write_capable(profile: McpOperatingProfile) -> bool:
    return profile is McpOperatingProfile.healthy


@dataclass(frozen=True, slots=True)
class McpToolGovernanceView:
    published_vs_draft: str
    canonical_vs_supporting: str
    runtime_safe_vs_internal_only: str
    writers_room_visible_vs_runtime_hidden: str
    reviewable_vs_publishable_posture: str


@dataclass(frozen=True, slots=True)
class McpCanonicalToolDescriptor:
    name: str
    authority_source: str
    tool_class: McpToolClass
    implementation_status: McpImplementationStatus
    governance: McpToolGovernanceView
    narrative_mutation_risk: str
    permission_legacy: str


AUTH_BACKEND_HTTP = "backend_http_authority"
AUTH_FILESYSTEM_REPO = "repository_filesystem_read"
AUTH_AI_STACK_CAPABILITY_CATALOG = "ai_stack_capability_registry_mirror"
AUTH_MCP_SURFACE_META = "mcp_surface_operator_meta"


CANONICAL_MCP_TOOL_DESCRIPTORS: tuple[McpCanonicalToolDescriptor, ...] = (
    McpCanonicalToolDescriptor(
        name="wos.system.health",
        authority_source=AUTH_BACKEND_HTTP,
        tool_class=McpToolClass.read_only,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="not_applicable",
            canonical_vs_supporting="not_applicable",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="not_applicable",
            reviewable_vs_publishable_posture="not_applicable",
        ),
        narrative_mutation_risk="none",
        permission_legacy="read",
    ),
    McpCanonicalToolDescriptor(
        name="wos.session.create",
        authority_source=AUTH_BACKEND_HTTP,
        tool_class=McpToolClass.write_capable,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="not_applicable",
            canonical_vs_supporting="session_shell_not_manuscript",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="not_applicable",
            reviewable_vs_publishable_posture="backend_session_create_not_publish",
        ),
        narrative_mutation_risk="none_direct_manuscript",
        permission_legacy="write",
    ),
    McpCanonicalToolDescriptor(
        name="wos.goc.list_modules",
        authority_source=AUTH_FILESYSTEM_REPO,
        tool_class=McpToolClass.read_only,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="draft_workspace_files",
            canonical_vs_supporting="supporting_content_files",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="writers_room_visible",
            reviewable_vs_publishable_posture="read_only_not_publish_path",
        ),
        narrative_mutation_risk="none",
        permission_legacy="read",
    ),
    McpCanonicalToolDescriptor(
        name="wos.goc.get_module",
        authority_source=AUTH_FILESYSTEM_REPO,
        tool_class=McpToolClass.read_only,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="draft_workspace_files",
            canonical_vs_supporting="supporting_content_files",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="writers_room_visible",
            reviewable_vs_publishable_posture="read_only_not_publish_path",
        ),
        narrative_mutation_risk="none",
        permission_legacy="read",
    ),
    McpCanonicalToolDescriptor(
        name="wos.content.search",
        authority_source=AUTH_FILESYSTEM_REPO,
        tool_class=McpToolClass.read_only,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="draft_workspace_files",
            canonical_vs_supporting="supporting_content_files",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="writers_room_visible",
            reviewable_vs_publishable_posture="read_only_not_publish_path",
        ),
        narrative_mutation_risk="none",
        permission_legacy="read",
    ),
    McpCanonicalToolDescriptor(
        name="wos.capabilities.catalog",
        authority_source=AUTH_AI_STACK_CAPABILITY_CATALOG,
        tool_class=McpToolClass.read_only,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="metadata_only",
            canonical_vs_supporting="canonical_registry_descriptor_read",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="descriptor_read_not_publish",
        ),
        narrative_mutation_risk="none",
        permission_legacy="read",
    ),
    McpCanonicalToolDescriptor(
        name="wos.mcp.operator_truth",
        authority_source=AUTH_MCP_SURFACE_META,
        tool_class=McpToolClass.read_only,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="not_applicable",
            canonical_vs_supporting="operator_legibility_support",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="read_only_not_publish_path",
        ),
        narrative_mutation_risk="none",
        permission_legacy="read",
    ),
    McpCanonicalToolDescriptor(
        name="wos.session.get",
        authority_source=AUTH_BACKEND_HTTP,
        tool_class=McpToolClass.read_only,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="not_applicable",
            canonical_vs_supporting="session_observability_canonical",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="read_only_observation_surface",
        ),
        narrative_mutation_risk="none_observation_only",
        permission_legacy="read",
    ),
    McpCanonicalToolDescriptor(
        name="wos.session.execute_turn",
        authority_source=AUTH_BACKEND_HTTP,
        tool_class=McpToolClass.review_bound,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="not_applicable",
            canonical_vs_supporting="runtime_turn_authority_required",
            runtime_safe_vs_internal_only="internal_only_via_runtime_executor",
            writers_room_visible_vs_runtime_hidden="runtime_hidden_from_mcp_shortcut",
            reviewable_vs_publishable_posture="must_use_guarded_runtime_path",
        ),
        narrative_mutation_risk="blocked_from_mcp",
        permission_legacy="preview",
    ),
    McpCanonicalToolDescriptor(
        name="wos.session.logs",
        authority_source=AUTH_BACKEND_HTTP,
        tool_class=McpToolClass.review_bound,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="not_applicable",
            canonical_vs_supporting="supporting_observability",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="preview_bound",
        ),
        narrative_mutation_risk="none_observation_only",
        permission_legacy="preview",
    ),
    McpCanonicalToolDescriptor(
        name="wos.session.state",
        authority_source=AUTH_BACKEND_HTTP,
        tool_class=McpToolClass.review_bound,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="not_applicable",
            canonical_vs_supporting="canonical_runtime_state_preview",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="preview_bound_no_write_via_mcp",
        ),
        narrative_mutation_risk="none_stub",
        permission_legacy="preview",
    ),
    McpCanonicalToolDescriptor(
        name="wos.session.diag",
        authority_source=AUTH_BACKEND_HTTP,
        tool_class=McpToolClass.read_only,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="not_applicable",
            canonical_vs_supporting="supporting_observability_canonical",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="read_only_observation_surface",
        ),
        narrative_mutation_risk="none_observation_only",
        permission_legacy="read",
    ),
    McpCanonicalToolDescriptor(
        name="wos.research.source.inspect",
        authority_source=AUTH_AI_STACK_CAPABILITY_CATALOG,
        tool_class=McpToolClass.read_only,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="internal_research_store",
            canonical_vs_supporting="research_provenance_read",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="read_only_not_publish_path",
        ),
        narrative_mutation_risk="none_observation_only",
        permission_legacy="read",
    ),
    McpCanonicalToolDescriptor(
        name="wos.research.aspect.extract",
        authority_source=AUTH_AI_STACK_CAPABILITY_CATALOG,
        tool_class=McpToolClass.read_only,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="internal_research_store",
            canonical_vs_supporting="research_aspect_projection",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="read_only_not_publish_path",
        ),
        narrative_mutation_risk="none_observation_only",
        permission_legacy="read",
    ),
    McpCanonicalToolDescriptor(
        name="wos.research.claim.list",
        authority_source=AUTH_AI_STACK_CAPABILITY_CATALOG,
        tool_class=McpToolClass.read_only,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="internal_research_store",
            canonical_vs_supporting="research_claim_observability",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="read_only_not_publish_path",
        ),
        narrative_mutation_risk="none_observation_only",
        permission_legacy="read",
    ),
    McpCanonicalToolDescriptor(
        name="wos.research.run.get",
        authority_source=AUTH_AI_STACK_CAPABILITY_CATALOG,
        tool_class=McpToolClass.read_only,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="internal_research_store",
            canonical_vs_supporting="research_run_observability",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="read_only_not_publish_path",
        ),
        narrative_mutation_risk="none_observation_only",
        permission_legacy="read",
    ),
    McpCanonicalToolDescriptor(
        name="wos.research.exploration.graph",
        authority_source=AUTH_AI_STACK_CAPABILITY_CATALOG,
        tool_class=McpToolClass.read_only,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="internal_research_store",
            canonical_vs_supporting="research_graph_observability",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="read_only_not_publish_path",
        ),
        narrative_mutation_risk="none_observation_only",
        permission_legacy="read",
    ),
    McpCanonicalToolDescriptor(
        name="wos.canon.issue.inspect",
        authority_source=AUTH_AI_STACK_CAPABILITY_CATALOG,
        tool_class=McpToolClass.read_only,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="internal_research_store",
            canonical_vs_supporting="canon_issue_observability",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="read_only_not_publish_path",
        ),
        narrative_mutation_risk="none_observation_only",
        permission_legacy="read",
    ),
    McpCanonicalToolDescriptor(
        name="wos.research.explore",
        authority_source=AUTH_AI_STACK_CAPABILITY_CATALOG,
        tool_class=McpToolClass.review_bound,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="internal_research_store",
            canonical_vs_supporting="research_generation_non_canon",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="review_bound_no_canon_mutation",
        ),
        narrative_mutation_risk="review_bound_generation_only",
        permission_legacy="preview",
    ),
    McpCanonicalToolDescriptor(
        name="wos.research.validate",
        authority_source=AUTH_AI_STACK_CAPABILITY_CATALOG,
        tool_class=McpToolClass.review_bound,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="internal_research_store",
            canonical_vs_supporting="research_validation_non_publish",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="review_bound_no_canon_mutation",
        ),
        narrative_mutation_risk="review_bound_non_publish",
        permission_legacy="preview",
    ),
    McpCanonicalToolDescriptor(
        name="wos.research.bundle.build",
        authority_source=AUTH_AI_STACK_CAPABILITY_CATALOG,
        tool_class=McpToolClass.review_bound,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="internal_research_store",
            canonical_vs_supporting="review_bundle_generation",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="recommendation_only_not_publish",
        ),
        narrative_mutation_risk="none_bundle_only",
        permission_legacy="preview",
    ),
    McpCanonicalToolDescriptor(
        name="wos.canon.improvement.propose",
        authority_source=AUTH_AI_STACK_CAPABILITY_CATALOG,
        tool_class=McpToolClass.review_bound,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="internal_research_store",
            canonical_vs_supporting="proposal_generation_non_publish",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="review_bound_no_canon_mutation",
        ),
        narrative_mutation_risk="review_bound_non_publish",
        permission_legacy="preview",
    ),
    McpCanonicalToolDescriptor(
        name="wos.canon.improvement.preview",
        authority_source=AUTH_AI_STACK_CAPABILITY_CATALOG,
        tool_class=McpToolClass.review_bound,
        implementation_status=McpImplementationStatus.implemented,
        governance=McpToolGovernanceView(
            published_vs_draft="internal_research_store",
            canonical_vs_supporting="proposal_preview_non_publish",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_visible",
            reviewable_vs_publishable_posture="review_bound_no_canon_mutation",
        ),
        narrative_mutation_risk="none_preview_only",
        permission_legacy="preview",
    ),
)


def canonical_mcp_tool_descriptors_by_name() -> dict[str, McpCanonicalToolDescriptor]:
    return {d.name: d for d in CANONICAL_MCP_TOOL_DESCRIPTORS}


def _tool_class_for_capability_row(name: str, kind: str) -> McpToolClass:
    """Derive tool class strictly from capability kind and name (not static mapping)."""
    if kind == CapabilityKind.RETRIEVAL.value:
        return McpToolClass.read_only
    if name == "wos.review_bundle.build":
        return McpToolClass.review_bound
    return McpToolClass.review_bound


def _writers_room_visibility_token(modes: list[str]) -> str:
    """Derive writers room visibility from allowed modes (not static)."""
    wr_visible = "writers_room" in modes
    runtime_in = "runtime" in modes
    if wr_visible and not runtime_in:
        return "writers_room_visible_runtime_may_skip"
    if wr_visible:
        return "writers_room_visible"
    if "runtime" in modes or "improvement" in modes:
        return "runtime_focused"
    return "mode_gated"


def _derive_reviewable_posture(tool_class: McpToolClass, name: str) -> str:
    """Derive reviewable posture from tool class and function (derived, not static)."""
    if tool_class is McpToolClass.read_only:
        return "read_only_no_review_path"
    if "build" in name or "create" in name or "execute" in name:
        return "review_required_for_mutation"
    return "read_and_review_paths"


def _derive_governance_risk_token(name: str, kind: str) -> str:
    """Derive narrative mutation risk from tool name and kind (derived, not static)."""
    if kind == CapabilityKind.RETRIEVAL.value:
        return "none_read_only"
    if "execute" in name or "commit" in name or "publish" in name:
        return "high_direct_authority_mutation"
    if "build" in name or "create" in name:
        return "medium_stage_mutation"
    if "diag" in name or "logs" in name or "state" in name:
        return "none_observation_only"
    return "medium_standard"


def _derive_runtime_safe_vs_internal(name: str, tool_class: McpToolClass) -> str:
    """Derive runtime safety from tool name and class (not static parallel field)."""
    # Session tools (get, diag, logs, state) are runtime-safe observations
    if name.startswith("wos.session.") and tool_class is McpToolClass.read_only:
        return "runtime_safe"
    # execute_turn is internal-only via runtime executor (hidden from shortcut)
    if name == "wos.session.execute_turn":
        return "internal_only_via_runtime_executor"
    # Content/GOC tools are runtime-safe (read-only)
    if name.startswith("wos.goc.") or name.startswith("wos.content."):
        return "runtime_safe"
    # System health is runtime-safe
    if name == "wos.system.health":
        return "runtime_safe"
    # Session.create is runtime-safe (session shell)
    if name == "wos.session.create":
        return "runtime_safe"
    return "runtime_safe"


def _derive_canonical_vs_supporting(name: str, tool_class: McpToolClass) -> str:
    """Derive canonical vs supporting from tool domain and class (derived from semantics)."""
    if "session" in name and tool_class is McpToolClass.read_only:
        return "session_observability_canonical"
    if name == "wos.session.execute_turn":
        return "runtime_turn_authority_required"
    if name == "wos.session.create":
        return "session_shell_not_manuscript"
    if "goc" in name or "content" in name:
        return "supporting_content_files"
    return "supporting"


def _derive_permission_legacy(tool_class: McpToolClass, name: str) -> str:
    """Derive legacy permission from tool class and semantics (not static)."""
    if tool_class is McpToolClass.read_only:
        return "read"
    if tool_class is McpToolClass.review_bound:
        return "preview"
    return "write"


def capability_records_for_mcp() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in capability_catalog():
        name = row["name"]
        kind = row["kind"]
        tc = _tool_class_for_capability_row(name, kind)
        modes = list(row.get("allowed_modes") or [])
        canon_sup = (
            "retrieval_support" if kind == CapabilityKind.RETRIEVAL.value else "recommendation_preview_only"
        )
        rti = (
            "runtime_safe"
            if ("runtime" in modes or "improvement" in modes)
            else "mode_gated_internal_surfaces_possible"
        )
        out.append(
            {
                **row,
                "authority_source": AUTH_AI_STACK_CAPABILITY_CATALOG,
                "tool_class": tc.value,
                "governance_posture": {
                    "published_vs_draft": "governed_by_mode_and_registry_not_mcp_publish",
                    "canonical_vs_supporting": canon_sup,
                    "runtime_safe_vs_internal_only": rti,
                    "writers_room_visible_vs_runtime_hidden": _writers_room_visibility_token(modes),
                    "reviewable_vs_publishable_posture": (
                        "read_and_review_paths" if tc is McpToolClass.review_bound else "read_only_retrieval"
                    ),
                },
            }
        )
    return out


def verify_catalog_names_alignment() -> dict[str, Any]:
    names = tuple(sorted(row["name"] for row in capability_records_for_mcp()))
    return {
        "aligned": names == MCP_CATALOG_CAPABILITY_NAMES,
        "expected": list(MCP_CATALOG_CAPABILITY_NAMES),
        "actual": list(names),
    }


def classify_mcp_no_eligible_discipline(
    *,
    catalog_alignment_ok: bool,
    implemented_tool_count: int,
    deferred_stub_count: int,
    profile: McpOperatingProfile,
) -> dict[str, Any]:
    if not catalog_alignment_ok:
        return {
            "applicable": True,
            "operator_meaning_token": "misconfigured_capability_catalog_mismatch",
            "discipline_worst_case": "misconfigured",
            "stages_reporting_no_eligible_adapter": [],
        }
    if profile is McpOperatingProfile.degraded:
        return {
            "applicable": True,
            "operator_meaning_token": "degraded_profile_operator_declared",
            "discipline_worst_case": "degraded_but_controlled",
            "stages_reporting_no_eligible_adapter": [],
        }
    if profile is McpOperatingProfile.test_isolated:
        return {
            "applicable": True,
            "operator_meaning_token": "test_isolated_expected_posture_not_true_no_eligible",
            "discipline_worst_case": "test_isolated_empty_or_suppressed",
            "stages_reporting_no_eligible_adapter": [],
        }
    if implemented_tool_count == 0 and deferred_stub_count == 0:
        return {
            "applicable": True,
            "operator_meaning_token": "true_no_eligible_mcp_surface",
            "discipline_worst_case": "true_no_eligible_adapter",
            "stages_reporting_no_eligible_adapter": ["mcp_tool_surface"],
        }
    return {
        "applicable": False,
        "operator_meaning_token": "healthy_mcp_surface_with_implemented_tools",
        "discipline_worst_case": "not_applicable",
        "stages_reporting_no_eligible_adapter": [],
    }


def _route_status_token(
    *,
    profile: McpOperatingProfile,
    backend_reachable: bool | None,
    catalog_alignment_ok: bool,
) -> str:
    if not catalog_alignment_ok:
        return "misconfigured_catalog_translation"
    if profile is McpOperatingProfile.test_isolated:
        return "test_isolated_mcp_posture"
    if profile is McpOperatingProfile.degraded:
        return "degraded_operator_declared"
    if profile is McpOperatingProfile.review_safe:
        return "review_safe_writes_suppressed"
    if backend_reachable is False:
        return "backend_unreachable_degraded_operations"
    return "canonical_mcp_tools_registered"


def _operational_state_token(
    *,
    profile: McpOperatingProfile,
    backend_reachable: bool | None,
    catalog_alignment_ok: bool,
) -> str:
    if not catalog_alignment_ok:
        return "misconfigured"
    if profile is McpOperatingProfile.degraded:
        return "degraded"
    if profile is McpOperatingProfile.test_isolated:
        return "test_isolated"
    if backend_reachable is False:
        return "degraded"
    return "healthy"


def build_compact_mcp_operator_truth(
    *,
    backend_reachable: bool | None,
    catalog_alignment_ok: bool,
    registry_tool_names: list[str],
) -> dict[str, Any]:
    profile = resolve_mcp_operating_profile()
    desc_by = canonical_mcp_tool_descriptors_by_name()
    implemented = sum(
        1
        for n in registry_tool_names
        if (d := desc_by.get(n)) and d.implementation_status is McpImplementationStatus.implemented
    )
    stubs = sum(
        1
        for n in registry_tool_names
        if (d := desc_by.get(n)) and d.implementation_status is McpImplementationStatus.deferred_stub
    )
    nea = classify_mcp_no_eligible_discipline(
        catalog_alignment_ok=catalog_alignment_ok,
        implemented_tool_count=implemented,
        deferred_stub_count=stubs,
        profile=profile,
    )
    op_state = _operational_state_token(
        profile=profile, backend_reachable=backend_reachable, catalog_alignment_ok=catalog_alignment_ok
    )
    route_status = _route_status_token(
        profile=profile, backend_reachable=backend_reachable, catalog_alignment_ok=catalog_alignment_ok
    )

    classes: dict[str, int] = {"read_only": 0, "review_bound": 0, "write_capable": 0}
    for n in registry_tool_names:
        d = desc_by.get(n)
        if d:
            k = d.tool_class.value
            classes[k] = classes.get(k, 0) + 1

    return {
        "grammar_version": MCP_OPERATOR_TRUTH_GRAMMAR_VERSION,
        "authority_source": "mcp_canonical_surface_aggregate",
        "startup_profile": profile.value,
        "operational_state": op_state,
        "route_status": route_status,
        "available_vs_deferred": {
            "available": implemented,
            "deferred": stubs,
            "tool_classes": classes,
        },
        "governance_posture": {
            "write_capable_allowed": operating_profile_allows_write_capable(profile),
            "review_bound_allowed": True,
            "read_only_allowed": True,
        },
        "readiness_posture": (
            "catalog_aligned" if catalog_alignment_ok else "catalog_misaligned_requires_fix"
        ),
        "no_eligible_operator_meaning": nea,
        "runtime_authority_preservation": "no_mcp_invoke_shortcut_to_capability_registry",
        "execution_model": "mcp_executes_named_tool_only_no_hidden_runtime_shortcut",
        "primary_operational_concern": (
            "catalog_mismatch"
            if not catalog_alignment_ok
            else ("backend_unreachable" if backend_reachable is False else "none")
        ),
    }


def governance_dict(view: McpToolGovernanceView) -> dict[str, str]:
    return {
        "published_vs_draft": view.published_vs_draft,
        "canonical_vs_supporting": view.canonical_vs_supporting,
        "runtime_safe_vs_internal_only": view.runtime_safe_vs_internal_only,
        "writers_room_visible_vs_runtime_hidden": view.writers_room_visible_vs_runtime_hidden,
        "reviewable_vs_publishable_posture": view.reviewable_vs_publishable_posture,
    }


def descriptor_to_public_metadata(d: McpCanonicalToolDescriptor) -> dict[str, Any]:
    return {
        "authority_source": d.authority_source,
        "tool_class": d.tool_class.value,
        "implementation_status": d.implementation_status.value,
        "governance": governance_dict(d.governance),
        "narrative_mutation_risk": d.narrative_mutation_risk,
    }
