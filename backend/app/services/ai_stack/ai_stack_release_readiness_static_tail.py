"""Statischer Report-Tail für Release-Readiness (DS-009)."""

from __future__ import annotations

from typing import Any


def build_release_readiness_static_tail(*, trace_id: str) -> dict[str, Any]:
    """Top-level keys shared with assemble_release_readiness_report_payload."""
    retrieval_readiness_summary = {
        "trace_schema": "retrieval_closure_v1_via_build_retrieval_trace",
        "strengths": [
            "Hybrid and sparse retrieval paths with explicit degradation_mode and retrieval_route in capability payloads",
            "Source governance lanes and pack roles preserved from Task 3; traces expose lane mix and policy outcome hints",
            "Named evaluation scenarios in ai_stack/tests exercise runtime, writers_room, and improvement profiles",
        ],
        "known_degradations": [
            "Sparse-only route caps multi-hit strong tiers unless hybrid canonical/evaluative backing applies",
            "Local JSON corpus and single-host dense index; not a distributed vector service",
            "Partial dense persistence marks degraded_due_to_partial_persistence_problem and can cap evidence tiers",
        ],
        "evaluation_coverage": (
            "ai_stack/tests/test_rag.py (retrieval_eval_scenarios harness); "
            "ai_stack/tests/test_capabilities.py (build_retrieval_trace); "
            "backend tests for improvement and observability when retrieval payloads are mocked or live"
        ),
        "intentionally_deferred": [
            "External observability platform or long-term trace warehouse",
            "Full UI dashboards for retrieval analytics",
            "Cross-session retrieval quality trending",
        ],
    }
    return {
        "trace_id": trace_id,
        "retrieval_readiness_summary": retrieval_readiness_summary,
        "subsystem_maturity": [
            {
                "subsystem": "story_runtime_world_engine",
                "role": "authoritative_host",
                "maturity_note": "Committed state vs diagnostic envelopes are explicit in engine diagnostics API.",
            },
            {
                "subsystem": "writers_room_langgraph",
                "role": "workflow_seed",
                "maturity_note": "Seed graph only; orchestration depth is partial vs runtime turn graph.",
            },
            {
                "subsystem": "runtime_turn_langgraph",
                "role": "primary_turn_executor",
                "maturity_note": "Full node chain with explicit execution_health and fallback semantics.",
            },
            {
                "subsystem": "retrieval_rag_task4",
                "role": "knowledge_layer",
                "maturity_note": (
                    "Local hybrid/sparse RAG with governed lanes; compact traces (evidence_tier, lane mix, "
                    "readiness_label) for operators—no second hidden ranker in the trace layer."
                ),
            },
        ],
        "known_partiality": [
            "local_json_persistence_not_distributed",
            "no_signed_immutable_audit_store",
            "release_readiness_aggregate_does_not_substitute_for_session_evidence",
        ],
        "known_environment_sensitivities": [
            "writers_room_and_improvement_artifacts_depend_on_local_var_json_layout",
            "improvement_latest_package_requires_parseable_generated_at_iso_timestamps",
        ],
    }
