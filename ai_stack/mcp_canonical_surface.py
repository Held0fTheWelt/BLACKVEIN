"""Canonical MCP surface and governance helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        def __str__(self) -> str:
            return self.value


AUTH_BACKEND_HTTP = "backend_http_authority"
AUTH_FILESYSTEM_REPO = "filesystem_repo_authority"
AUTH_AI_STACK_CAPABILITY_CATALOG = "ai_stack_capability_catalog"
AUTH_MCP_SURFACE_META = "mcp_surface_meta"
MCP_OPERATOR_TRUTH_GRAMMAR_VERSION = "mcp_operator_truth_v1"


class McpToolClass(StrEnum):
    read_only = "read_only"
    review_bound = "review_bound"
    write_capable = "write_capable"


class McpImplementationStatus(StrEnum):
    implemented = "implemented"
    deferred_stub = "deferred_stub"


class McpOperatingProfile(StrEnum):
    healthy = "healthy"
    degraded = "degraded"
    test_isolated = "test_isolated"
    review_safe = "review_safe"


class McpSuite(StrEnum):
    wos_admin = "wos-admin"
    wos_runtime_read = "wos-runtime-read"
    wos_runtime_control = "wos-runtime-control"
    wos_author = "wos-author"
    wos_ai = "wos-ai"


MCP_SUITES_ALL: tuple[McpSuite, ...] = tuple(McpSuite)


@dataclass(frozen=True)
class McpToolGovernanceView:
    published_vs_draft: str
    canonical_vs_supporting: str
    runtime_safe_vs_internal_only: str
    writers_room_visible_vs_runtime_hidden: str
    reviewable_vs_publishable_posture: str


@dataclass(frozen=True)
class McpCanonicalToolDescriptor:
    name: str
    tool_class: McpToolClass
    authority_source: str
    implementation_status: McpImplementationStatus
    permission_legacy: str
    narrative_mutation_risk: str
    governance: McpToolGovernanceView
    mcp_suite: McpSuite


def _writers_room_visibility_token(modes: list[str]) -> str:
    m = set(modes)
    if m == {"writers_room"}:
        return "writers_room_visible_runtime_may_skip"
    if "writers_room" in m:
        return "writers_room_visible"
    if "runtime" in m or "improvement" in m:
        return "runtime_focused"
    return "mode_gated"


def _derive_reviewable_posture(tool_class: McpToolClass, name: str) -> str:
    if tool_class is McpToolClass.read_only:
        return "read_only_no_review_path"
    if any(t in name for t in (".build", ".create", ".execute")):
        return "review_required_for_mutation"
    return "read_and_review_paths"


def _derive_governance_risk_token(name: str, capability_kind: str) -> str:
    low_names = ("diag", "logs", "state")
    if capability_kind == "retrieval":
        return "none_read_only"
    if any(x in name for x in (".execute", ".commit", ".publish")):
        return "high_direct_authority_mutation"
    if any(x in name for x in (".build", ".create")):
        return "medium_stage_mutation"
    if any(x in name for x in low_names):
        return "none_observation_only"
    return "medium_standard"


def _derive_runtime_safe_vs_internal(name: str, tool_class: McpToolClass) -> str:
    if name == "wos.session.execute_turn":
        return "internal_only_via_runtime_executor"
    return "runtime_safe"


def _derive_canonical_vs_supporting(name: str, tool_class: McpToolClass) -> str:
    if name in {"wos.session.get", "wos.session.logs", "wos.session.state", "wos.session.diag"}:
        return "session_observability_canonical"
    if name == "wos.session.execute_turn":
        return "runtime_turn_authority_required"
    if name == "wos.session.create":
        return "session_shell_not_manuscript"
    if name.startswith("wos.goc.") or name.startswith("wos.content."):
        return "supporting_content_files"
    return "supporting"


def _derive_permission_legacy(tool_class: McpToolClass, name: str) -> str:
    if tool_class is McpToolClass.read_only:
        return "read"
    if tool_class is McpToolClass.review_bound:
        return "preview"
    return "write"


def _tool_class_for_capability_row(name: str, capability_kind: str) -> McpToolClass:
    if capability_kind == "retrieval":
        return McpToolClass.read_only
    if name == "wos.review_bundle.build":
        return McpToolClass.review_bound
    return McpToolClass.review_bound


def governance_dict(view: McpToolGovernanceView) -> dict[str, str]:
    return {
        "published_vs_draft": view.published_vs_draft,
        "canonical_vs_supporting": view.canonical_vs_supporting,
        "runtime_safe_vs_internal_only": view.runtime_safe_vs_internal_only,
        "writers_room_visible_vs_runtime_hidden": view.writers_room_visible_vs_runtime_hidden,
        "reviewable_vs_publishable_posture": view.reviewable_vs_publishable_posture,
    }


_TOOL_SPECS: tuple[tuple[str, McpToolClass, McpSuite, str], ...] = (
    ("wos.system.health", McpToolClass.read_only, McpSuite.wos_admin, AUTH_BACKEND_HTTP),
    ("wos.capabilities.catalog", McpToolClass.read_only, McpSuite.wos_admin, AUTH_AI_STACK_CAPABILITY_CATALOG),
    ("wos.mcp.operator_truth", McpToolClass.read_only, McpSuite.wos_admin, AUTH_MCP_SURFACE_META),
    ("wos.session.create", McpToolClass.write_capable, McpSuite.wos_runtime_control, AUTH_BACKEND_HTTP),
    ("wos.session.get", McpToolClass.read_only, McpSuite.wos_runtime_read, AUTH_BACKEND_HTTP),
    ("wos.session.logs", McpToolClass.read_only, McpSuite.wos_runtime_read, AUTH_BACKEND_HTTP),
    ("wos.session.state", McpToolClass.read_only, McpSuite.wos_runtime_read, AUTH_BACKEND_HTTP),
    ("wos.session.diag", McpToolClass.read_only, McpSuite.wos_runtime_read, AUTH_BACKEND_HTTP),
    ("wos.session.execute_turn", McpToolClass.review_bound, McpSuite.wos_runtime_control, AUTH_BACKEND_HTTP),
    ("wos.goc.list_modules", McpToolClass.read_only, McpSuite.wos_author, AUTH_FILESYSTEM_REPO),
    ("wos.goc.get_module", McpToolClass.read_only, McpSuite.wos_author, AUTH_FILESYSTEM_REPO),
    ("wos.content.search", McpToolClass.read_only, McpSuite.wos_author, AUTH_FILESYSTEM_REPO),
    ("wos.research.source.inspect", McpToolClass.read_only, McpSuite.wos_ai, AUTH_AI_STACK_CAPABILITY_CATALOG),
    ("wos.research.aspect.extract", McpToolClass.read_only, McpSuite.wos_ai, AUTH_AI_STACK_CAPABILITY_CATALOG),
    ("wos.research.claim.list", McpToolClass.read_only, McpSuite.wos_ai, AUTH_AI_STACK_CAPABILITY_CATALOG),
    ("wos.research.run.get", McpToolClass.read_only, McpSuite.wos_ai, AUTH_AI_STACK_CAPABILITY_CATALOG),
    ("wos.research.exploration.graph", McpToolClass.read_only, McpSuite.wos_ai, AUTH_AI_STACK_CAPABILITY_CATALOG),
    ("wos.canon.issue.inspect", McpToolClass.read_only, McpSuite.wos_ai, AUTH_AI_STACK_CAPABILITY_CATALOG),
    ("wos.research.explore", McpToolClass.review_bound, McpSuite.wos_ai, AUTH_AI_STACK_CAPABILITY_CATALOG),
    ("wos.research.validate", McpToolClass.review_bound, McpSuite.wos_ai, AUTH_AI_STACK_CAPABILITY_CATALOG),
    ("wos.research.bundle.build", McpToolClass.review_bound, McpSuite.wos_ai, AUTH_AI_STACK_CAPABILITY_CATALOG),
    ("wos.canon.improvement.propose", McpToolClass.write_capable, McpSuite.wos_ai, AUTH_AI_STACK_CAPABILITY_CATALOG),
    ("wos.canon.improvement.preview", McpToolClass.review_bound, McpSuite.wos_ai, AUTH_AI_STACK_CAPABILITY_CATALOG),
    ("run_projection_tests", McpToolClass.review_bound, McpSuite.wos_ai, AUTH_BACKEND_HTTP),
    ("fetch_langfuse_trace", McpToolClass.read_only, McpSuite.wos_ai, AUTH_BACKEND_HTTP),
    ("query_langfuse_traces", McpToolClass.read_only, McpSuite.wos_ai, AUTH_BACKEND_HTTP),
    ("assert_langfuse_opening_contract", McpToolClass.review_bound, McpSuite.wos_ai, AUTH_BACKEND_HTTP),
    ("summarize_live_opening_matrix", McpToolClass.read_only, McpSuite.wos_ai, AUTH_BACKEND_HTTP),
    ("fetch_langfuse_trace_scores", McpToolClass.read_only, McpSuite.wos_ai, AUTH_BACKEND_HTTP),
    ("summarize_opening_judge_scores", McpToolClass.read_only, McpSuite.wos_ai, AUTH_BACKEND_HTTP),
    ("build_opening_quality_context", McpToolClass.read_only, McpSuite.wos_ai, AUTH_BACKEND_HTTP),
)


def _build_descriptor(name: str, tool_class: McpToolClass, suite: McpSuite, authority: str) -> McpCanonicalToolDescriptor:
    governance = McpToolGovernanceView(
        published_vs_draft="published",
        canonical_vs_supporting=_derive_canonical_vs_supporting(name, tool_class),
        runtime_safe_vs_internal_only=_derive_runtime_safe_vs_internal(name, tool_class),
        writers_room_visible_vs_runtime_hidden=_writers_room_visibility_token(["runtime"]),
        reviewable_vs_publishable_posture=_derive_reviewable_posture(tool_class, name),
    )
    return McpCanonicalToolDescriptor(
        name=name,
        tool_class=tool_class,
        authority_source=authority,
        implementation_status=McpImplementationStatus.implemented,
        permission_legacy=_derive_permission_legacy(tool_class, name),
        narrative_mutation_risk=_derive_governance_risk_token(name, "action"),
        governance=governance,
        mcp_suite=suite,
    )


CANONICAL_MCP_TOOL_DESCRIPTORS: tuple[McpCanonicalToolDescriptor, ...] = tuple(
    _build_descriptor(n, tc, s, a) for (n, tc, s, a) in _TOOL_SPECS
)

MCP_CATALOG_CAPABILITY_NAMES: tuple[str, ...] = tuple(sorted(d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS))


class CanonicalMCPSurface:
    """Defines a concise MCP tool-spec list for simple consumers."""

    TOOLS: list[dict[str, Any]] = [
        {"name": "wos.session.get", "description": "Get full session state", "input_schema": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]}, "output_schema": {"type": "object", "properties": {"session_id": {"type": "string"}}}},
        {"name": "wos.session.state", "description": "Get current game state snapshot", "input_schema": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]}, "output_schema": {"type": "object", "properties": {"state": {"type": "object"}}}},
        {"name": "wos.session.logs", "description": "Get turn history and logs", "input_schema": {"type": "object", "properties": {"session_id": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["session_id"]}, "output_schema": {"type": "object", "properties": {"history": {"type": "array"}}}},
        {"name": "wos.session.diag", "description": "Get diagnostic info", "input_schema": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]}, "output_schema": {"type": "object", "properties": {"diagnostics": {"type": "object"}}}},
        {"name": "wos.session.execute_turn", "description": "Execute a player action", "input_schema": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]}, "output_schema": {"type": "object", "properties": {"success": {"type": "boolean"}}}},
    ]

    def list_tool_specs(self) -> list[dict[str, Any]]:
        return self.TOOLS

    def get_tool_spec(self, tool_name: str) -> dict[str, Any] | None:
        for tool in self.TOOLS:
            if tool["name"] == tool_name:
                return tool
        return None


def resolve_mcp_operating_profile() -> McpOperatingProfile:
    raw = os.environ.get("WOS_MCP_OPERATING_PROFILE", "").strip().lower()
    if not raw:
        return McpOperatingProfile.healthy
    for p in McpOperatingProfile:
        if p.value == raw:
            return p
    return McpOperatingProfile.degraded


def operating_profile_allows_write_capable(profile: McpOperatingProfile) -> bool:
    return profile is McpOperatingProfile.healthy


def resolve_active_mcp_suite_filter() -> McpSuite | None:
    raw = os.environ.get("WOS_MCP_SUITE", "").strip().lower()
    if not raw:
        return None
    for suite in McpSuite:
        if suite.value == raw:
            return suite
    return None


def canonical_tool_names_for_suite(suite: McpSuite) -> tuple[str, ...]:
    return tuple(d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS if d.mcp_suite == suite)


def canonical_mcp_tool_descriptors_by_name() -> dict[str, McpCanonicalToolDescriptor]:
    return {d.name: d for d in CANONICAL_MCP_TOOL_DESCRIPTORS}


def descriptor_to_public_metadata(desc: McpCanonicalToolDescriptor) -> dict[str, Any]:
    return {
        "authority_source": desc.authority_source,
        "tool_class": desc.tool_class.value,
        "implementation_status": desc.implementation_status.value,
        "governance": governance_dict(desc.governance),
        "narrative_mutation_risk": desc.narrative_mutation_risk,
        "mcp_suite": desc.mcp_suite.value,
    }


def capability_records_for_mcp() -> list[dict[str, Any]]:
    """Mirror ``capability_catalog()`` with MCP governance metadata (see docs/mcp/12_M1_canonical_parity.md)."""
    from ai_stack.capabilities import capability_catalog

    rows: list[dict[str, Any]] = []
    for entry in capability_catalog():
        name = str(entry.get("name") or "")
        kind = str(entry.get("kind") or "retrieval")
        tc = _tool_class_for_capability_row(name, kind)
        modes = list(entry.get("allowed_modes") or [])
        gov = McpToolGovernanceView(
            published_vs_draft="published",
            canonical_vs_supporting=_derive_canonical_vs_supporting(name, tc),
            runtime_safe_vs_internal_only=_derive_runtime_safe_vs_internal(name, tc),
            writers_room_visible_vs_runtime_hidden=_writers_room_visibility_token(modes),
            reviewable_vs_publishable_posture=_derive_reviewable_posture(tc, name),
        )
        rows.append(
            {
                "name": name,
                "kind": kind,
                "allowed_modes": modes,
                "tool_class": tc.value,
                "authority_source": AUTH_AI_STACK_CAPABILITY_CATALOG,
                "implementation_status": McpImplementationStatus.implemented.value,
                "governance_posture": governance_dict(gov),
                "narrative_mutation_risk": _derive_governance_risk_token(name, kind),
                "mcp_suite": McpSuite.wos_ai.value,
            }
        )
    return rows


def verify_catalog_names_alignment() -> dict[str, Any]:
    expected = list(MCP_CATALOG_CAPABILITY_NAMES)
    observed = sorted(d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS)
    return {"aligned": expected == observed, "expected": expected, "observed": observed, "errors": []}


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
    if profile is McpOperatingProfile.test_isolated:
        return "test_isolated"
    if profile is McpOperatingProfile.degraded or backend_reachable is False:
        return "degraded"
    return "healthy"


def classify_mcp_no_eligible_discipline(
    *,
    catalog_alignment_ok: bool,
    implemented_tool_count: int,
    deferred_stub_count: int,
    profile: McpOperatingProfile,
) -> dict[str, Any]:
    if not catalog_alignment_ok:
        return {"applicable": True, "operator_meaning_token": "misconfigured_capability_catalog_mismatch", "discipline_worst_case": "misconfigured", "stages_reporting_no_eligible_adapter": ["mcp_tool_surface"]}
    if profile is McpOperatingProfile.degraded:
        return {"applicable": True, "operator_meaning_token": "degraded_profile_operator_declared", "discipline_worst_case": "degraded_but_controlled", "stages_reporting_no_eligible_adapter": ["mcp_tool_surface"]}
    if profile is McpOperatingProfile.test_isolated:
        return {"applicable": True, "operator_meaning_token": "test_isolated_expected_posture_not_true_no_eligible", "discipline_worst_case": "test_isolated_empty_or_suppressed", "stages_reporting_no_eligible_adapter": ["mcp_tool_surface"]}
    if implemented_tool_count == 0 and deferred_stub_count == 0:
        return {"applicable": True, "operator_meaning_token": "true_no_eligible_mcp_surface", "discipline_worst_case": "true_no_eligible_adapter", "stages_reporting_no_eligible_adapter": ["mcp_tool_surface"]}
    return {"applicable": False, "operator_meaning_token": "healthy_mcp_surface_with_implemented_tools", "discipline_worst_case": "not_applicable", "stages_reporting_no_eligible_adapter": []}


def build_compact_mcp_operator_truth(
    *,
    backend_reachable: bool | None = None,
    catalog_alignment_ok: bool = True,
    registry_tool_names: list[str] | None = None,
) -> dict[str, Any]:
    profile = resolve_mcp_operating_profile()
    names = set(registry_tool_names or [])
    available = len(names)
    deferred = 0
    cls_counts = {"read_only": 0, "review_bound": 0, "write_capable": 0}
    by_name = canonical_mcp_tool_descriptors_by_name()
    for name in names:
        desc = by_name.get(name)
        if desc is not None:
            cls_counts[desc.tool_class.value] += 1
    return {
        "grammar_version": MCP_OPERATOR_TRUTH_GRAMMAR_VERSION,
        "authority_source": "canonical_mcp_surface",
        "startup_profile": profile.value,
        "operational_state": _operational_state_token(profile=profile, backend_reachable=backend_reachable, catalog_alignment_ok=catalog_alignment_ok),
        "route_status": _route_status_token(profile=profile, backend_reachable=backend_reachable, catalog_alignment_ok=catalog_alignment_ok),
        "available_vs_deferred": {"available": available, "deferred": deferred, "tool_classes": cls_counts},
        "governance_posture": {
            "read_only_allowed": True,
            "review_bound_allowed": True,
            "write_capable_allowed": operating_profile_allows_write_capable(profile),
        },
        "readiness_posture": "ready" if available > 0 else "empty",
        "primary_operational_concern": "catalog_mismatch" if not catalog_alignment_ok else ("backend_unreachable" if backend_reachable is False else "none"),
        "no_eligible_operator_meaning": classify_mcp_no_eligible_discipline(
            catalog_alignment_ok=catalog_alignment_ok,
            implemented_tool_count=available,
            deferred_stub_count=deferred,
            profile=profile,
        )["operator_meaning_token"],
        "runtime_authority_preservation": "preserved",
    }
