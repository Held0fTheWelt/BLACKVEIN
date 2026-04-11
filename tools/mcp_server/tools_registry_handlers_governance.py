"""MCP handlers for capability catalog and operator-facing truth surfaces."""

from __future__ import annotations

from typing import Any, Callable

from ai_stack.mcp_canonical_surface import (
    build_compact_mcp_operator_truth,
    capability_records_for_mcp,
    verify_catalog_names_alignment,
)
from tools.mcp_server.backend_client import BackendClient
from tools.mcp_server.errors import JsonRpcError
from tools.mcp_server.tools_registry_handlers_protocol import RegistryListToolNames


def build_governance_mcp_handlers(
    backend: BackendClient,
    registry: RegistryListToolNames,
) -> dict[str, Callable[..., dict[str, Any]]]:
    def handle_capability_catalog(arguments: dict[str, Any]) -> dict[str, Any]:
        return {"capabilities": capability_records_for_mcp()}

    def handle_operator_truth(arguments: dict[str, Any]) -> dict[str, Any]:
        probe = bool(arguments.get("probe_backend"))
        backend_reachable: bool | None = None
        if probe:
            try:
                import uuid

                backend.health(trace_id=str(uuid.uuid4()))
                backend_reachable = True
            except JsonRpcError:
                backend_reachable = False
        align = verify_catalog_names_alignment()
        truth = build_compact_mcp_operator_truth(
            backend_reachable=backend_reachable,
            catalog_alignment_ok=bool(align["aligned"]),
            registry_tool_names=registry.list_tool_names(),
        )
        return {"operator_truth": truth, "catalog_alignment": align}

    return {
        "wos.capabilities.catalog": handle_capability_catalog,
        "wos.mcp.operator_truth": handle_operator_truth,
    }
