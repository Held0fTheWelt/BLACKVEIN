"""MCP resources and prompts — read-only mirrors of stable surfaces (docs/mcp/MVP_SUITE_MAP.md)."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from ai_stack.mcp_canonical_surface import (
    McpSuite,
    build_compact_mcp_operator_truth,
    capability_records_for_mcp,
    verify_catalog_names_alignment,
)
from ai_stack.mcp_static_catalog import MCP_PROMPT_SPECS, MCP_RESOURCE_SPECS

from tools.mcp_server.backend_client import BackendClient
from tools.mcp_server.errors import JsonRpcError
from tools.mcp_server.fs_tools import FileSystemTools


def _json_text(payload: Any) -> str:
    return json.dumps(payload, indent=2, default=str)


def list_resource_descriptors(suite_filter: McpSuite | None) -> list[dict[str, str]]:
    """Static resource catalog for ``resources/list`` (templates use ``{session_id}`` / ``{module_id}`` in URI)."""
    out: list[dict[str, str]] = []
    for uri, name, description, suite in MCP_RESOURCE_SPECS:
        if suite_filter is not None and suite != suite_filter:
            continue
        out.append(
            {
                "uri": uri,
                "name": name,
                "description": description,
                "mimeType": "application/json",
            }
        )
    return out


def list_prompt_descriptors(suite_filter: McpSuite | None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for name, title, description, suite in MCP_PROMPT_SPECS:
        if suite_filter is not None and suite != suite_filter:
            continue
        out.append({"name": name, "description": f"{title}. {description}"})
    return out


_PROMPT_BODIES: dict[str, str] = {
    "wos-admin-session-triage": (
        "1) Read resource `wos://system/health`.\n"
        "2) Read `wos://mcp/operator_truth?probe_backend=true`.\n"
        "3) For the affected backend session, read `wos://session/{session_id}`.\n"
        "4) If world-engine bridge errors appear, escalate with trace_id from the snapshot.\n"
        "Do not use research tools for pure session outages."
    ),
    "wos-runtime-read-trace-review": (
        "Given backend `session_id`:\n"
        "1) `wos://session/{session_id}/diagnostics`\n"
        "2) `wos://session/{session_id}/state`\n"
        "3) `wos://session/{session_id}/logs?limit=200`\n"
        "Compare turn_counter and scene progression across steps."
    ),
    "wos-author-module-spotcheck": (
        "1) `wos://content/modules`\n"
        "2) Pick `module_id`, then `wos://content/module/{module_id}`\n"
        "3) If needed, use tool `wos.content.search` with a tight pattern (author suite).\n"
        "Do not treat filesystem draft as published runtime truth."
    ),
    "wos-ai-research-bundle": (
        "1) `wos.research.explore` with mandatory budget object and source_inputs.\n"
        "2) `wos.research.validate` with run_id.\n"
        "3) `wos.research.bundle.build` with run_id.\n"
        "Canon changes remain review-only; no publish via MCP."
    ),
}


def get_prompt_messages(name: str, suite_filter: McpSuite | None) -> dict[str, Any] | None:
    if name not in _PROMPT_BODIES:
        return None
    suite_by_prompt = {
        "wos-admin-session-triage": McpSuite.wos_admin,
        "wos-runtime-read-trace-review": McpSuite.wos_runtime_read,
        "wos-author-module-spotcheck": McpSuite.wos_author,
        "wos-ai-research-bundle": McpSuite.wos_ai,
    }
    su = suite_by_prompt.get(name)
    if suite_filter is not None and su != suite_filter:
        return None
    body = _PROMPT_BODIES[name]
    return {
        "description": next(
            (p["description"] for p in list_prompt_descriptors(None) if p["name"] == name),
            name,
        ),
        "messages": [{"role": "user", "content": {"type": "text", "text": body}}],
    }


class McpResourceReader:
    """Resolve ``wos://`` URIs to JSON text (same backing as tools, no extra authority)."""

    def __init__(self, backend: BackendClient, fs: FileSystemTools) -> None:
        self._backend = backend
        self._fs = fs

    def read(self, uri: str, trace_id: str) -> tuple[str, str]:
        """Return (mime_type, text). Raises ValueError on unknown or malformed URI."""
        parsed = urlparse(uri)
        if parsed.scheme != "wos":
            raise ValueError("URI scheme must be wos://")

        # ``wos://system/health`` → netloc ``system``, path ``/health`` → ``system/health``
        path = f"{parsed.netloc}{parsed.path}".strip("/")
        qs = parse_qs(parsed.query)
        probe_list = qs.get("probe_backend", ["false"])
        probe_backend = str(probe_list[0]).lower() in ("1", "true", "yes")

        if path == "system/health":
            try:
                data = self._backend.health(trace_id=trace_id)
            except JsonRpcError as e:
                data = {"error": e.message, "code": e.code}
            return "application/json", _json_text(data)

        if path == "mcp/operator_truth":
            backend_reachable: bool | None = None
            if probe_backend:
                try:
                    self._backend.health(trace_id=trace_id)
                    backend_reachable = True
                except JsonRpcError:
                    backend_reachable = False
            align = verify_catalog_names_alignment()
            # Registry names: all canonical tools (suite filter does not shrink truth surface here)
            from ai_stack.mcp_canonical_surface import CANONICAL_MCP_TOOL_DESCRIPTORS

            reg_names = [d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS]
            truth = build_compact_mcp_operator_truth(
                backend_reachable=backend_reachable,
                catalog_alignment_ok=bool(align["aligned"]),
                registry_tool_names=reg_names,
            )
            return "application/json", _json_text({"operator_truth": truth, "catalog_alignment": align})

        if path == "capabilities/catalog":
            return "application/json", _json_text({"capabilities": capability_records_for_mcp()})

        if path == "content/modules":
            return "application/json", _json_text({"modules": self._fs.list_modules()})

        m_mod = re.fullmatch(r"content/module/([^/]+)", path)
        if m_mod:
            mid = m_mod.group(1)
            mod = self._fs.get_module(mid)
            return "application/json", _json_text(mod)

        m_sess = re.fullmatch(r"session/([^/]+)", path)
        if m_sess:
            sid = m_sess.group(1)
            try:
                data = self._backend._get(f"{self._backend.base_url}/api/v1/sessions/{sid}", trace_id)
            except JsonRpcError as e:
                data = {"error": e.message, "code": e.code}
            return "application/json", _json_text(data)

        m_diag = re.fullmatch(r"session/([^/]+)/diagnostics", path)
        if m_diag:
            sid = m_diag.group(1)
            try:
                data = self._backend._get(
                    f"{self._backend.base_url}/api/v1/sessions/{sid}/diagnostics", trace_id
                )
            except JsonRpcError as e:
                data = {"error": e.message, "code": e.code}
            return "application/json", _json_text(data)

        m_state = re.fullmatch(r"session/([^/]+)/state", path)
        if m_state:
            sid = m_state.group(1)
            try:
                data = self._backend._get(f"{self._backend.base_url}/api/v1/sessions/{sid}/state", trace_id)
            except JsonRpcError as e:
                data = {"error": e.message, "code": e.code}
            return "application/json", _json_text(data)

        m_logs = re.fullmatch(r"session/([^/]+)/logs", path)
        if m_logs:
            sid = m_logs.group(1)
            limit_list = qs.get("limit", ["100"])
            try:
                lim = int(limit_list[0])
            except (TypeError, ValueError):
                lim = 100
            try:
                data = self._backend._get(
                    f"{self._backend.base_url}/api/v1/sessions/{sid}/logs?limit={lim}", trace_id
                )
            except JsonRpcError as e:
                data = {"error": e.message, "code": e.code}
            return "application/json", _json_text(data)

        raise ValueError(f"unknown resource URI: {uri}")
