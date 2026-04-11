"""Writers Room: persistence and public service API.

Heavy workflow implementation lives in ``writers_room_pipeline``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.contracts.writers_room_artifact_class import (
    GOC_SHARED_SEMANTIC_CONTRACT_VERSION,
    WritersRoomArtifactClass,
    build_writers_room_artifact_record,
)
from app.services.writers_room_pipeline import (
    _execute_writers_room_workflow_package,
    _get_workflow,
    _utc_now,
    _writers_room_artifact_manifest,
)


@dataclass
class WritersRoomStore:
    root: Path

    @classmethod
    def default(cls) -> "WritersRoomStore":
        root = Path(__file__).resolve().parents[2] / "var" / "writers_room"
        return cls(root=root)

    def ensure_dirs(self) -> None:
        (self.root / "reviews").mkdir(parents=True, exist_ok=True)

    def write_review(self, review_id: str, payload: dict[str, Any]) -> Path:
        self.ensure_dirs()
        path = self.root / "reviews" / f"{review_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return path

    def read_review(self, review_id: str) -> dict[str, Any]:
        path = self.root / "reviews" / f"{review_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))


def run_writers_room_review(
    *, module_id: str, focus: str, actor_id: str, trace_id: str | None = None
) -> dict[str, Any]:
    storage = WritersRoomStore.default()
    workflow = _get_workflow()
    package = _execute_writers_room_workflow_package(
        workflow=workflow,
        module_id=module_id,
        focus=focus,
        actor_id=actor_id,
        trace_id=trace_id,
    )
    review_id = f"review_{uuid4().hex}"
    review_state = {
        "status": "pending_human_review",
        "updated_at": _utc_now(),
        "updated_by": actor_id,
        "history": [
            {
                "status": "pending_human_review",
                "changed_at": _utc_now(),
                "changed_by": actor_id,
                "note": "Initial workflow package created.",
            }
        ],
    }
    report = {
        **package,
        "review_id": review_id,
        "review_state": review_state,
        "revision_cycles": [],
        "artifact_provenance": {
            "workflow": "writers_room_unified_stack_workflow",
            "created_at": _utc_now(),
            "module_id": module_id,
            "trace_id": trace_id,
            "shared_semantic_contract_version": GOC_SHARED_SEMANTIC_CONTRACT_VERSION,
        },
    }
    report["writers_room_artifact_manifest"] = _writers_room_artifact_manifest(report)
    storage.write_review(review_id, report)
    return report


def get_writers_room_review(*, review_id: str) -> dict[str, Any]:
    storage = WritersRoomStore.default()
    return storage.read_review(review_id)


def apply_writers_room_decision(
    *,
    review_id: str,
    actor_id: str,
    decision: str,
    note: str | None = None,
) -> dict[str, Any]:
    storage = WritersRoomStore.default()
    review = storage.read_review(review_id)
    state = review.get("review_state", {})
    current_status = str(state.get("status", "pending_human_review"))
    normalized = decision.strip().lower()
    if normalized not in {"accept", "reject", "revise"}:
        raise ValueError("decision_must_be_accept_reject_or_revise")
    if current_status in {"accepted", "rejected"}:
        raise ValueError("review_already_finalized")
    if current_status not in {"pending_human_review", "pending_revision"}:
        raise ValueError("invalid_review_state_for_decision")

    history = state.get("history", [])
    if not isinstance(history, list):
        history = []

    if normalized == "revise":
        next_status = "pending_revision"
        history.append(
            {
                "decision": "revise",
                "status": next_status,
                "changed_at": _utc_now(),
                "changed_by": actor_id,
                "note": note or "",
            }
        )
        state["status"] = next_status
        state["updated_at"] = _utc_now()
        state["updated_by"] = actor_id
        state["history"] = history
        review["review_state"] = state
        review["last_hitl_action"] = {
            "decision": "revise",
            "actor_id": actor_id,
            "acted_at": _utc_now(),
            "note": note or "",
        }
        review.pop("governance_outcome_artifact", None)
        review["writers_room_artifact_manifest"] = _writers_room_artifact_manifest(review)
        storage.write_review(review_id, review)
        return review

    next_status = "accepted" if normalized == "accept" else "rejected"
    history.append(
        {
            "decision": normalized,
            "status": next_status,
            "changed_at": _utc_now(),
            "changed_by": actor_id,
            "note": note or "",
        }
    )
    state["status"] = next_status
    state["updated_at"] = _utc_now()
    state["updated_by"] = actor_id
    state["history"] = history
    review["review_state"] = state
    decided_at = _utc_now()
    review["human_decision"] = {
        "decision": normalized,
        "decided_by": actor_id,
        "decided_at": decided_at,
        "note": note or "",
    }
    mod_id = str(review.get("module_id") or "")
    pp = review.get("proposal_package") if isinstance(review.get("proposal_package"), dict) else {}
    ev_src = pp.get("evidence_sources") if isinstance(pp.get("evidence_sources"), list) else []
    ev_refs = [str(x) for x in ev_src[:20] if x]
    outcome_cls = (
        WritersRoomArtifactClass.approved_authored_artifact
        if next_status == "accepted"
        else WritersRoomArtifactClass.rejected_artifact
    )
    review["governance_outcome_artifact"] = {
        **build_writers_room_artifact_record(
            artifact_id=f"gov_outcome_{review_id}",
            artifact_class=outcome_cls,
            source_module_id=mod_id,
            evidence_refs=ev_refs,
            proposal_scope="hitl_terminal_decision",
            approval_state=next_status,
        ),
        "review_id": review_id,
        "terminal_status": next_status,
        "decided_at": decided_at,
        "note": "HITL outcome only; does not auto-publish canonical module content.",
    }
    review["writers_room_artifact_manifest"] = _writers_room_artifact_manifest(review)
    storage.write_review(review_id, review)
    return review


_REVISION_SNAPSHOT_KEYS = frozenset(
    {
        "proposal_package",
        "review_bundle",
        "review_summary",
        "workflow_manifest",
        "issues",
        "recommendation_artifacts",
        "patch_candidates",
        "variant_candidates",
        "comment_bundle",
        "model_generation",
        "langchain_retriever_preview",
        "retrieval",
        "retrieval_trace",
    }
)


def submit_writers_room_revision(
    *,
    review_id: str,
    actor_id: str,
    focus: str | None = None,
    note: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Re-run workflow while persisting prior artifact snapshot; only from pending_revision."""
    storage = WritersRoomStore.default()
    review = storage.read_review(review_id)
    state = review.get("review_state", {})
    if str(state.get("status", "")) != "pending_revision":
        raise ValueError("revision_submit_requires_pending_revision")

    module_id = str(review.get("module_id") or "")
    if not module_id:
        raise ValueError("review_missing_module_id")

    focus_resolved = (focus or "").strip() or str(review.get("focus") or "canon consistency and dramaturgy")

    prior_snapshot = {k: review[k] for k in _REVISION_SNAPSHOT_KEYS if k in review}
    cycles = review.get("revision_cycles")
    if not isinstance(cycles, list):
        cycles = []

    workflow = _get_workflow()
    package = _execute_writers_room_workflow_package(
        workflow=workflow,
        module_id=module_id,
        focus=focus_resolved,
        actor_id=actor_id,
        trace_id=trace_id or review.get("trace_id"),
    )

    cycle_id = f"revcycle_{uuid4().hex}"
    cycles.append(
        {
            "cycle_id": cycle_id,
            "submitted_at": _utc_now(),
            "submitted_by": actor_id,
            "actor_note": note or "",
            "focus": focus_resolved,
            "prior_snapshot": prior_snapshot,
        }
    )

    merged = dict(review)
    for key, value in package.items():
        merged[key] = value
    merged["review_id"] = review_id
    merged["focus"] = focus_resolved
    merged["revision_cycles"] = cycles

    history = state.get("history", [])
    if not isinstance(history, list):
        history = []
    history.append(
        {
            "event": "revision_submitted",
            "cycle_id": cycle_id,
            "status": "pending_human_review",
            "changed_at": _utc_now(),
            "changed_by": actor_id,
            "note": note or "",
        }
    )
    state["status"] = "pending_human_review"
    state["updated_at"] = _utc_now()
    state["updated_by"] = actor_id
    state["history"] = history
    merged["review_state"] = state
    merged.pop("human_decision", None)
    merged.pop("last_hitl_action", None)
    merged.pop("governance_outcome_artifact", None)
    merged["writers_room_artifact_manifest"] = _writers_room_artifact_manifest(merged)
    storage.write_review(review_id, merged)
    return merged
