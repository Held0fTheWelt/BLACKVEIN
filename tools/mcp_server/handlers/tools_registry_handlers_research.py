"""MCP handlers for research store and canon improvement tools."""

from __future__ import annotations

from typing import Any, Callable

from tools.mcp_server.research_mcp_handler_factories import (
    make_handle_canon_improvement_preview,
    make_handle_canon_improvement_propose,
    make_handle_canon_issue_inspect,
    make_handle_research_aspect_extract,
    make_handle_research_bundle_build,
    make_handle_research_claim_list,
    make_handle_research_exploration_graph,
    make_handle_research_explore,
    make_handle_research_run_get,
    make_handle_research_source_inspect,
    make_handle_research_validate,
)


def build_research_mcp_handlers(
    research_store: Any,
) -> dict[str, Callable[..., dict[str, Any]]]:
    return {
        "wos.research.source.inspect": make_handle_research_source_inspect(research_store),
        "wos.research.aspect.extract": make_handle_research_aspect_extract(research_store),
        "wos.research.claim.list": make_handle_research_claim_list(research_store),
        "wos.research.run.get": make_handle_research_run_get(research_store),
        "wos.research.exploration.graph": make_handle_research_exploration_graph(research_store),
        "wos.canon.issue.inspect": make_handle_canon_issue_inspect(research_store),
        "wos.research.explore": make_handle_research_explore(research_store),
        "wos.research.validate": make_handle_research_validate(research_store),
        "wos.research.bundle.build": make_handle_research_bundle_build(research_store),
        "wos.canon.improvement.propose": make_handle_canon_improvement_propose(research_store),
        "wos.canon.improvement.preview": make_handle_canon_improvement_preview(research_store),
    }
