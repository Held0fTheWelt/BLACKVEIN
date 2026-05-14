from __future__ import annotations

from ai_stack.context_synthesis_contracts import (
    CONTEXT_SYNTHESIS_AUTHORITY,
    CONTEXT_SYNTHESIS_FORBIDDEN_TRUTH_FIELDS,
    CONTEXT_SYNTHESIS_SCHEMA_VERSION,
)
from ai_stack.context_synthesis_engine import (
    build_context_synthesis_bundle,
    context_synthesis_prompt_lines,
    summarize_context_synthesis_for_diagnostics,
)


def _retrieval_with_sources(*lanes: str) -> dict:
    return {
        "status": "ok",
        "hit_count": len(lanes),
        "sources": [
            {
                "chunk_id": f"chunk-{index}",
                "source_path": f"content/runtime/source-{index}.md",
                "snippet": f"Evidence item {index} describes a bounded runtime fact.",
                "score": "0.8800",
                "pack_role": "supporting_context",
                "selection_reason": "selected by retrieval rank",
                "source_evidence_lane": lane,
                "source_visibility_class": "model_visible",
            }
            for index, lane in enumerate(lanes, start=1)
        ],
    }


def test_context_synthesis_bundle_tracks_sources_and_authority_boundary() -> None:
    bundle = build_context_synthesis_bundle(
        retrieval=_retrieval_with_sources("canonical", "draft"),
        context_text="bounded evidence pack",
        scene_assessment={"scene_core": "tense exchange", "pressure_state": "rising"},
        semantic_move_record={"move_type": "challenge", "scene_risk_band": "medium"},
        social_state_record={"scene_pressure_state": "active", "active_thread_count": 2},
        turn_aspect_ledger={"input": {"applicable": True, "status": "ok"}},
        hierarchical_memory_context={"context_lines": ["Earlier choice remains relevant."]},
    )

    assert bundle["schema_version"] == CONTEXT_SYNTHESIS_SCHEMA_VERSION
    assert bundle["authority"] == CONTEXT_SYNTHESIS_AUTHORITY
    assert bundle["forbidden_as_truth"] is True
    assert all(field not in bundle for field in CONTEXT_SYNTHESIS_FORBIDDEN_TRUTH_FIELDS)

    retrieval_items = [
        item for item in bundle["evidence_items"] if "retrieval" in item.get("derived_from", [])
    ]
    assert len(retrieval_items) == 2
    assert all(item.get("source_refs") for item in retrieval_items)
    assert bundle["source_lane_mix"].get("canonical") == 1
    assert bundle["source_lane_mix"].get("draft") == 1

    obligation_codes = {item["code"] for item in bundle["obligations"]}
    assert "preserve_runtime_authority_boundary" in obligation_codes
    assert "ground_generation_in_retrieved_evidence" in obligation_codes
    assert "respect_actor_lanes_and_validation" in obligation_codes

    conflict_codes = {item["code"] for item in bundle["conflicts"]}
    assert "mixed_authority_context" in conflict_codes


def test_context_synthesis_records_gaps_without_truth_or_commit_fields() -> None:
    bundle = build_context_synthesis_bundle(
        retrieval={"status": "skipped", "hit_count": 0, "sources": []},
        context_text="",
        scene_assessment=None,
        semantic_move_record=None,
        social_state_record=None,
        turn_aspect_ledger=None,
        hierarchical_memory_context=None,
    )
    diagnostics = summarize_context_synthesis_for_diagnostics(bundle)

    assert bundle["status"] == "degraded_empty"
    assert diagnostics["authority"] == CONTEXT_SYNTHESIS_AUTHORITY
    assert diagnostics["forbidden_truth_fields_absent"] is True
    assert "retrieval_context_missing" in diagnostics["gap_codes"]
    assert "scene_assessment_missing" in diagnostics["gap_codes"]
    assert all(field not in bundle for field in CONTEXT_SYNTHESIS_FORBIDDEN_TRUTH_FIELDS)


def test_context_synthesis_prompt_lines_are_bounded_prompt_support() -> None:
    bundle = build_context_synthesis_bundle(
        retrieval=_retrieval_with_sources("canonical"),
        context_text="bounded evidence pack",
        scene_assessment={"scene_core": "focused scene"},
        semantic_move_record={"move_type": "answer"},
        social_state_record={"scene_pressure_state": "steady"},
        turn_aspect_ledger={"validation": {"applicable": True, "status": "partial"}},
        hierarchical_memory_context={},
    )

    prompt_text = "\n".join(context_synthesis_prompt_lines(bundle))
    diagnostics = summarize_context_synthesis_for_diagnostics(bundle, used_in_model_prompt=bool(prompt_text))

    assert "Context Synthesis (proposal support, non-authoritative):" in prompt_text
    assert "Synthesis Obligations:" in prompt_text
    assert "preserve_runtime_authority_boundary" in prompt_text
    assert diagnostics["used_in_model_prompt"] is True
    assert diagnostics["evidence_item_count"] >= 1
