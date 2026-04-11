"""MCP handlers for research store and canon improvement tools."""

from __future__ import annotations

from typing import Any, Callable


def build_research_mcp_handlers(
    research_store: Any,
) -> dict[str, Callable[..., dict[str, Any]]]:
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
        run_research_pipeline,
    )

    def handle_research_source_inspect(arguments: dict[str, Any]) -> dict[str, Any]:
        source_id = arguments.get("source_id")
        if not source_id:
            return {"error": "source_id required"}
        return inspect_source(store=research_store, source_id=str(source_id))

    def handle_research_aspect_extract(arguments: dict[str, Any]) -> dict[str, Any]:
        source_id = arguments.get("source_id")
        if not source_id:
            return {"error": "source_id required"}
        inspected = inspect_source(store=research_store, source_id=str(source_id))
        if inspected.get("error"):
            return inspected
        return {"source_id": str(source_id), "aspects": inspected.get("aspects", [])}

    def handle_research_claim_list(arguments: dict[str, Any]) -> dict[str, Any]:
        return list_claims(store=research_store, work_id=arguments.get("work_id"))

    def handle_research_run_get(arguments: dict[str, Any]) -> dict[str, Any]:
        run_id = arguments.get("run_id")
        if not run_id:
            return {"error": "run_id required"}
        return get_run(store=research_store, run_id=str(run_id))

    def handle_research_exploration_graph(arguments: dict[str, Any]) -> dict[str, Any]:
        run_id = arguments.get("run_id")
        if not run_id:
            return {"error": "run_id required"}
        return exploration_graph(store=research_store, run_id=str(run_id))

    def handle_canon_issue_inspect(arguments: dict[str, Any]) -> dict[str, Any]:
        return inspect_canon_issue(store=research_store, module_id=arguments.get("module_id"))

    def handle_research_explore(arguments: dict[str, Any]) -> dict[str, Any]:
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

    def handle_research_validate(arguments: dict[str, Any]) -> dict[str, Any]:
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

    def handle_research_bundle_build(arguments: dict[str, Any]) -> dict[str, Any]:
        run_id = arguments.get("run_id")
        if not run_id:
            return {"error": "run_id required"}
        return build_research_bundle(store=research_store, run_id=str(run_id))

    def handle_canon_improvement_propose(arguments: dict[str, Any]) -> dict[str, Any]:
        module_id = arguments.get("module_id")
        if not module_id:
            return {"error": "module_id required"}
        return propose_canon_improvement(store=research_store, module_id=str(module_id))

    def handle_canon_improvement_preview(arguments: dict[str, Any]) -> dict[str, Any]:
        module_id = arguments.get("module_id")
        if not module_id:
            return {"error": "module_id required"}
        return preview_canon_improvement(store=research_store, module_id=str(module_id))

    return {
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
