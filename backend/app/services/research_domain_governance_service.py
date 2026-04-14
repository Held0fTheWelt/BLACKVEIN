"""
Strategic research-domain visibility for administration-tool and APIs.

This module encodes a **layered** model (source intake, extraction/tuning, candidate
findings, canonical promoted truth, MCP/workbench posture). It aggregates **truthful**
signals from the repository and existing persistence (narrative revision governance,
improvement experiments on disk) without collapsing layers into one blob.

Principle: many revision candidates / experiments may coexist; **narrative_packages**
rows represent the current **promoted operational package** per module (canonical for
that governed unit), distinct from non-promoted ``NarrativeRevisionCandidate`` rows.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlalchemy import func

from app.extensions import db
from app.models import NarrativePackage, NarrativeRevisionCandidate, NarrativeRevisionConflict
from app.services.improvement_store import ImprovementStore
from app.services.runtime_status_semantics import STATUS_SEMANTICS


RESEARCH_DOMAIN_GOVERNANCE_VERSION = "1.0"

LAYER_IDS: tuple[str, ...] = (
    "source_intake",
    "extraction_tuning",
    "findings_candidates",
    "canonical_truth",
    "mcp_workbench",
)


def governance_principles() -> dict[str, Any]:
    """Stable cross-payload rules for operators and tests."""
    return {
        "many_candidate_findings_allowed": True,
        "single_promoted_canonical_truth_per_governed_module": True,
        "canonical_truth_requires_promotion_review_path": True,
        "research_execution_deeper_than_admin_strategy_pages": True,
        "layer_order": list(LAYER_IDS),
    }


def _resolve_repo_root() -> Path | None:
    env = (os.environ.get("WOS_REPO_ROOT") or "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        return p if p.is_dir() else None
    # backend/app/services -> parents[3] == repository root
    try:
        return Path(__file__).resolve().parents[3]
    except (OSError, ValueError):
        return None


def _count_docs_under(path: Path, pattern: str = "*.md") -> int:
    if not path.is_dir():
        return 0
    return sum(1 for _ in path.rglob(pattern))


def _source_intake_layer(repo: Path | None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "layer_id": "source_intake",
        "layer_role": "strategic_inventory_and_provenance_visibility",
        "summary": {},
        "categories": [],
        "processing_signals": [],
        "blockers": [],
        "warnings": [],
        "guidance": [],
        "related_admin_routes": [
            {"label": "Wiki (authored reference corpus)", "path": "/manage/wiki"},
            {"label": "Narrative governance (module packages)", "path": "/manage/narrative/overview"},
        ],
    }
    if repo is None:
        out["summary"] = {"repository_footprint_available": False}
        out["blockers"].append(
            {
                "code": "repo_root_unavailable",
                "message": "Repository root could not be resolved; source footprint counts are omitted.",
            }
        )
        out["guidance"].append("Set WOS_REPO_ROOT to the World of Shadows repository root on this host for path-based inventory.")
        return out

    docs = repo / "docs"
    tools_mcp = repo / "tools" / "mcp_server"
    scripts = repo / "scripts"
    out["summary"] = {
        "repository_footprint_available": True,
        "docs_markdown_files": _count_docs_under(docs),
        "mcp_server_tree_present": tools_mcp.is_dir(),
        "scripts_dir_present": scripts.is_dir(),
    }
    out["categories"] = [
        {
            "id": "documentation_corpus",
            "label": "Documentation corpus (markdown under docs/)",
            "count_hint": out["summary"]["docs_markdown_files"],
        },
        {
            "id": "mcp_tooling_tree",
            "label": "MCP server / tooling tree",
            "present": out["summary"]["mcp_server_tree_present"],
        },
        {
            "id": "operational_scripts",
            "label": "Scripts directory (CLI / batch processing)",
            "present": out["summary"]["scripts_dir_present"],
        },
    ]
    if out["summary"]["docs_markdown_files"] == 0 and docs.is_dir():
        out["warnings"].append({"code": "docs_empty", "message": "docs/ exists but no markdown files were counted."})
    out["guidance"].append("Use Source Intake for inventory posture; deep authoring stays in wiki and repo workflows.")
    return out


def _extraction_tuning_layer(repo: Path | None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "layer_id": "extraction_tuning",
        "layer_role": "governed_experiment_and_pipeline_visibility",
        "summary": {},
        "recent_runs": [],
        "blockers": [],
        "warnings": [],
        "guidance": [],
        "deferred_execution_surfaces": [
            {
                "id": "improvement_api",
                "label": "Improvement / experiment HTTP API",
                "note": "Active sandbox runs are initiated via authenticated improvement endpoints, not this admin page.",
            },
            {
                "id": "mcp_research_tools",
                "label": "MCP research tool handlers (tools/mcp_server)",
                "note": "Deeper retrieval and tool-driven research belong to MCP-adjacent clients; admin shows posture only.",
            },
        ],
    }
    store = ImprovementStore.default()
    experiments = store.list_json("experiments")
    out["summary"] = {
        "improvement_store_root": str(store.root),
        "experiment_file_count": len(experiments),
        "repository_attached": repo is not None,
    }
    # Newest-ish: last files in sorted glob order (store lists sorted)
    for exp in experiments[-5:]:
        eid = exp.get("experiment_id") or exp.get("id") or "unknown"
        status = exp.get("status") or exp.get("stage") or "unknown"
        out["recent_runs"].append(
            {
                "experiment_id": str(eid),
                "status": str(status),
                "contract_version": exp.get("contract_version"),
            }
        )
    if not experiments:
        out["warnings"].append(
            {
                "code": "no_persisted_experiments",
                "message": "No experiment JSON files under improvement store; extraction/tuning activity is not yet recorded on disk.",
            }
        )
    out["guidance"].append("Strategic view only — use improvement workflows or future workbench UIs for new runs.")
    return out


def _findings_candidates_layer() -> dict[str, Any]:
    out: dict[str, Any] = {
        "layer_id": "findings_candidates",
        "layer_role": "non_canonical_revision_and_conflict_visibility",
        "is_canonical_layer": False,
        "summary": {},
        "review_status_counts": {},
        "pending_conflict_count": 0,
        "sample_candidates": [],
        "blockers": [],
        "warnings": [],
        "guidance": [],
        "related_admin_routes": [
            {"label": "Narrative revisions (detailed CRUD)", "path": "/manage/narrative/revisions"},
            {"label": "Narrative findings", "path": "/manage/narrative/findings"},
        ],
    }
    q = (
        db.session.query(NarrativeRevisionCandidate.review_status, func.count(NarrativeRevisionCandidate.id))
        .group_by(NarrativeRevisionCandidate.review_status)
        .all()
    )
    out["review_status_counts"] = {str(row[0]): int(row[1]) for row in q}
    total_candidates = sum(out["review_status_counts"].values())
    out["summary"] = {"revision_candidate_total": total_candidates}

    pending = (
        db.session.query(func.count(NarrativeRevisionConflict.id))
        .filter(NarrativeRevisionConflict.resolution_status == "pending")
        .scalar()
    )
    out["pending_conflict_count"] = int(pending or 0)
    if out["pending_conflict_count"]:
        out["warnings"].append(
            {
                "code": "unresolved_revision_conflicts",
                "message": f"{out['pending_conflict_count']} narrative revision conflict(s) await resolution.",
            }
        )

    samples = (
        NarrativeRevisionCandidate.query.order_by(NarrativeRevisionCandidate.updated_at.desc()).limit(5).all()
    )
    for c in samples:
        out["sample_candidates"].append(
            {
                "revision_id": c.revision_id,
                "module_id": c.module_id,
                "review_status": c.review_status,
                "requires_review": bool(c.requires_review),
            }
        )

    out["guidance"].append(
        "Candidates are not canonical until promoted through narrative governance; use Revisions for detail."
    )
    return out


def _canonical_truth_layer() -> dict[str, Any]:
    out: dict[str, Any] = {
        "layer_id": "canonical_truth",
        "layer_role": "promoted_operational_packages_per_module",
        "is_canonical_layer": True,
        "summary": {},
        "promoted_modules": [],
        "blockers": [],
        "warnings": [],
        "guidance": [],
        "related_admin_routes": [
            {"label": "Narrative packages", "path": "/manage/narrative/packages"},
            {"label": "Narrative revisions (promotion workflow)", "path": "/manage/narrative/revisions"},
        ],
    }
    packages = NarrativePackage.query.order_by(NarrativePackage.module_id).all()
    out["summary"] = {
        "governed_module_count": len(packages),
        "semantic_note": "Each row is the current active narrative package for one module_id (promoted operational truth).",
    }
    for p in packages:
        out["promoted_modules"].append(
            {
                "module_id": p.module_id,
                "active_package_version": p.active_package_version,
                "active_source_revision": p.active_source_revision,
                "validation_status": p.validation_status,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
        )
    degraded = [m for m in out["promoted_modules"] if m.get("validation_status") not in ("ok", "valid", "unknown")]
    if degraded:
        out["warnings"].append(
            {
                "code": "package_validation_not_green",
                "message": "One or more active packages report non-ok validation_status; review narrative packages.",
                "modules": [m["module_id"] for m in degraded[:10]],
            }
        )
    out["guidance"].append("Canonical truth for narrative modules lives in narrative_packages; do not mutate via raw research drafts.")
    return out


def _mcp_workbench_layer(repo: Path | None) -> dict[str, Any]:
    research_handlers = repo / "tools" / "mcp_server" / "research_mcp_handler_factories.py" if repo else None
    present = research_handlers.is_file() if research_handlers else False
    out: dict[str, Any] = {
        "layer_id": "mcp_workbench",
        "layer_role": "connectivity_and_execution_posture_not_canonical_truth",
        "summary": {
            "mcp_server_package_present": present,
            "research_handler_factory_path": str(research_handlers) if research_handlers else None,
            "admin_strategic_mcp_page": "/manage/mcp-operations",
        },
        "execution_vs_strategy": {
            "administration_tool": "Strategic visibility, governance bundling, bounded admin actions.",
            "mcp_clients": "Tool-driven research, filesystem-backed workflows, deeper inspection.",
            "canonical_truth": "Promoted narrative packages and governed promotion paths — not MCP transcripts.",
        },
        "available_now": [
            "MCP Operations cockpit in administration-tool (suite registry, diagnostics, logs).",
            "Research-oriented MCP handler scaffolding under tools/mcp_server/ (when repo tree is present).",
        ],
        "deferred_to_workbench": [
            "Full interactive research IDE inside administration-tool.",
            "Automated promotion from MCP traces into narrative_packages without review.",
        ],
        "blockers": [],
        "warnings": [],
        "guidance": [],
        "related_admin_routes": [
            {"label": "MCP Operations", "path": "/manage/mcp-operations"},
            {"label": "Inspector Suite (AI stack workbench)", "path": "/manage/inspector-workbench"},
        ],
    }
    if repo is None:
        out["warnings"].append({"code": "repo_root_unavailable", "message": "Could not verify on-disk MCP research handler paths."})
    elif not present:
        out["warnings"].append({"code": "research_handlers_missing", "message": "Expected research MCP handler module not found at resolved path."})
    out["guidance"].append("Use MCP Operations for live suite posture; attach a capable MCP client for tool-heavy research execution.")
    return out


def _rollup_operational_state(layers: dict[str, dict[str, Any]]) -> str:
    """Coarse health for overview strip (reuses shared semantics ids)."""
    blocker_codes = []
    for key in LAYER_IDS:
        layer = layers.get(key) or {}
        for b in layer.get("blockers") or []:
            if isinstance(b, dict) and b.get("code"):
                blocker_codes.append(b["code"])
    if blocker_codes:
        return "blocked"
    warn_any = any(len((layers.get(k) or {}).get("warnings") or []) > 0 for k in LAYER_IDS)
    if warn_any:
        return "degraded"
    return "healthy"


def build_research_domain_overview() -> dict[str, Any]:
    """Aggregate all layers for the strategic Research Overview page."""
    repo = _resolve_repo_root()
    layers = {
        "source_intake": _source_intake_layer(repo),
        "extraction_tuning": _extraction_tuning_layer(repo),
        "findings_candidates": _findings_candidates_layer(),
        "canonical_truth": _canonical_truth_layer(),
        "mcp_workbench": _mcp_workbench_layer(repo),
    }
    state = _rollup_operational_state(layers)
    return {
        "domain": "research_governance",
        "governance_version": RESEARCH_DOMAIN_GOVERNANCE_VERSION,
        "status_semantics": STATUS_SEMANTICS,
        "operational_state": state,
        "governance_principles": governance_principles(),
        "layers": layers,
        "drill_down": [
            {"label": "Source intake", "path": "/manage/research/source-intake"},
            {"label": "Extraction / tuning", "path": "/manage/research/extraction-tuning"},
            {"label": "Findings (non-canonical)", "path": "/manage/research/findings"},
            {"label": "Canonical truth", "path": "/manage/research/canonical-truth"},
            {"label": "MCP / workbench posture", "path": "/manage/research/mcp-workbench"},
        ],
    }


def build_research_layer_payload(layer_id: str) -> dict[str, Any]:
    """Return one layer dict plus shared governance framing (for sub-pages)."""
    if layer_id not in LAYER_IDS:
        raise ValueError(f"unknown_layer:{layer_id}")
    repo = _resolve_repo_root()
    builders = {
        "source_intake": lambda: _source_intake_layer(repo),
        "extraction_tuning": lambda: _extraction_tuning_layer(repo),
        "findings_candidates": _findings_candidates_layer,
        "canonical_truth": _canonical_truth_layer,
        "mcp_workbench": lambda: _mcp_workbench_layer(repo),
    }
    layer_payload = builders[layer_id]()
    blocker_n = len(layer_payload.get("blockers") or [])
    warn_n = len(layer_payload.get("warnings") or [])
    op = "blocked" if blocker_n else ("degraded" if warn_n else "healthy")
    return {
        "domain": "research_governance",
        "governance_version": RESEARCH_DOMAIN_GOVERNANCE_VERSION,
        "status_semantics": STATUS_SEMANTICS,
        "operational_state": op,
        "governance_principles": governance_principles(),
        "layer": layer_payload,
        "overview_path": "/manage/research/overview",
    }
