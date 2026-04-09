"""Observable gate-family evaluation for tests and reports (GATE_SCORING_POLICY_GOC.md §1)."""

from __future__ import annotations

from typing import Any, Literal

from ai_stack.goc_turn_seams import repro_metadata_complete

GateOutcome = Literal["pass", "fail", "conditional_pass"]


def gate_turn_integrity(state: dict[str, Any]) -> GateOutcome:
    nodes = (state.get("graph_diagnostics") or {}).get("nodes_executed") or []
    required = (
        "goc_resolve_canonical_content",
        "director_assess_scene",
        "director_select_dramatic_parameters",
        "proposal_normalize",
        "validate_seam",
        "commit_seam",
        "render_visible",
    )
    if not all(n in nodes for n in required):
        return "fail"
    vo = state.get("validation_outcome") if isinstance(state.get("validation_outcome"), dict) else {}
    cr = state.get("committed_result") if isinstance(state.get("committed_result"), dict) else {}
    if vo.get("status") == "approved" and not cr.get("commit_applied") and state.get("module_id") == "god_of_carnage":
        # Empty proposal still seams-complete; Phase 1 allows this path.
        pass
    return "pass"


def gate_diagnostic_sufficiency(state: dict[str, Any]) -> GateOutcome:
    repro = (state.get("graph_diagnostics") or {}).get("repro_metadata") or {}
    if not isinstance(repro, dict):
        return "fail"
    if repro_metadata_complete(repro):
        return "pass"
    return "conditional_pass"


def gate_dramatic_quality(state: dict[str, Any]) -> GateOutcome:
    vo = state.get("validation_outcome") if isinstance(state.get("validation_outcome"), dict) else {}
    reason = str(vo.get("reason", ""))
    if vo.get("status") == "rejected" and (
        reason.startswith("dramatic_alignment") or reason.startswith("dramatic_effect_")
    ):
        return "fail"
    markers = state.get("visibility_class_markers") or []
    if not isinstance(markers, list):
        markers = []
    if vo.get("status") != "approved":
        return "conditional_pass"
    if "truth_aligned" not in markers and state.get("experiment_preview") is False:
        return "conditional_pass"
    sf = state.get("selected_scene_function")
    bundle = state.get("visible_output_bundle") if isinstance(state.get("visible_output_bundle"), dict) else {}
    narr = bundle.get("gm_narration")
    if isinstance(narr, list) and narr:
        first = str(narr[0] or "")
        if len(first.strip()) < 12 and sf in ("escalate_conflict", "redirect_blame", "reveal_surface"):
            return "conditional_pass"
    return "pass"


def gate_slice_boundary(state: dict[str, Any]) -> GateOutcome:
    markers = state.get("failure_markers") or []
    if not isinstance(markers, list):
        return "pass"
    for m in markers:
        if isinstance(m, dict) and m.get("failure_class") == "scope_breach":
            return "fail"
    return "pass"
