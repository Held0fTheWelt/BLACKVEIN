"""Wire-format alias layer for MCP tool names.

Cursor's MCP host filters tool names against ``^[A-Za-z0-9_]+$``. The canonical
descriptor names use dotted notation (``wos.system.health``) for governance
parity with M1 docs / ADRs / suite map. The registry preserves that canonical
identity but emits a Cursor-safe wire form (``wos_system_health``) in
``tools/list`` and accepts BOTH forms in ``tools/call``.

These tests pin that contract.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from ai_stack.mcp.mcp_canonical_surface import (
    CANONICAL_MCP_TOOL_DESCRIPTORS,
    McpCanonicalToolDescriptor,
    McpImplementationStatus,
    McpSuite,
    McpToolClass,
    McpToolGovernanceView,
)
from tools.mcp_server.tools_registry import (
    CURSOR_SAFE_TOOL_NAME_RE,
    ToolDefinition,
    ToolRegistry,
    create_default_registry,
    cursor_safe_name,
)


def _make_descriptor(name: str) -> McpCanonicalToolDescriptor:
    """Build a minimal canonical descriptor for registry-shape tests."""
    return McpCanonicalToolDescriptor(
        name=name,
        tool_class=McpToolClass.read_only,
        authority_source="mcp_surface_meta",
        implementation_status=McpImplementationStatus.implemented,
        permission_scope="read",
        narrative_mutation_risk="none_read_only",
        governance=McpToolGovernanceView(
            published_vs_draft="published",
            canonical_vs_supporting="canonical",
            runtime_safe_vs_internal_only="runtime_safe",
            writers_room_visible_vs_runtime_hidden="runtime_focused",
            reviewable_vs_publishable_posture="read_only_no_review_path",
        ),
        mcp_suite=McpSuite.wos_admin,
    )


def _make_tool(name: str, *, calls: list[dict[str, Any]] | None = None) -> ToolDefinition:
    sink: list[dict[str, Any]] = calls if calls is not None else []

    def _handler(arguments: dict[str, Any]) -> dict[str, Any]:
        sink.append(dict(arguments))
        return {"ok": True, "echo": arguments}

    return ToolDefinition(
        descriptor=_make_descriptor(name),
        description=f"fake tool {name}",
        handler=_handler,
        input_schema={"type": "object", "properties": {}, "required": []},
    )


# --- pure helper -------------------------------------------------------------


def test_cursor_safe_name_replaces_dots_with_underscores():
    assert cursor_safe_name("wos.system.health") == "wos_system_health"
    assert cursor_safe_name("wos.research.exploration.graph") == "wos_research_exploration_graph"


def test_cursor_safe_name_passes_through_already_safe_names():
    for n in ("run_projection_tests", "fetch_langfuse_trace", "build_opening_quality_context"):
        assert cursor_safe_name(n) == n


def test_cursor_safe_name_is_bijective_over_canonical_descriptors():
    """No two canonical names collapse to the same wire form. If this ever
    fires, two canonical names differ only in ``.`` vs ``_`` placement and
    the alias map can't disambiguate them safely."""
    safe = [cursor_safe_name(d.name) for d in CANONICAL_MCP_TOOL_DESCRIPTORS]
    assert len(set(safe)) == len(safe), (
        f"cursor_safe_name collisions: "
        f"{sorted({n for n in safe if safe.count(n) > 1})}"
    )


def test_cursor_safe_name_matches_mcp_regex():
    """Every emitted wire-form name must satisfy Cursor's tool-name regex."""
    for d in CANONICAL_MCP_TOOL_DESCRIPTORS:
        emitted = cursor_safe_name(d.name)
        assert CURSOR_SAFE_TOOL_NAME_RE.match(emitted), (
            f"canonical {d.name!r} -> wire {emitted!r} fails ^[A-Za-z0-9_]+$"
        )
        assert re.match(r"^[A-Za-z0-9_]+$", emitted)


# --- registry alias resolution -----------------------------------------------


def test_tools_call_accepts_canonical_dotted_form():
    registry = ToolRegistry()
    calls: list[dict[str, Any]] = []
    registry.register(_make_tool("wos.system.health", calls=calls))

    tool = registry.get("wos.system.health")
    assert tool is not None
    result = tool.handler({"probe": True})
    assert result == {"ok": True, "echo": {"probe": True}}
    assert calls == [{"probe": True}]


def test_tools_call_accepts_cursor_safe_underscored_form():
    registry = ToolRegistry()
    calls: list[dict[str, Any]] = []
    registry.register(_make_tool("wos.system.health", calls=calls))

    tool = registry.get("wos_system_health")
    assert tool is not None
    assert tool.name == "wos.system.health", (
        "alias resolution must return the canonical entry, not a copy"
    )
    result = tool.handler({"probe": True})
    assert result == {"ok": True, "echo": {"probe": True}}
    assert calls == [{"probe": True}]


def test_tools_call_returns_none_for_unknown_name():
    registry = ToolRegistry()
    registry.register(_make_tool("wos.system.health"))
    assert registry.get("definitely_not_a_tool") is None


def test_register_collision_on_alias_raises_value_error():
    """If two canonical names ever collapse to the same wire form, the second
    register() must fail loudly rather than silently shadow the first."""
    registry = ToolRegistry()
    registry.register(_make_tool("wos.foo.bar"))
    with pytest.raises(ValueError, match="alias collision"):
        registry.register(_make_tool("wos.foo_bar"))


def test_already_safe_name_does_not_create_alias_entry():
    """Names that already satisfy the regex must not pollute the alias map."""
    registry = ToolRegistry()
    registry.register(_make_tool("run_projection_tests"))
    assert "run_projection_tests" in registry.tools
    assert "run_projection_tests" not in registry.aliases


# --- to_dict shape -----------------------------------------------------------


def test_to_dict_emits_underscored_name_and_canonical_name_field():
    tool = _make_tool("wos.system.health")
    payload = tool.to_dict()
    assert payload["name"] == "wos_system_health"
    assert payload["canonical_name"] == "wos.system.health"


def test_to_dict_for_already_safe_name_repeats_canonical():
    tool = _make_tool("run_projection_tests")
    payload = tool.to_dict()
    assert payload["name"] == "run_projection_tests"
    assert payload["canonical_name"] == "run_projection_tests"


# --- end-to-end with default registry ----------------------------------------


def test_default_registry_lists_only_cursor_safe_names():
    registry = create_default_registry()
    tools = registry.list_tools()
    for t in tools:
        assert CURSOR_SAFE_TOOL_NAME_RE.match(t["name"]), (
            f"emitted name {t['name']!r} (canonical {t.get('canonical_name')!r}) "
            f"fails Cursor regex"
        )


def test_default_registry_canonical_names_resolve_via_dotted_or_underscored():
    """Every canonical descriptor must be reachable via both supported wire forms."""
    registry = create_default_registry()
    for desc in CANONICAL_MCP_TOOL_DESCRIPTORS:
        canonical = desc.name
        underscored = cursor_safe_name(canonical)
        assert registry.get(canonical) is not None, f"missing dotted {canonical}"
        assert registry.get(underscored) is not None, f"missing wire {underscored}"
        assert registry.get(canonical) is registry.get(underscored), (
            f"dotted and underscored forms resolve to different entries for {canonical}"
        )
