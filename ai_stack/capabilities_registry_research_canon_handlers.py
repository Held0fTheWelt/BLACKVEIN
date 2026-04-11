"""Payload handlers for research/canon capabilities (DS-038) — extracted from impl module."""

from __future__ import annotations

from typing import Any


def research_source_inspect_handler(research_store: Any, payload: dict[str, Any]) -> dict[str, Any]:
    from ai_stack.research_langgraph import inspect_source

    return inspect_source(store=research_store, source_id=str(payload["source_id"]))


def research_aspect_extract_handler(research_store: Any, payload: dict[str, Any]) -> dict[str, Any]:
    from ai_stack.research_langgraph import inspect_source

    source_id = str(payload["source_id"])
    inspected = inspect_source(store=research_store, source_id=source_id)
    if inspected.get("error"):
        return inspected
    return {
        "source_id": source_id,
        "aspects": inspected.get("aspects", []),
    }


def research_claim_list_handler(research_store: Any, payload: dict[str, Any]) -> dict[str, Any]:
    from ai_stack.research_langgraph import list_claims

    return list_claims(store=research_store, work_id=payload.get("work_id"))


def research_run_get_handler(research_store: Any, payload: dict[str, Any]) -> dict[str, Any]:
    from ai_stack.research_langgraph import get_run

    return get_run(store=research_store, run_id=str(payload["run_id"]))


def research_exploration_graph_handler(research_store: Any, payload: dict[str, Any]) -> dict[str, Any]:
    from ai_stack.research_langgraph import exploration_graph

    return exploration_graph(store=research_store, run_id=str(payload["run_id"]))


def canon_issue_inspect_handler(research_store: Any, payload: dict[str, Any]) -> dict[str, Any]:
    from ai_stack.research_langgraph import inspect_canon_issue

    return inspect_canon_issue(store=research_store, module_id=payload.get("module_id"))


def research_explore_handler(research_store: Any, payload: dict[str, Any]) -> dict[str, Any]:
    from ai_stack.research_contract import ExplorationBudget
    from ai_stack.research_langgraph import run_research_pipeline

    budget = ExplorationBudget.from_payload(payload.get("budget", {}))
    run = run_research_pipeline(
        store=research_store,
        work_id=str(payload["work_id"]),
        module_id=str(payload["module_id"]),
        source_inputs=list(payload["source_inputs"]),
        seed_question=str(payload.get("seed_question", "")),
        budget_payload=budget.to_dict(),
        mode="capability_explore",
    )
    return {
        "run_id": run["run_id"],
        "exploration_summary": (run.get("outputs", {}) or {}).get("exploration_summary", {}),
        "effective_budget": budget.to_dict(),
    }


def research_validate_handler(research_store: Any, payload: dict[str, Any]) -> dict[str, Any]:
    from ai_stack.research_langgraph import get_run

    run_id = str(payload["run_id"])
    run = get_run(store=research_store, run_id=run_id)
    if run.get("error"):
        return run
    return {
        "run_id": run_id,
        "claims": ((run.get("run", {}) or {}).get("outputs", {}) or {}).get("claim_ids", []),
        "status": "validated_from_run_outputs",
    }


def research_bundle_build_handler(research_store: Any, payload: dict[str, Any]) -> dict[str, Any]:
    from ai_stack.research_langgraph import build_research_bundle

    return build_research_bundle(store=research_store, run_id=str(payload["run_id"]))


def canon_improvement_propose_handler(research_store: Any, payload: dict[str, Any]) -> dict[str, Any]:
    from ai_stack.research_langgraph import propose_canon_improvement

    return propose_canon_improvement(store=research_store, module_id=str(payload["module_id"]))


def canon_improvement_preview_handler(research_store: Any, payload: dict[str, Any]) -> dict[str, Any]:
    from ai_stack.research_langgraph import preview_canon_improvement

    return preview_canon_improvement(store=research_store, module_id=str(payload["module_id"]))
