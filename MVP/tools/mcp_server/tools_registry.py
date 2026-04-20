"""Tool registry and metadata — derived from ai_stack canonical MCP descriptors."""

from typing import Any, Callable, Optional

from ai_stack.mcp_canonical_surface import (
    CANONICAL_MCP_TOOL_DESCRIPTORS,
    McpCanonicalToolDescriptor,
    McpImplementationStatus,
    build_compact_mcp_operator_truth,
    capability_records_for_mcp,
    descriptor_to_public_metadata,
    verify_catalog_names_alignment,
)
from tools.mcp_server.backend_client import BackendClient
from tools.mcp_server.config import Config
from tools.mcp_server.errors import JsonRpcError
from tools.mcp_server.fs_tools import FileSystemTools


class ToolDefinition:
    """Tool metadata: canonical strand + handler (permission_legacy for older clients)."""

    def __init__(
        self,
        descriptor: McpCanonicalToolDescriptor,
        description: str,
        handler: Callable[..., dict[str, Any]],
        input_schema: dict[str, Any],
    ):
        self.descriptor = descriptor
        self.name = descriptor.name
        self.description = description
        self.handler = handler
        self.input_schema = input_schema
        self.tool_class = descriptor.tool_class
        self.authority_source = descriptor.authority_source
        self.implementation_status = descriptor.implementation_status
        self.permission = descriptor.permission_legacy

    def to_dict(self) -> dict[str, Any]:
        meta = descriptor_to_public_metadata(self.descriptor)
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "permission": self.permission,
            "tool_class": meta["tool_class"],
            "authority_source": meta["authority_source"],
            "implementation_status": meta["implementation_status"],
            "governance": meta["governance"],
            "narrative_mutation_risk": meta["narrative_mutation_risk"],
        }


class ToolRegistry:
    """Central registry of available tools."""

    def __init__(self) -> None:
        self.tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self.tools.get(name)

    def list_tool_names(self) -> list[str]:
        return sorted(self.tools.keys())

    def list_tools(self) -> list[dict[str, Any]]:
        return [tool.to_dict() for tool in self.tools.values()]


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    config = Config()
    backend = BackendClient(base_url=config.backend_url, bearer_token=config.bearer_token)
    fs = FileSystemTools(config)
    from ai_stack.research_contract import ExplorationBudget
    from ai_stack.research_langgraph import (
        build_research_bundle,
        exploration_graph,
        get_run,
        inspect_canon_issue,
        inspect_source,
        list_claims,
        preview_canon_improvement,
        propose_canon_improvement,
        research_store_from_repo_root,
        run_research_pipeline,
    )
    research_store = research_store_from_repo_root(config.repo_root)

    def handle_system_health(arguments: dict) -> dict:
        try:
            import uuid

            trace_id = str(uuid.uuid4())
            result = backend.health(trace_id=trace_id)
            return {"status": "healthy", "backend": result}
        except JsonRpcError as e:
            return {"status": "error", "message": e.message}

    def handle_session_create(arguments: dict) -> dict:
        module_id = arguments.get("module_id")
        module_version = arguments.get("module_version")
        try:
            import uuid

            trace_id = str(uuid.uuid4())
            result = backend.create_session(
                module_id=module_id, trace_id=trace_id, module_version=module_version
            )
            return result
        except JsonRpcError as e:
            return {"error": e.message}

    def handle_list_modules(arguments: dict) -> dict:
        return {"modules": fs.list_modules()}

    def handle_get_module(arguments: dict) -> dict:
        module_id = arguments.get("module_id")
        return fs.get_module(module_id)

    def handle_search_content(arguments: dict) -> dict:
        pattern = arguments.get("pattern", "")
        case_sensitive = arguments.get("case_sensitive", False)
        return fs.search_content(pattern, case_sensitive)

    def handle_capability_catalog(arguments: dict) -> dict:
        return {"capabilities": capability_records_for_mcp()}

    def handle_operator_truth(arguments: dict) -> dict:
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

    def handle_session_get(arguments: dict) -> dict:
        """Runtime-safe session snapshot (read-only, authority-respecting)."""
        session_id = arguments.get("session_id")
        if not session_id:
            return {"error": "session_id required"}
        try:
            import uuid
            trace_id = str(uuid.uuid4())
            # Call backend's session endpoint (authority-respecting, read-only)
            result = backend._get(
                f"{backend.base_url}/api/v1/sessions/{session_id}",
                trace_id
            )
            return result
        except JsonRpcError as e:
            return {"error": e.message}
        except Exception as e:
            return {"error": f"session_get failed: {str(e)}"}

    def handle_session_diag(arguments: dict) -> dict:
        """Runtime-safe session diagnostics (read-only, authority-respecting)."""
        session_id = arguments.get("session_id")
        if not session_id:
            return {"error": "session_id required"}
        try:
            import uuid
            trace_id = str(uuid.uuid4())
            # Call backend's diagnostics endpoint (authority-respecting, read-only)
            result = backend._get(
                f"{backend.base_url}/api/v1/sessions/{session_id}/diagnostics",
                trace_id
            )
            return result
        except JsonRpcError as e:
            return {"error": e.message}
        except Exception as e:
            return {"error": f"session_diag failed: {str(e)}"}

    def handle_session_logs(arguments: dict) -> dict:
        """Session event logs (read-only, authority-respecting, audit surfaces)."""
        session_id = arguments.get("session_id")
        limit = arguments.get("limit", 100)
        if not session_id:
            return {"error": "session_id required"}
        try:
            import uuid
            trace_id = str(uuid.uuid4())
            # Call backend's session logs endpoint (authority-respecting, read-only)
            result = backend._get(
                f"{backend.base_url}/api/v1/sessions/{session_id}/logs?limit={limit}",
                trace_id
            )
            return result
        except JsonRpcError as e:
            return {"error": e.message}
        except Exception as e:
            return {"error": f"session_logs failed: {str(e)}"}

    def handle_session_state(arguments: dict) -> dict:
        """Session state snapshot (read-only, authority-respecting, runtime state machine)."""
        session_id = arguments.get("session_id")
        if not session_id:
            return {"error": "session_id required"}
        try:
            import uuid
            trace_id = str(uuid.uuid4())
            # Call backend's session state endpoint (authority-respecting, read-only)
            result = backend._get(
                f"{backend.base_url}/api/v1/sessions/{session_id}/state",
                trace_id
            )
            return result
        except JsonRpcError as e:
            return {"error": e.message}
        except Exception as e:
            return {"error": f"session_state failed: {str(e)}"}

    def handle_session_execute_turn(arguments: dict) -> dict:
        """Execute turn in session (review-bound, authority-required from runtime)."""
        session_id = arguments.get("session_id")
        prompt = arguments.get("prompt")
        if not session_id:
            return {"error": "session_id required"}
        if not prompt:
            return {"error": "prompt required"}
        try:
            import uuid
            trace_id = str(uuid.uuid4())
            # Call backend's session turn execution endpoint (authority-required)
            result = backend._post(
                f"{backend.base_url}/api/v1/sessions/{session_id}/execute_turn",
                {"prompt": prompt},
                trace_id
            )
            return result
        except JsonRpcError as e:
            return {"error": e.message}
        except Exception as e:
            return {"error": f"session_execute_turn failed: {str(e)}"}

    def handle_research_source_inspect(arguments: dict) -> dict:
        source_id = arguments.get("source_id")
        if not source_id:
            return {"error": "source_id required"}
        return inspect_source(store=research_store, source_id=str(source_id))

    def handle_research_aspect_extract(arguments: dict) -> dict:
        source_id = arguments.get("source_id")
        if not source_id:
            return {"error": "source_id required"}
        inspected = inspect_source(store=research_store, source_id=str(source_id))
        if inspected.get("error"):
            return inspected
        return {"source_id": str(source_id), "aspects": inspected.get("aspects", [])}

    def handle_research_claim_list(arguments: dict) -> dict:
        return list_claims(store=research_store, work_id=arguments.get("work_id"))

    def handle_research_run_get(arguments: dict) -> dict:
        run_id = arguments.get("run_id")
        if not run_id:
            return {"error": "run_id required"}
        return get_run(store=research_store, run_id=str(run_id))

    def handle_research_exploration_graph(arguments: dict) -> dict:
        run_id = arguments.get("run_id")
        if not run_id:
            return {"error": "run_id required"}
        return exploration_graph(store=research_store, run_id=str(run_id))

    def handle_canon_issue_inspect(arguments: dict) -> dict:
        return inspect_canon_issue(store=research_store, module_id=arguments.get("module_id"))

    def handle_research_explore(arguments: dict) -> dict:
        # Hard MCP-level budget enforcement.
        budget_payload = arguments.get("budget")
        if not isinstance(budget_payload, dict):
            return {"error": "budget object required"}
        try:
            budget = ExplorationBudget.from_payload(budget_payload)
        except ValueError as exc:
            return {"error": str(exc)}
        source_inputs = arguments.get("source_inputs")
        if not isinstance(source_inputs, list) or not source_inputs:
            return {"error": "source_inputs must be a non-empty array"}
        work_id = arguments.get("work_id")
        module_id = arguments.get("module_id")
        if not isinstance(work_id, str) or not work_id.strip():
            return {"error": "work_id required"}
        if not isinstance(module_id, str) or not module_id.strip():
            return {"error": "module_id required"}
        run = run_research_pipeline(
            store=research_store,
            work_id=work_id,
            module_id=module_id,
            source_inputs=source_inputs,
            seed_question=str(arguments.get("seed_question") or ""),
            budget_payload=budget.to_dict(),
            mode="mcp_research_explore",
        )
        return {
            "run_id": run["run_id"],
            "effective_budget": budget.to_dict(),
            "exploration_summary": (run.get("outputs", {}) or {}).get("exploration_summary", {}),
        }

    def handle_research_validate(arguments: dict) -> dict:
        run_id = arguments.get("run_id")
        if not run_id:
            return {"error": "run_id required"}
        run = get_run(store=research_store, run_id=str(run_id))
        if run.get("error"):
            return run
        run_payload = run.get("run", {})
        outputs = run_payload.get("outputs", {}) if isinstance(run_payload, dict) else {}
        return {
            "run_id": run_id,
            "claim_ids": outputs.get("claim_ids", []),
            "status": "validated_from_run_outputs",
        }

    def handle_research_bundle_build(arguments: dict) -> dict:
        run_id = arguments.get("run_id")
        if not run_id:
            return {"error": "run_id required"}
        return build_research_bundle(store=research_store, run_id=str(run_id))

    def handle_canon_improvement_propose(arguments: dict) -> dict:
        module_id = arguments.get("module_id")
        if not module_id:
            return {"error": "module_id required"}
        return propose_canon_improvement(store=research_store, module_id=str(module_id))

    def handle_canon_improvement_preview(arguments: dict) -> dict:
        module_id = arguments.get("module_id")
        if not module_id:
            return {"error": "module_id required"}
        return preview_canon_improvement(store=research_store, module_id=str(module_id))

    def handle_blocked(name: str) -> Callable[[dict], dict]:
        def handler(arguments: dict) -> dict:
            return {
                "code": "NOT_IMPLEMENTED",
                "reason": f"{name} is not available in this phase",
                "implementation_status": McpImplementationStatus.deferred_stub.value,
                "authority_note": "deferred_stub_non_authoritative",
            }

        return handler

    handlers: dict[str, Callable[..., dict[str, Any]]] = {
        "wos.system.health": handle_system_health,
        "wos.session.create": handle_session_create,
        "wos.goc.list_modules": handle_list_modules,
        "wos.goc.get_module": handle_get_module,
        "wos.content.search": handle_search_content,
        "wos.capabilities.catalog": handle_capability_catalog,
        "wos.mcp.operator_truth": handle_operator_truth,
        "wos.session.get": handle_session_get,
        "wos.session.logs": handle_session_logs,
        "wos.session.state": handle_session_state,
        "wos.session.execute_turn": handle_session_execute_turn,
        "wos.session.diag": handle_session_diag,
        "wos.research.source.inspect": handle_research_source_inspect,
        "wos.research.aspect.extract": handle_research_aspect_extract,
        "wos.research.claim.list": handle_research_claim_list,
        "wos.research.run.get": handle_research_run_get,
        "wos.research.exploration.graph": handle_research_exploration_graph,
        "wos.canon.issue.inspect": handle_canon_issue_inspect,
        "wos.research.explore": handle_research_explore,
        "wos.research.validate": handle_research_validate,
        "wos.research.bundle.build": handle_research_bundle_build,
        "wos.canon.improvement.propose": handle_canon_improvement_propose,
        "wos.canon.improvement.preview": handle_canon_improvement_preview,
    }

    descriptions: dict[str, str] = {
        "wos.system.health": "Check backend system health status",
        "wos.session.create": "Create a new session for a module (authority-respecting backend flow only)",
        "wos.goc.list_modules": "List available modules",
        "wos.goc.get_module": "Get module metadata and file list",
        "wos.content.search": "Search content with regex pattern",
        "wos.capabilities.catalog": "Canonical capability surface with governance metadata (read-only mirror)",
        "wos.mcp.operator_truth": "Compact MCP operator truth (profile, route, policy, no-eligible discipline)",
        "wos.session.get": "Session snapshot (read-only, authority-respecting backend mirror)",
        "wos.session.execute_turn": "Execute turn in session (review-bound, authority-required from runtime)",
        "wos.session.logs": "Session event logs (read-only, authority-respecting audit surfaces)",
        "wos.session.state": "Session state snapshot (read-only, authority-respecting runtime state machine)",
        "wos.session.diag": "Session diagnostics (read-only, authority-respecting backend mirror)",
        "wos.research.source.inspect": "Inspect normalized research source with anchors and aspects",
        "wos.research.aspect.extract": "Read extracted aspect records for a source",
        "wos.research.claim.list": "List structured research claims",
        "wos.research.run.get": "Get one research run with deterministic outputs",
        "wos.research.exploration.graph": "Get exploration graph for one run",
        "wos.canon.issue.inspect": "Inspect structured canon issues",
        "wos.research.explore": "Run bounded research exploration with mandatory budget",
        "wos.research.validate": "Validate research run claims in review-bound mode",
        "wos.research.bundle.build": "Build review-safe research bundle from run output",
        "wos.canon.improvement.propose": "Generate taxonomy-bound canon improvement proposals",
        "wos.canon.improvement.preview": "Preview generated canon improvement proposals",
    }

    schemas: dict[str, dict[str, Any]] = {
        "wos.system.health": {"type": "object", "properties": {}, "required": []},
        "wos.session.create": {
            "type": "object",
            "properties": {
                "module_id": {"type": "string"},
                "module_version": {"type": "string"},
            },
            "required": ["module_id"],
        },
        "wos.goc.list_modules": {"type": "object", "properties": {}, "required": []},
        "wos.goc.get_module": {
            "type": "object",
            "properties": {"module_id": {"type": "string"}},
            "required": ["module_id"],
        },
        "wos.content.search": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "case_sensitive": {"type": "boolean"},
            },
            "required": ["pattern"],
        },
        "wos.capabilities.catalog": {"type": "object", "properties": {}, "required": []},
        "wos.mcp.operator_truth": {
            "type": "object",
            "properties": {"probe_backend": {"type": "boolean"}},
            "required": [],
        },
        "wos.session.diag": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        "wos.session.get": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        "wos.session.logs": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["session_id"],
        },
        "wos.session.state": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        "wos.session.execute_turn": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "prompt": {"type": "string"},
            },
            "required": ["session_id"],
        },
        "wos.research.source.inspect": {
            "type": "object",
            "properties": {"source_id": {"type": "string"}},
            "required": ["source_id"],
        },
        "wos.research.aspect.extract": {
            "type": "object",
            "properties": {"source_id": {"type": "string"}},
            "required": ["source_id"],
        },
        "wos.research.claim.list": {
            "type": "object",
            "properties": {"work_id": {"type": "string"}},
            "required": [],
        },
        "wos.research.run.get": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
        "wos.research.exploration.graph": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
        "wos.canon.issue.inspect": {
            "type": "object",
            "properties": {"module_id": {"type": "string"}},
            "required": [],
        },
        "wos.research.explore": {
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
        "wos.research.validate": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
        "wos.research.bundle.build": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
        "wos.canon.improvement.propose": {
            "type": "object",
            "properties": {"module_id": {"type": "string"}},
            "required": ["module_id"],
        },
        "wos.canon.improvement.preview": {
            "type": "object",
            "properties": {"module_id": {"type": "string"}},
            "required": ["module_id"],
        },
    }

    for desc in CANONICAL_MCP_TOOL_DESCRIPTORS:
        name = desc.name
        if name in handlers:
            handler_fn = handlers[name]
        else:
            handler_fn = handle_blocked(name)
        registry.register(
            ToolDefinition(
                descriptor=desc,
                description=descriptions.get(name, name),
                handler=handler_fn,
                input_schema=schemas.get(name, {"type": "object", "properties": {}, "required": []}),
            )
        )

    return registry
