"""Proposal, validation, commit, visible seams helpers (CANONICAL_TURN_CONTRACT_GOC.md §2)."""

from __future__ import annotations

from typing import Any

from ai_stack.goc_frozen_vocab import DIRECTOR_IMMUTABLE_FIELDS, GOC_MODULE_ID, assert_transition_pattern


def strip_director_overwrites_from_structured_output(
    structured: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Remove immutable director fields from model structured output (§3.6)."""
    if not structured or not isinstance(structured, dict):
        return structured, []
    markers: list[dict[str, Any]] = []
    cleaned = dict(structured)
    for key in DIRECTOR_IMMUTABLE_FIELDS:
        if key in cleaned:
            del cleaned[key]
            markers.append(
                {
                    "marker": "stripped_model_overwrite_attempt",
                    "field": key,
                    "note": "CANONICAL_TURN_CONTRACT_GOC.md §3.6 — model cannot replace director fields.",
                }
            )
    return cleaned, markers


def structured_output_to_proposed_effects(structured: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Map structured output into proposed_state_effects list."""
    if not structured or not isinstance(structured, dict):
        return []
    raw = structured.get("proposed_state_effects")
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if structured.get("effect_type") or structured.get("description"):
        return [
            {
                "effect_type": structured.get("effect_type", "narrative_beat"),
                "description": str(structured.get("description", "")),
            }
        ]
    narr = structured.get("narrative_response")
    if isinstance(narr, str) and narr.strip():
        return [
            {
                "effect_type": "narrative_proposal",
                "description": narr.strip()[:4096],
            }
        ]
    return []


def run_validation_seam(
    *,
    module_id: str,
    proposed_state_effects: list[dict[str, Any]],
    generation: dict[str, Any],
) -> dict[str, Any]:
    """Emit validation_outcome — no player text (CANONICAL_TURN_CONTRACT_GOC.md §2.1)."""
    if module_id != GOC_MODULE_ID:
        return {
            "status": "waived",
            "reason": "non_goc_vertical_slice",
        }
    success = generation.get("success")
    if success is False or generation.get("error"):
        return {
            "status": "rejected",
            "reason": "model_generation_failed",
        }
    for eff in proposed_state_effects:
        if not isinstance(eff, dict):
            return {"status": "rejected", "reason": "malformed_proposed_effect"}
        if "description" not in eff and "effect_type" not in eff:
            return {"status": "rejected", "reason": "incomplete_proposed_effect"}
    return {
        "status": "approved",
        "reason": "goc_default_validator_pass",
    }


def run_commit_seam(
    *,
    module_id: str,
    validation_outcome: dict[str, Any],
    proposed_state_effects: list[dict[str, Any]],
) -> dict[str, Any]:
    if validation_outcome.get("status") != "approved":
        return {"committed_effects": [], "commit_applied": False}
    if module_id != GOC_MODULE_ID:
        return {"committed_effects": [], "commit_applied": False}
    return {
        "committed_effects": list(proposed_state_effects),
        "commit_applied": bool(proposed_state_effects),
    }


def run_visible_render(
    *,
    module_id: str,
    committed_result: dict[str, Any],
    validation_outcome: dict[str, Any],
    generation: dict[str, Any],
    transition_pattern: str,
) -> tuple[dict[str, Any], list[str]]:
    """Build visible_output_bundle aligned with committed truth (§2.2–§2.3)."""
    _ = transition_pattern  # reserved for future bundle tone selection
    content = str(generation.get("content") or generation.get("text") or "").strip()
    if not content and isinstance(generation.get("metadata"), dict):
        meta = generation["metadata"]
        if isinstance(meta.get("raw_content"), str):
            content = meta["raw_content"].strip()

    markers: list[str] = []
    approved = validation_outcome.get("status") == "approved"
    committed = committed_result.get("committed_effects") or []
    has_commit = bool(committed) and committed_result.get("commit_applied")

    if module_id != GOC_MODULE_ID:
        bundle = {
            "gm_narration": [content] if content else [],
            "spoken_lines": [],
        }
        markers.append("non_factual_staging")
        return bundle, markers

    if has_commit and approved:
        bundle = {
            "gm_narration": [content] if content else ["(scene continues — committed effects applied.)"],
            "spoken_lines": [],
        }
        markers.append("truth_aligned")
        return bundle, markers

    # No commit: truth-safe staging (GATE_SCORING_POLICY_GOC.md §6.3).
    safe = content if content else "(Preview staging — no committed world-state change.)"
    bundle = {
        "gm_narration": [safe],
        "spoken_lines": [],
    }
    markers.append("non_factual_staging")
    return bundle, markers


def build_diagnostics_refs(
    *,
    graph_diagnostics: dict[str, Any],
    experiment_preview: bool,
    transition_pattern: str,
    gate_hints: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Project operational diagnostics into canonical refs (CANONICAL_TURN_CONTRACT_GOC.md §5)."""
    tp = assert_transition_pattern(transition_pattern)
    refs: list[dict[str, Any]] = [
        {
            "ref_type": "graph_diagnostics_projection",
            "graph_name": graph_diagnostics.get("graph_name"),
            "graph_version": graph_diagnostics.get("graph_version"),
            "nodes_executed": graph_diagnostics.get("nodes_executed"),
            "node_outcomes": graph_diagnostics.get("node_outcomes"),
            "fallback_path_taken": graph_diagnostics.get("fallback_path_taken"),
            "execution_health": graph_diagnostics.get("execution_health"),
        },
        {
            "ref_type": "experiment_preview",
            "experiment_preview": experiment_preview,
        },
        {
            "ref_type": "transition_pattern",
            "transition_pattern": tp,
        },
    ]
    if gate_hints:
        refs.append({"ref_type": "gate_review_hints", **gate_hints})
    return refs


def repro_metadata_complete(repro: dict[str, Any]) -> bool:
    """GATE_SCORING_POLICY_GOC.md §5.2 — required fields for operator questions."""
    required = (
        "graph_name",
        "trace_id",
        "selected_model",
        "selected_provider",
        "retrieval_domain",
        "retrieval_profile",
        "model_attempted",
        "model_success",
        "adapter_invocation_mode",
        "graph_path_summary",
    )
    return all(repro.get(k) not in (None, "") for k in required)
