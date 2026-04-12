"""Read-only projection services for Inspector timeline/comparison/coverage/provenance views."""

from __future__ import annotations

from typing import Any

from ai_stack.semantic_planner_effect_surface import (
    resolve_dramatic_effect_evaluator,
    support_level_for_module,
)

from app.contracts.inspector_turn_projection import (
    INSPECTOR_COMPARISON_PROJECTION_SCHEMA_VERSION,
    INSPECTOR_PROVENANCE_RAW_PROJECTION_SCHEMA_VERSION,
    INSPECTOR_TIMELINE_PROJECTION_SCHEMA_VERSION,
    make_supported_section,
    make_unavailable_section,
)
from app.services.ai_stack_evidence_service import build_session_evidence_bundle
from app.services.inspector_projection_comparison import (
    build_turn_comparisons,
    comparison_dimension_lists,
    session_has_candidate_matrix,
)
from app.services.inspector_projection_provenance_raw_entries import build_provenance_entries
from app.services.inspector_projection_shared import _build_root, _diagnostics_rows
from app.services.inspector_projection_turn_view import extract_turn_view


def build_inspector_timeline_projection(*, session_id: str, trace_id: str) -> dict[str, Any]:
    """Return per-turn timeline projection from existing diagnostics rows."""
    bundle = build_session_evidence_bundle(session_id=session_id, trace_id=trace_id)
    if bundle.get("error") == "backend_session_not_found":
        return bundle
    rows = _diagnostics_rows(bundle)
    if not rows:
        section = make_unavailable_section(reason="no_turn_diagnostics_for_session", data={"turns": []})
        return _build_root(
            bundle=bundle,
            session_id=session_id,
            schema_version=INSPECTOR_TIMELINE_PROJECTION_SCHEMA_VERSION,
            projection_status="partial",
            section_key="timeline_projection",
            section=section,
        )

    mid = bundle.get("module_id")
    turns = [extract_turn_view(row, idx, module_id=mid) for idx, row in enumerate(rows)]
    section = make_supported_section(
        {
            "total_turns": len(turns),
            "turns": turns,
        }
    )
    return _build_root(
        bundle=bundle,
        session_id=session_id,
        schema_version=INSPECTOR_TIMELINE_PROJECTION_SCHEMA_VERSION,
        projection_status="ok",
        section_key="timeline_projection",
        section=section,
    )


def build_inspector_comparison_projection(*, session_id: str, trace_id: str) -> dict[str, Any]:
    """Return bounded turn-to-turn comparison projection for one session."""
    bundle = build_session_evidence_bundle(session_id=session_id, trace_id=trace_id)
    if bundle.get("error") == "backend_session_not_found":
        return bundle
    rows = _diagnostics_rows(bundle)
    if len(rows) < 2:
        section = make_unavailable_section(
            reason="comparison_requires_at_least_two_turns",
            data={
                "mandatory_dimension": "turn_to_turn_within_session",
                "supported_dimensions": [],
                "unsupported_dimensions": [
                    "cross_session_comparison_no_shared_projection_source",
                    "cross_run_version_delta_not_emitted",
                ],
                "comparisons": [],
            },
        )
        return _build_root(
            bundle=bundle,
            session_id=session_id,
            schema_version=INSPECTOR_COMPARISON_PROJECTION_SCHEMA_VERSION,
            projection_status="partial",
            section_key="comparison_projection",
            section=section,
        )

    mid = bundle.get("module_id")
    turns = [extract_turn_view(row, idx, module_id=mid) for idx, row in enumerate(rows)]
    has_candidates = session_has_candidate_matrix(rows)
    supported_dimensions, unsupported_dimensions = comparison_dimension_lists(has_candidates=has_candidates)
    comparisons = build_turn_comparisons(rows, turns, has_candidates=has_candidates)

    section = make_supported_section(
        {
            "mandatory_dimension": "turn_to_turn_within_session",
            "supported_dimensions": supported_dimensions,
            "unsupported_dimensions": unsupported_dimensions,
            "comparisons": comparisons,
            "semantic_planner_support_level": support_level_for_module(mid if isinstance(mid, str) else "").value,
            "dramatic_effect_evaluator_class": type(
                resolve_dramatic_effect_evaluator(mid if isinstance(mid, str) else "")
            ).__name__,
        }
    )
    return _build_root(
        bundle=bundle,
        session_id=session_id,
        schema_version=INSPECTOR_COMPARISON_PROJECTION_SCHEMA_VERSION,
        projection_status="ok",
        section_key="comparison_projection",
        section=section,
    )


def build_inspector_coverage_health_projection(*, session_id: str, trace_id: str) -> dict[str, Any]:
    """Return evidence-backed coverage/health aggregates."""
    from app.services.inspector_projection_coverage_health import (
        build_inspector_coverage_health_projection as _build_inspector_coverage_health_projection,
    )

    return _build_inspector_coverage_health_projection(session_id=session_id, trace_id=trace_id)


def build_inspector_provenance_raw_projection(
    *,
    session_id: str,
    trace_id: str,
    mode: str = "canonical",
) -> dict[str, Any]:
    """Return provenance entries and optional raw evidence bundle."""
    bundle = build_session_evidence_bundle(session_id=session_id, trace_id=trace_id)
    if bundle.get("error") == "backend_session_not_found":
        return bundle
    rows = _diagnostics_rows(bundle)
    if not rows:
        section = make_unavailable_section(reason="no_turn_diagnostics_for_session", data={"entries": []})
        payload = _build_root(
            bundle=bundle,
            session_id=session_id,
            schema_version=INSPECTOR_PROVENANCE_RAW_PROJECTION_SCHEMA_VERSION,
            projection_status="partial",
            section_key="provenance_raw_projection",
            section=section,
        )
        payload["raw_mode_loaded"] = False
        return payload

    last = rows[-1]
    entries = build_provenance_entries(last=last, bundle=bundle)
    section = make_supported_section(
        {
            "entries": entries,
            "canonical_vs_raw_boundary": (
                "raw_evidence_is_operator_inspection_material_only_and_must_not_replace_canonical_projection_sections"
            ),
        }
    )
    payload = _build_root(
        bundle=bundle,
        session_id=session_id,
        schema_version=INSPECTOR_PROVENANCE_RAW_PROJECTION_SCHEMA_VERSION,
        projection_status="ok",
        section_key="provenance_raw_projection",
        section=section,
    )
    if mode == "raw":
        payload["raw_mode_loaded"] = True
        payload["raw_evidence"] = {
            "world_engine_state": bundle.get("world_engine_state"),
            "world_engine_diagnostics": bundle.get("world_engine_diagnostics"),
            "execution_truth": bundle.get("execution_truth"),
            "cross_layer_classifiers": bundle.get("cross_layer_classifiers"),
            "bridge_errors": bundle.get("bridge_errors"),
        }
    else:
        payload["raw_mode_loaded"] = False
    return payload
