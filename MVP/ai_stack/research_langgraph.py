"""Deterministic research pipeline orchestration (control-flow only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_stack.canon_improvement_engine import derive_canon_improvements
from ai_stack.research_aspect_extraction import extract_and_store_aspects
from ai_stack.research_contract import ExplorationBudget, ResearchRunRecord, ResearchStatus, utc_now_iso
from ai_stack.research_exploration import run_bounded_exploration
from ai_stack.research_ingestion import ingest_resource, normalize_resource
from ai_stack.research_store import ResearchStore
from ai_stack.research_validation import evaluate_candidate_from_exploration_node, verify_and_promote_claims


def _review_safe_flag(*, claims: list[dict[str, Any]], exploration_summary: dict[str, Any]) -> bool:
    if any(str(claim.get("contradiction_status", "")) == "hard_conflict" for claim in claims):
        return False
    if any(not claim.get("evidence_anchor_ids") for claim in claims):
        return False
    abort_reason = str(exploration_summary.get("abort_reason", ""))
    unsafe_abort_reasons = {"token_budget_exhausted", "llm_budget_exhausted", "time_budget_exhausted"}
    if abort_reason in unsafe_abort_reasons:
        return False
    return True


def _canon_relevance_hint(node: dict[str, Any]) -> bool:
    hypothesis = str(node.get("hypothesis", "")).lower()
    return "improvement_probe" in hypothesis or "tension_probe" in hypothesis


def build_review_bundle(
    *,
    run_id: str,
    work_id: str,
    module_id: str,
    sources: list[dict[str, Any]],
    anchors: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    proposals: list[dict[str, Any]],
    exploration_summary: dict[str, Any],
) -> dict[str, Any]:
    contradiction_summary: dict[str, int] = {}
    for claim in claims:
        key = str(claim.get("contradiction_status", "none"))
        contradiction_summary[key] = contradiction_summary.get(key, 0) + 1
    status_summary: dict[str, int] = {}
    for claim in claims:
        key = str(claim.get("status", "unknown"))
        status_summary[key] = status_summary.get(key, 0) + 1
    review_safe = _review_safe_flag(claims=claims, exploration_summary=exploration_summary)
    perspective_summary: dict[str, int] = {}
    for aspect in aspects:
        perspective = str(aspect.get("perspective", "unknown"))
        perspective_summary[perspective] = perspective_summary.get(perspective, 0) + 1
    return {
        "bundle_schema_version": "research_review_bundle_v1",
        "run_id": run_id,
        "work_id": work_id,
        "module_id": module_id,
        "sections": [
            "intake",
            "aspects",
            "exploration",
            "verification",
            "canon_improvement",
            "governance",
        ],
        "intake": {
            "source_count": len(sources),
            "anchor_count": len(anchors),
            "source_ids": sorted([str(s.get("source_id", "")) for s in sources]),
        },
        "aspects": {
            "perspective_summary": perspective_summary,
            "aspect_count": len(aspects),
            "source_ids_with_aspects": sorted({str(a.get("source_id", "")) for a in aspects if a.get("source_id")}),
        },
        "exploration": dict(exploration_summary),
        "verification": {
            "claim_count": len(claims),
            "status_summary": status_summary,
            "contradiction_summary": contradiction_summary,
        },
        "canon_improvement": {
            "issue_count": len(issues),
            "proposal_count": len(proposals),
            "proposal_types": sorted({str(p.get("proposal_type", "")) for p in proposals}),
        },
        "governance": {
            "review_safe": review_safe,
            "canon_mutation_permitted": False,
            "silent_mutation_blocked": True,
        },
    }


def run_research_pipeline(
    *,
    store: ResearchStore,
    work_id: str,
    module_id: str,
    source_inputs: list[dict[str, Any]],
    seed_question: str,
    budget_payload: dict[str, Any],
    mode: str = "research_full",
    audit_refs: list[str] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    budget = ExplorationBudget.from_payload(budget_payload)
    run_identifier = run_id or store.next_id("run")

    intake_sources: list[dict[str, Any]] = []
    all_segments: list[dict[str, Any]] = []
    all_anchors: list[dict[str, Any]] = []
    for source_input in source_inputs:
        normalized = normalize_resource(
            work_id=work_id,
            source_type=str(source_input.get("source_type", "note")),
            title=str(source_input.get("title", "untitled")),
            raw_text=str(source_input.get("raw_text", "")),
            provenance=dict(source_input.get("provenance", {})),
            visibility=str(source_input.get("visibility", "internal")),
            copyright_posture=source_input.get("copyright_posture"),
            metadata=dict(source_input.get("metadata", {})),
        )
        intake = ingest_resource(store=store, normalized_source=normalized)
        intake_sources.append(intake["source"])
        all_segments.extend(intake["segments"])
        all_anchors.extend(intake["anchors"])

    aspects: list[dict[str, Any]] = []
    for source in intake_sources:
        source_id = str(source["source_id"])
        source_segments = [s for s in all_segments if s.get("source_id") == source_id and s.get("segment_ref")]
        aspects.extend(extract_and_store_aspects(store=store, source_id=source_id, segments=source_segments))

    exploration_result = run_bounded_exploration(seed_aspects=aspects, budget=budget)
    for node in exploration_result.nodes:
        store.upsert_exploration_node(node)
    for edge in exploration_result.edges:
        store.upsert_exploration_edge(edge)

    candidate_payloads: list[dict[str, Any]] = []
    for node in exploration_result.nodes:
        is_candidate, reason = evaluate_candidate_from_exploration_node(node)
        if not is_candidate:
            continue
        candidate_payloads.append(
            {
                "claim_type": "improvement_lead",
                "statement": node.get("hypothesis"),
                "evidence_anchor_ids": list(node.get("evidence_anchor_ids", [])),
                "perspective": node.get("perspective"),
                "notes": reason,
                "canon_relevance_hint": _canon_relevance_hint(node),
            }
        )

    verified = verify_and_promote_claims(
        store=store,
        work_id=work_id,
        candidate_payloads=candidate_payloads,
    )
    claims = verified["claims"]

    improvement = derive_canon_improvements(store=store, module_id=module_id, claims=claims)
    issues = improvement["issues"]
    proposals = improvement["proposals"]

    exploration_summary = {
        "abort_reason": exploration_result.abort_reason,
        "node_count": len(exploration_result.nodes),
        "edge_count": len(exploration_result.edges),
        "promoted_candidate_count": exploration_result.promoted_candidate_count,
        "rejected_branch_count": exploration_result.rejected_branch_count,
        "unresolved_branch_count": exploration_result.unresolved_branch_count,
        "pruned_branch_count": exploration_result.pruned_branch_count,
        "consumed_budget": exploration_result.consumed_budget,
        "effective_budget": budget.to_dict(),
    }
    bundle = build_review_bundle(
        run_id=run_identifier,
        work_id=work_id,
        module_id=module_id,
        sources=intake_sources,
        anchors=all_anchors,
        aspects=aspects,
        claims=claims,
        issues=issues,
        proposals=proposals,
        exploration_summary=exploration_summary,
    )

    run_record = ResearchRunRecord(
        run_id=run_identifier,
        mode=mode,
        source_ids=sorted([str(s.get("source_id", "")) for s in intake_sources]),
        seed_question=seed_question,
        budget=budget.to_dict(),
        outputs={
            "source_ids": sorted([str(s.get("source_id", "")) for s in intake_sources]),
            "aspect_ids": sorted([str(a.get("aspect_id", "")) for a in aspects]),
            "exploration_node_ids": sorted([str(n.get("node_id", "")) for n in exploration_result.nodes]),
            "claim_ids": sorted([str(c.get("claim_id", "")) for c in claims]),
            "issue_ids": sorted([str(i.get("issue_id", "")) for i in issues]),
            "proposal_ids": sorted([str(p.get("proposal_id", "")) for p in proposals]),
            "bundle": bundle,
            "exploration_summary": exploration_summary,
        },
        audit_refs=list(audit_refs or []),
        created_at=utc_now_iso(),
    ).to_dict()
    stored_run = store.upsert_run(run_record)
    return stored_run


def research_store_from_repo_root(repo_root: Path) -> ResearchStore:
    return ResearchStore.from_repo_root(repo_root)


def inspect_source(*, store: ResearchStore, source_id: str) -> dict[str, Any]:
    source = store.get_source(source_id)
    if source is None:
        return {"error": "source_not_found", "source_id": source_id}
    anchors = [a for a in store.list_anchors() if a.get("source_id") == source_id]
    aspects = [a for a in store.list_aspects() if a.get("source_id") == source_id]
    return {
        "source": source,
        "anchors": sorted(anchors, key=lambda row: row["anchor_id"]),
        "aspects": sorted(aspects, key=lambda row: row["aspect_id"]),
    }


def list_claims(*, store: ResearchStore, work_id: str | None = None) -> dict[str, Any]:
    claims = store.list_claims()
    if work_id:
        claims = [c for c in claims if c.get("work_id") == work_id]
    return {"claims": claims}


def get_run(*, store: ResearchStore, run_id: str) -> dict[str, Any]:
    run = store.get_run(run_id)
    if run is None:
        return {"error": "run_not_found", "run_id": run_id}
    return {"run": run}


def exploration_graph(*, store: ResearchStore, run_id: str) -> dict[str, Any]:
    run = store.get_run(run_id)
    if run is None:
        return {"error": "run_not_found", "run_id": run_id}
    outputs = run.get("outputs", {})
    node_ids = set(outputs.get("exploration_node_ids", []))
    nodes = [row for row in store.list_exploration_nodes() if row.get("node_id") in node_ids]
    edges = [
        row
        for row in store.list_exploration_edges()
        if row.get("from_node_id") in node_ids and row.get("to_node_id") in node_ids
    ]
    return {
        "run_id": run_id,
        "nodes": sorted(nodes, key=lambda row: row["node_id"]),
        "edges": sorted(edges, key=lambda row: row["edge_id"]),
    }


def inspect_canon_issue(*, store: ResearchStore, module_id: str | None = None) -> dict[str, Any]:
    issues = store.list_issues()
    if module_id:
        issues = [i for i in issues if i.get("module_id") == module_id]
    return {"issues": issues}


def build_research_bundle(*, store: ResearchStore, run_id: str) -> dict[str, Any]:
    run = store.get_run(run_id)
    if run is None:
        return {"error": "run_not_found", "run_id": run_id}
    outputs = run.get("outputs", {})
    bundle = outputs.get("bundle")
    if not isinstance(bundle, dict):
        return {"error": "bundle_missing", "run_id": run_id}
    return {"bundle": bundle}


def propose_canon_improvement(*, store: ResearchStore, module_id: str) -> dict[str, Any]:
    claims = [c for c in store.list_claims() if c.get("status") == ResearchStatus.CANON_APPLICABLE.value]
    result = derive_canon_improvements(store=store, module_id=module_id, claims=claims)
    return result


def preview_canon_improvement(*, store: ResearchStore, module_id: str) -> dict[str, Any]:
    proposals = [p for p in store.list_proposals() if p.get("module_id") == module_id]
    return {
        "module_id": module_id,
        "preview": [
            {
                "proposal_id": row.get("proposal_id"),
                "proposal_type": row.get("proposal_type"),
                "preview_patch_ref": row.get("preview_patch_ref"),
                "mutation_allowed": False,
            }
            for row in sorted(proposals, key=lambda p: str(p.get("proposal_id", "")))
        ],
    }
