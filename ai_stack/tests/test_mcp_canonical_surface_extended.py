"""Extended coverage for mcp_canonical_surface: target 95%+ coverage.

Focuses on:
- All _derive_* helper functions
- Edge cases in resolver functions
- All governance derivation paths
- Error conditions and boundary cases
"""

import os
import pytest

from ai_stack.mcp_canonical_surface import (
    AUTH_BACKEND_HTTP,
    AUTH_FILESYSTEM_REPO,
    AUTH_AI_STACK_CAPABILITY_CATALOG,
    AUTH_MCP_SURFACE_META,
    CANONICAL_MCP_TOOL_DESCRIPTORS,
    MCP_CATALOG_CAPABILITY_NAMES,
    MCP_OPERATOR_TRUTH_GRAMMAR_VERSION,
    MCP_SUITES_ALL,
    McpCanonicalToolDescriptor,
    McpImplementationStatus,
    McpOperatingProfile,
    McpSuite,
    McpToolClass,
    McpToolGovernanceView,
    build_compact_mcp_operator_truth,
    canonical_mcp_tool_descriptors_by_name,
    canonical_tool_names_for_suite,
    classify_mcp_no_eligible_discipline,
    descriptor_to_public_metadata,
    governance_dict,
    operating_profile_allows_write_capable,
    resolve_active_mcp_suite_filter,
    resolve_mcp_operating_profile,
    verify_catalog_names_alignment,
    _derive_canonical_vs_supporting,
    _derive_governance_risk_token,
    _derive_permission_legacy,
    _derive_reviewable_posture,
    _derive_runtime_safe_vs_internal,
    _operational_state_token,
    _route_status_token,
    _tool_class_for_capability_row,
    _writers_room_visibility_token,
)
from ai_stack.capabilities import CapabilityKind


# ============================================================================
# Tests for resolve_mcp_operating_profile()
# ============================================================================


def test_resolve_mcp_operating_profile_healthy_default(monkeypatch):
    monkeypatch.delenv("WOS_MCP_OPERATING_PROFILE", raising=False)
    profile = resolve_mcp_operating_profile()
    assert profile is McpOperatingProfile.healthy


def test_resolve_mcp_operating_profile_explicit_healthy(monkeypatch):
    monkeypatch.setenv("WOS_MCP_OPERATING_PROFILE", "healthy")
    profile = resolve_mcp_operating_profile()
    assert profile is McpOperatingProfile.healthy


def test_resolve_mcp_operating_profile_case_insensitive(monkeypatch):
    monkeypatch.setenv("WOS_MCP_OPERATING_PROFILE", "REVIEW_SAFE")
    profile = resolve_mcp_operating_profile()
    assert profile is McpOperatingProfile.review_safe


def test_resolve_mcp_operating_profile_whitespace_stripped(monkeypatch):
    monkeypatch.setenv("WOS_MCP_OPERATING_PROFILE", "  test_isolated  ")
    profile = resolve_mcp_operating_profile()
    assert profile is McpOperatingProfile.test_isolated


def test_resolve_mcp_operating_profile_invalid_defaults_degraded(monkeypatch):
    monkeypatch.setenv("WOS_MCP_OPERATING_PROFILE", "invalid_profile")
    profile = resolve_mcp_operating_profile()
    assert profile is McpOperatingProfile.degraded


def test_resolve_mcp_operating_profile_empty_string(monkeypatch):
    monkeypatch.setenv("WOS_MCP_OPERATING_PROFILE", "")
    profile = resolve_mcp_operating_profile()
    assert profile is McpOperatingProfile.healthy


# ============================================================================
# Tests for operating_profile_allows_write_capable()
# ============================================================================


def test_operating_profile_allows_write_capable_healthy():
    assert operating_profile_allows_write_capable(McpOperatingProfile.healthy) is True


def test_operating_profile_allows_write_capable_degraded():
    assert operating_profile_allows_write_capable(McpOperatingProfile.degraded) is False


def test_operating_profile_allows_write_capable_test_isolated():
    assert operating_profile_allows_write_capable(McpOperatingProfile.test_isolated) is False


def test_operating_profile_allows_write_capable_review_safe():
    assert operating_profile_allows_write_capable(McpOperatingProfile.review_safe) is False


# ============================================================================
# Tests for resolve_active_mcp_suite_filter()
# ============================================================================


def test_resolve_active_mcp_suite_filter_default_no_filter(monkeypatch):
    monkeypatch.delenv("WOS_MCP_SUITE", raising=False)
    result = resolve_active_mcp_suite_filter()
    assert result is None


def test_resolve_active_mcp_suite_filter_all_no_filter(monkeypatch):
    monkeypatch.setenv("WOS_MCP_SUITE", "all")
    result = resolve_active_mcp_suite_filter()
    assert result is None


def test_resolve_active_mcp_suite_filter_wildcard_no_filter(monkeypatch):
    monkeypatch.setenv("WOS_MCP_SUITE", "*")
    result = resolve_active_mcp_suite_filter()
    assert result is None


def test_resolve_active_mcp_suite_filter_empty_string(monkeypatch):
    monkeypatch.setenv("WOS_MCP_SUITE", "")
    result = resolve_active_mcp_suite_filter()
    assert result is None


def test_resolve_active_mcp_suite_filter_valid_suite(monkeypatch):
    monkeypatch.setenv("WOS_MCP_SUITE", "wos-admin")
    result = resolve_active_mcp_suite_filter()
    assert result is McpSuite.wos_admin


def test_resolve_active_mcp_suite_filter_case_insensitive(monkeypatch):
    monkeypatch.setenv("WOS_MCP_SUITE", "WOS-AUTHOR")
    result = resolve_active_mcp_suite_filter()
    assert result is McpSuite.wos_author


def test_resolve_active_mcp_suite_filter_whitespace_stripped(monkeypatch):
    monkeypatch.setenv("WOS_MCP_SUITE", "  wos-ai  ")
    result = resolve_active_mcp_suite_filter()
    assert result is McpSuite.wos_ai


def test_resolve_active_mcp_suite_filter_invalid_value(monkeypatch):
    monkeypatch.setenv("WOS_MCP_SUITE", "invalid_suite")
    result = resolve_active_mcp_suite_filter()
    assert result is None


# ============================================================================
# Tests for canonical_tool_names_for_suite()
# ============================================================================


def test_canonical_tool_names_for_suite_wos_admin():
    names = canonical_tool_names_for_suite(McpSuite.wos_admin)
    assert isinstance(names, tuple)
    assert len(names) > 0
    assert all(isinstance(n, str) for n in names)
    assert all(d.mcp_suite == McpSuite.wos_admin for d in CANONICAL_MCP_TOOL_DESCRIPTORS if d.name in names)


def test_canonical_tool_names_for_suite_wos_author():
    names = canonical_tool_names_for_suite(McpSuite.wos_author)
    assert isinstance(names, tuple)
    assert len(names) > 0


def test_canonical_tool_names_for_suite_wos_ai():
    names = canonical_tool_names_for_suite(McpSuite.wos_ai)
    assert isinstance(names, tuple)
    assert len(names) > 0


def test_canonical_tool_names_for_suite_wos_runtime_read():
    names = canonical_tool_names_for_suite(McpSuite.wos_runtime_read)
    assert isinstance(names, tuple)


def test_canonical_tool_names_for_suite_wos_runtime_control():
    names = canonical_tool_names_for_suite(McpSuite.wos_runtime_control)
    assert isinstance(names, tuple)


def test_canonical_tool_names_for_suite_all_suites():
    suite_counts = {}
    for suite in McpSuite:
        names = canonical_tool_names_for_suite(suite)
        suite_counts[suite] = len(names)
    total = sum(suite_counts.values())
    expected_total = len(CANONICAL_MCP_TOOL_DESCRIPTORS)
    assert total == expected_total


# ============================================================================
# Tests for canonical_mcp_tool_descriptors_by_name()
# ============================================================================


def test_canonical_mcp_tool_descriptors_by_name_returns_dict():
    result = canonical_mcp_tool_descriptors_by_name()
    assert isinstance(result, dict)


def test_canonical_mcp_tool_descriptors_by_name_has_all_descriptors():
    result = canonical_mcp_tool_descriptors_by_name()
    assert len(result) == len(CANONICAL_MCP_TOOL_DESCRIPTORS)
    for descriptor in CANONICAL_MCP_TOOL_DESCRIPTORS:
        assert descriptor.name in result
        assert result[descriptor.name] is descriptor


def test_canonical_mcp_tool_descriptors_by_name_values_are_descriptors():
    result = canonical_mcp_tool_descriptors_by_name()
    for value in result.values():
        assert isinstance(value, McpCanonicalToolDescriptor)


# ============================================================================
# Tests for _tool_class_for_capability_row()
# ============================================================================


def test_tool_class_for_capability_row_retrieval_is_read_only():
    tc = _tool_class_for_capability_row("some_retrieval_tool", CapabilityKind.RETRIEVAL.value)
    assert tc is McpToolClass.read_only


def test_tool_class_for_capability_row_review_bundle_build_is_review_bound():
    tc = _tool_class_for_capability_row("wos.review_bundle.build", "some_kind")
    assert tc is McpToolClass.review_bound


def test_tool_class_for_capability_row_other_tools_are_review_bound():
    tc = _tool_class_for_capability_row("wos.some.tool", "some_kind")
    assert tc is McpToolClass.review_bound


def test_tool_class_for_capability_row_non_retrieval_kind():
    tc = _tool_class_for_capability_row("wos.another.tool", "GENERATION")
    assert tc is McpToolClass.review_bound


# ============================================================================
# Tests for _writers_room_visibility_token()
# ============================================================================


def test_writers_room_visibility_token_writers_room_only():
    token = _writers_room_visibility_token(["writers_room"])
    assert token == "writers_room_visible_runtime_may_skip"


def test_writers_room_visibility_token_writers_room_and_runtime():
    token = _writers_room_visibility_token(["writers_room", "runtime"])
    assert token == "writers_room_visible"


def test_writers_room_visibility_token_runtime_only():
    token = _writers_room_visibility_token(["runtime"])
    assert token == "runtime_focused"


def test_writers_room_visibility_token_improvement_mode():
    token = _writers_room_visibility_token(["improvement"])
    assert token == "runtime_focused"


def test_writers_room_visibility_token_empty_modes():
    token = _writers_room_visibility_token([])
    assert token == "mode_gated"


def test_writers_room_visibility_token_unknown_modes():
    token = _writers_room_visibility_token(["unknown_mode"])
    assert token == "mode_gated"


def test_writers_room_visibility_token_multiple_unknown_modes():
    token = _writers_room_visibility_token(["mode1", "mode2", "mode3"])
    assert token == "mode_gated"


# ============================================================================
# Tests for _derive_reviewable_posture()
# ============================================================================


def test_derive_reviewable_posture_read_only_tools():
    posture = _derive_reviewable_posture(McpToolClass.read_only, "any_name")
    assert posture == "read_only_no_review_path"


def test_derive_reviewable_posture_build_in_name():
    posture = _derive_reviewable_posture(McpToolClass.review_bound, "wos.something.build")
    assert posture == "review_required_for_mutation"


def test_derive_reviewable_posture_create_in_name():
    posture = _derive_reviewable_posture(McpToolClass.review_bound, "wos.something.create")
    assert posture == "review_required_for_mutation"


def test_derive_reviewable_posture_execute_in_name():
    posture = _derive_reviewable_posture(McpToolClass.review_bound, "wos.something.execute")
    assert posture == "review_required_for_mutation"


def test_derive_reviewable_posture_other_names():
    posture = _derive_reviewable_posture(McpToolClass.review_bound, "wos.something.list")
    assert posture == "read_and_review_paths"


def test_derive_reviewable_posture_write_capable():
    posture = _derive_reviewable_posture(McpToolClass.write_capable, "wos.something.other")
    assert posture == "read_and_review_paths"


# ============================================================================
# Tests for _derive_governance_risk_token()
# ============================================================================


def test_derive_governance_risk_token_retrieval_kind():
    token = _derive_governance_risk_token("any_name", CapabilityKind.RETRIEVAL.value)
    assert token == "none_read_only"


def test_derive_governance_risk_token_execute_in_name():
    token = _derive_governance_risk_token("wos.something.execute", "GENERATION")
    assert token == "high_direct_authority_mutation"


def test_derive_governance_risk_token_commit_in_name():
    token = _derive_governance_risk_token("wos.something.commit", "GENERATION")
    assert token == "high_direct_authority_mutation"


def test_derive_governance_risk_token_publish_in_name():
    token = _derive_governance_risk_token("wos.something.publish", "GENERATION")
    assert token == "high_direct_authority_mutation"


def test_derive_governance_risk_token_build_in_name():
    token = _derive_governance_risk_token("wos.something.build", "GENERATION")
    assert token == "medium_stage_mutation"


def test_derive_governance_risk_token_create_in_name():
    token = _derive_governance_risk_token("wos.something.create", "GENERATION")
    assert token == "medium_stage_mutation"


def test_derive_governance_risk_token_diag_in_name():
    token = _derive_governance_risk_token("wos.session.diag", "GENERATION")
    assert token == "none_observation_only"


def test_derive_governance_risk_token_logs_in_name():
    token = _derive_governance_risk_token("wos.session.logs", "GENERATION")
    assert token == "none_observation_only"


def test_derive_governance_risk_token_state_in_name():
    token = _derive_governance_risk_token("wos.session.state", "GENERATION")
    assert token == "none_observation_only"


def test_derive_governance_risk_token_other_names():
    token = _derive_governance_risk_token("wos.something.other", "GENERATION")
    assert token == "medium_standard"


# ============================================================================
# Tests for _derive_runtime_safe_vs_internal()
# ============================================================================


def test_derive_runtime_safe_vs_internal_session_get():
    result = _derive_runtime_safe_vs_internal("wos.session.get", McpToolClass.read_only)
    assert result == "runtime_safe"


def test_derive_runtime_safe_vs_internal_session_logs():
    result = _derive_runtime_safe_vs_internal("wos.session.logs", McpToolClass.read_only)
    assert result == "runtime_safe"


def test_derive_runtime_safe_vs_internal_session_state():
    result = _derive_runtime_safe_vs_internal("wos.session.state", McpToolClass.read_only)
    assert result == "runtime_safe"


def test_derive_runtime_safe_vs_internal_session_diag():
    result = _derive_runtime_safe_vs_internal("wos.session.diag", McpToolClass.read_only)
    assert result == "runtime_safe"


def test_derive_runtime_safe_vs_internal_session_execute_turn():
    result = _derive_runtime_safe_vs_internal("wos.session.execute_turn", McpToolClass.review_bound)
    assert result == "internal_only_via_runtime_executor"


def test_derive_runtime_safe_vs_internal_session_write_capable():
    result = _derive_runtime_safe_vs_internal("wos.session.other", McpToolClass.write_capable)
    assert result == "runtime_safe"


def test_derive_runtime_safe_vs_internal_goc_list_modules():
    result = _derive_runtime_safe_vs_internal("wos.goc.list_modules", McpToolClass.read_only)
    assert result == "runtime_safe"


def test_derive_runtime_safe_vs_internal_content_search():
    result = _derive_runtime_safe_vs_internal("wos.content.search", McpToolClass.read_only)
    assert result == "runtime_safe"


def test_derive_runtime_safe_vs_internal_system_health():
    result = _derive_runtime_safe_vs_internal("wos.system.health", McpToolClass.read_only)
    assert result == "runtime_safe"


def test_derive_runtime_safe_vs_internal_session_create():
    result = _derive_runtime_safe_vs_internal("wos.session.create", McpToolClass.write_capable)
    assert result == "runtime_safe"


# ============================================================================
# Tests for _derive_canonical_vs_supporting()
# ============================================================================


def test_derive_canonical_vs_supporting_session_read_only():
    result = _derive_canonical_vs_supporting("wos.session.get", McpToolClass.read_only)
    assert result == "session_observability_canonical"


def test_derive_canonical_vs_supporting_session_logs_read_only():
    result = _derive_canonical_vs_supporting("wos.session.logs", McpToolClass.read_only)
    assert result == "session_observability_canonical"


def test_derive_canonical_vs_supporting_session_execute_turn():
    result = _derive_canonical_vs_supporting("wos.session.execute_turn", McpToolClass.review_bound)
    assert result == "runtime_turn_authority_required"


def test_derive_canonical_vs_supporting_session_create():
    result = _derive_canonical_vs_supporting("wos.session.create", McpToolClass.write_capable)
    assert result == "session_shell_not_manuscript"


def test_derive_canonical_vs_supporting_goc_list_modules():
    result = _derive_canonical_vs_supporting("wos.goc.list_modules", McpToolClass.read_only)
    assert result == "supporting_content_files"


def test_derive_canonical_vs_supporting_content_search():
    result = _derive_canonical_vs_supporting("wos.content.search", McpToolClass.read_only)
    assert result == "supporting_content_files"


def test_derive_canonical_vs_supporting_other_tools():
    result = _derive_canonical_vs_supporting("wos.research.explore", McpToolClass.review_bound)
    assert result == "supporting"


# ============================================================================
# Tests for _derive_permission_legacy()
# ============================================================================


def test_derive_permission_legacy_read_only():
    perm = _derive_permission_legacy(McpToolClass.read_only, "any_name")
    assert perm == "read"


def test_derive_permission_legacy_review_bound():
    perm = _derive_permission_legacy(McpToolClass.review_bound, "any_name")
    assert perm == "preview"


def test_derive_permission_legacy_write_capable():
    perm = _derive_permission_legacy(McpToolClass.write_capable, "any_name")
    assert perm == "write"


# ============================================================================
# Tests for governance_dict()
# ============================================================================


def test_governance_dict_returns_all_fields():
    view = McpToolGovernanceView(
        published_vs_draft="pub",
        canonical_vs_supporting="can",
        runtime_safe_vs_internal_only="runtime",
        writers_room_visible_vs_runtime_hidden="writers",
        reviewable_vs_publishable_posture="review",
    )
    result = governance_dict(view)
    assert result == {
        "published_vs_draft": "pub",
        "canonical_vs_supporting": "can",
        "runtime_safe_vs_internal_only": "runtime",
        "writers_room_visible_vs_runtime_hidden": "writers",
        "reviewable_vs_publishable_posture": "review",
    }


# ============================================================================
# Tests for descriptor_to_public_metadata()
# ============================================================================


def test_descriptor_to_public_metadata_has_expected_keys():
    desc = CANONICAL_MCP_TOOL_DESCRIPTORS[0]
    metadata = descriptor_to_public_metadata(desc)
    assert "authority_source" in metadata
    assert "tool_class" in metadata
    assert "implementation_status" in metadata
    assert "governance" in metadata
    assert "narrative_mutation_risk" in metadata
    assert "mcp_suite" in metadata


def test_descriptor_to_public_metadata_values_are_strings():
    desc = CANONICAL_MCP_TOOL_DESCRIPTORS[0]
    metadata = descriptor_to_public_metadata(desc)
    assert isinstance(metadata["authority_source"], str)
    assert isinstance(metadata["tool_class"], str)
    assert isinstance(metadata["implementation_status"], str)
    assert isinstance(metadata["narrative_mutation_risk"], str)
    assert isinstance(metadata["mcp_suite"], str)


def test_descriptor_to_public_metadata_governance_is_dict():
    desc = CANONICAL_MCP_TOOL_DESCRIPTORS[0]
    metadata = descriptor_to_public_metadata(desc)
    assert isinstance(metadata["governance"], dict)
    assert len(metadata["governance"]) == 5


def test_descriptor_to_public_metadata_all_descriptors():
    for desc in CANONICAL_MCP_TOOL_DESCRIPTORS:
        metadata = descriptor_to_public_metadata(desc)
        assert "authority_source" in metadata
        assert "tool_class" in metadata
        assert "governance" in metadata


# ============================================================================
# Tests for _route_status_token()
# ============================================================================


def test_route_status_token_misconfigured_catalog():
    token = _route_status_token(
        profile=McpOperatingProfile.healthy,
        backend_reachable=True,
        catalog_alignment_ok=False,
    )
    assert token == "misconfigured_catalog_translation"


def test_route_status_token_test_isolated():
    token = _route_status_token(
        profile=McpOperatingProfile.test_isolated,
        backend_reachable=True,
        catalog_alignment_ok=True,
    )
    assert token == "test_isolated_mcp_posture"


def test_route_status_token_degraded():
    token = _route_status_token(
        profile=McpOperatingProfile.degraded,
        backend_reachable=True,
        catalog_alignment_ok=True,
    )
    assert token == "degraded_operator_declared"


def test_route_status_token_review_safe():
    token = _route_status_token(
        profile=McpOperatingProfile.review_safe,
        backend_reachable=True,
        catalog_alignment_ok=True,
    )
    assert token == "review_safe_writes_suppressed"


def test_route_status_token_backend_unreachable():
    token = _route_status_token(
        profile=McpOperatingProfile.healthy,
        backend_reachable=False,
        catalog_alignment_ok=True,
    )
    assert token == "backend_unreachable_degraded_operations"


def test_route_status_token_healthy():
    token = _route_status_token(
        profile=McpOperatingProfile.healthy,
        backend_reachable=True,
        catalog_alignment_ok=True,
    )
    assert token == "canonical_mcp_tools_registered"


def test_route_status_token_backend_reachable_none():
    token = _route_status_token(
        profile=McpOperatingProfile.healthy,
        backend_reachable=None,
        catalog_alignment_ok=True,
    )
    assert token == "canonical_mcp_tools_registered"


# ============================================================================
# Tests for _operational_state_token()
# ============================================================================


def test_operational_state_token_misconfigured():
    token = _operational_state_token(
        profile=McpOperatingProfile.healthy,
        backend_reachable=True,
        catalog_alignment_ok=False,
    )
    assert token == "misconfigured"


def test_operational_state_token_degraded_profile():
    token = _operational_state_token(
        profile=McpOperatingProfile.degraded,
        backend_reachable=True,
        catalog_alignment_ok=True,
    )
    assert token == "degraded"


def test_operational_state_token_test_isolated():
    token = _operational_state_token(
        profile=McpOperatingProfile.test_isolated,
        backend_reachable=True,
        catalog_alignment_ok=True,
    )
    assert token == "test_isolated"


def test_operational_state_token_backend_unreachable():
    token = _operational_state_token(
        profile=McpOperatingProfile.healthy,
        backend_reachable=False,
        catalog_alignment_ok=True,
    )
    assert token == "degraded"


def test_operational_state_token_healthy():
    token = _operational_state_token(
        profile=McpOperatingProfile.healthy,
        backend_reachable=True,
        catalog_alignment_ok=True,
    )
    assert token == "healthy"


# ============================================================================
# Tests for classify_mcp_no_eligible_discipline()
# ============================================================================


def test_classify_mcp_no_eligible_discipline_catalog_mismatch():
    result = classify_mcp_no_eligible_discipline(
        catalog_alignment_ok=False,
        implemented_tool_count=10,
        deferred_stub_count=0,
        profile=McpOperatingProfile.healthy,
    )
    assert result["applicable"] is True
    assert result["operator_meaning_token"] == "misconfigured_capability_catalog_mismatch"
    assert result["discipline_worst_case"] == "misconfigured"


def test_classify_mcp_no_eligible_discipline_degraded_profile():
    result = classify_mcp_no_eligible_discipline(
        catalog_alignment_ok=True,
        implemented_tool_count=10,
        deferred_stub_count=0,
        profile=McpOperatingProfile.degraded,
    )
    assert result["applicable"] is True
    assert result["operator_meaning_token"] == "degraded_profile_operator_declared"
    assert result["discipline_worst_case"] == "degraded_but_controlled"


def test_classify_mcp_no_eligible_discipline_test_isolated():
    result = classify_mcp_no_eligible_discipline(
        catalog_alignment_ok=True,
        implemented_tool_count=10,
        deferred_stub_count=0,
        profile=McpOperatingProfile.test_isolated,
    )
    assert result["applicable"] is True
    assert result["operator_meaning_token"] == "test_isolated_expected_posture_not_true_no_eligible"
    assert result["discipline_worst_case"] == "test_isolated_empty_or_suppressed"


def test_classify_mcp_no_eligible_discipline_no_tools():
    result = classify_mcp_no_eligible_discipline(
        catalog_alignment_ok=True,
        implemented_tool_count=0,
        deferred_stub_count=0,
        profile=McpOperatingProfile.healthy,
    )
    assert result["applicable"] is True
    assert result["operator_meaning_token"] == "true_no_eligible_mcp_surface"
    assert result["discipline_worst_case"] == "true_no_eligible_adapter"
    assert "mcp_tool_surface" in result["stages_reporting_no_eligible_adapter"]


def test_classify_mcp_no_eligible_discipline_healthy():
    result = classify_mcp_no_eligible_discipline(
        catalog_alignment_ok=True,
        implemented_tool_count=10,
        deferred_stub_count=0,
        profile=McpOperatingProfile.healthy,
    )
    assert result["applicable"] is False
    assert result["operator_meaning_token"] == "healthy_mcp_surface_with_implemented_tools"
    assert result["discipline_worst_case"] == "not_applicable"


# ============================================================================
# Tests for build_compact_mcp_operator_truth()
# ============================================================================


def test_build_compact_mcp_operator_truth_healthy_all_tools():
    names = [d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS]
    ot = build_compact_mcp_operator_truth(
        backend_reachable=True,
        catalog_alignment_ok=True,
        registry_tool_names=names,
    )
    assert ot["grammar_version"] == MCP_OPERATOR_TRUTH_GRAMMAR_VERSION
    assert ot["operational_state"] == "healthy"
    assert ot["route_status"] == "canonical_mcp_tools_registered"
    assert ot["available_vs_deferred"]["available"] > 0
    assert "tool_classes" in ot["available_vs_deferred"]
    assert ot["governance_posture"]["write_capable_allowed"] is True


def test_build_compact_mcp_operator_truth_backend_unreachable():
    names = [d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS]
    ot = build_compact_mcp_operator_truth(
        backend_reachable=False,
        catalog_alignment_ok=True,
        registry_tool_names=names,
    )
    assert ot["operational_state"] == "degraded"
    assert ot["route_status"] == "backend_unreachable_degraded_operations"
    assert ot["primary_operational_concern"] == "backend_unreachable"


def test_build_compact_mcp_operator_truth_catalog_mismatch():
    names = [d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS]
    ot = build_compact_mcp_operator_truth(
        backend_reachable=True,
        catalog_alignment_ok=False,
        registry_tool_names=names,
    )
    assert ot["operational_state"] == "misconfigured"
    assert ot["route_status"] == "misconfigured_catalog_translation"
    assert ot["primary_operational_concern"] == "catalog_mismatch"


def test_build_compact_mcp_operator_truth_empty_registry():
    ot = build_compact_mcp_operator_truth(
        backend_reachable=True,
        catalog_alignment_ok=True,
        registry_tool_names=[],
    )
    assert ot["available_vs_deferred"]["available"] == 0
    assert ot["available_vs_deferred"]["deferred"] == 0


def test_build_compact_mcp_operator_truth_backend_reachable_none():
    names = [d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS]
    ot = build_compact_mcp_operator_truth(
        backend_reachable=None,
        catalog_alignment_ok=True,
        registry_tool_names=names,
    )
    assert ot["operational_state"] == "healthy"
    assert ot["primary_operational_concern"] == "none"


def test_build_compact_mcp_operator_truth_degraded_profile(monkeypatch):
    monkeypatch.setenv("WOS_MCP_OPERATING_PROFILE", "degraded")
    names = [d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS]
    ot = build_compact_mcp_operator_truth(
        backend_reachable=True,
        catalog_alignment_ok=True,
        registry_tool_names=names,
    )
    assert ot["operational_state"] == "degraded"
    assert ot["governance_posture"]["write_capable_allowed"] is False


def test_build_compact_mcp_operator_truth_read_only_tools_counted():
    names = [d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS if d.tool_class is McpToolClass.read_only][:3]
    ot = build_compact_mcp_operator_truth(
        backend_reachable=True,
        catalog_alignment_ok=True,
        registry_tool_names=names,
    )
    assert ot["available_vs_deferred"]["tool_classes"]["read_only"] == 3


def test_build_compact_mcp_operator_truth_write_capable_tools_counted():
    names = [d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS if d.tool_class is McpToolClass.write_capable]
    ot = build_compact_mcp_operator_truth(
        backend_reachable=True,
        catalog_alignment_ok=True,
        registry_tool_names=names,
    )
    assert ot["available_vs_deferred"]["tool_classes"]["write_capable"] > 0


def test_build_compact_mcp_operator_truth_deferred_stub_tools():
    # Note: Current test data doesn't have deferred stubs, but the function should count them if present
    ot = build_compact_mcp_operator_truth(
        backend_reachable=True,
        catalog_alignment_ok=True,
        registry_tool_names=[],
    )
    assert ot["available_vs_deferred"]["deferred"] == 0


def test_build_compact_mcp_operator_truth_review_bound_allowed():
    names = [d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS]
    ot = build_compact_mcp_operator_truth(
        backend_reachable=True,
        catalog_alignment_ok=True,
        registry_tool_names=names,
    )
    assert ot["governance_posture"]["review_bound_allowed"] is True
    assert ot["governance_posture"]["read_only_allowed"] is True


# ============================================================================
# Tests for StrEnum class (ImportError path)
# ============================================================================


def test_str_enum_conversion():
    suite = McpSuite.wos_admin
    assert str(suite) == "wos-admin"
    assert suite.value == "wos-admin"


def test_str_enum_comparison():
    suite1 = McpSuite.wos_admin
    suite2 = McpSuite.wos_admin
    assert suite1 == suite2


def test_str_enum_all_values():
    for profile in McpOperatingProfile:
        assert isinstance(str(profile), str)
        assert len(str(profile)) > 0


# ============================================================================
# Tests for constants
# ============================================================================


def test_mcp_suites_all_contains_all_suites():
    assert len(MCP_SUITES_ALL) == len(McpSuite)
    for suite in McpSuite:
        assert suite in MCP_SUITES_ALL


def test_mcp_catalog_capability_names_is_sorted():
    assert list(MCP_CATALOG_CAPABILITY_NAMES) == sorted(MCP_CATALOG_CAPABILITY_NAMES)


def test_auth_constants_are_strings():
    assert isinstance(AUTH_BACKEND_HTTP, str)
    assert isinstance(AUTH_FILESYSTEM_REPO, str)
    assert isinstance(AUTH_AI_STACK_CAPABILITY_CATALOG, str)
    assert isinstance(AUTH_MCP_SURFACE_META, str)


# ============================================================================
# Integration tests
# ============================================================================


def test_all_canonical_descriptors_have_valid_suites():
    for descriptor in CANONICAL_MCP_TOOL_DESCRIPTORS:
        assert descriptor.mcp_suite in MCP_SUITES_ALL


def test_all_canonical_descriptors_have_governance_view():
    for descriptor in CANONICAL_MCP_TOOL_DESCRIPTORS:
        assert isinstance(descriptor.governance, McpToolGovernanceView)
        gv = descriptor.governance
        assert gv.published_vs_draft
        assert gv.canonical_vs_supporting
        assert gv.runtime_safe_vs_internal_only
        assert gv.writers_room_visible_vs_runtime_hidden
        assert gv.reviewable_vs_publishable_posture


def test_profile_and_suite_enum_values_unique():
    profiles = [p.value for p in McpOperatingProfile]
    assert len(profiles) == len(set(profiles))

    suites = [s.value for s in McpSuite]
    assert len(suites) == len(set(suites))


def test_descriptor_to_public_metadata_roundtrip():
    for desc in CANONICAL_MCP_TOOL_DESCRIPTORS[:3]:
        metadata = descriptor_to_public_metadata(desc)
        assert metadata["authority_source"] == desc.authority_source
        assert metadata["tool_class"] == desc.tool_class.value
        assert metadata["implementation_status"] == desc.implementation_status.value
        assert metadata["narrative_mutation_risk"] == desc.narrative_mutation_risk
        assert metadata["mcp_suite"] == desc.mcp_suite.value
