"""G5: session evidence retrieval diagnostics passthrough canonical governance summary (control-plane only)."""

from __future__ import annotations

from ai_stack.retrieval_governance_summary import summarize_retrieval_governance_from_hit_rows

from app.services.ai_stack_evidence_service import _retrieval_influence_from_turn


def test_retrieval_influence_from_turn_passes_through_retrieval_governance_summary() -> None:
    sources = [
        {
            "chunk_id": "c-pg",
            "source_path": "policy/x.md",
            "content_class": "policy_guideline",
            "source_evidence_lane": "supporting",
            "source_visibility_class": "runtime_safe",
        }
    ]
    summary = summarize_retrieval_governance_from_hit_rows(sources)
    last_turn = {
        "retrieval": {
            "hit_count": 1,
            "status": "ok",
            "sources": sources,
            "retrieval_governance_summary": summary,
        }
    }
    out = _retrieval_influence_from_turn(last_turn)
    assert out is not None
    assert out.get("retrieval_governance_summary") is summary
    assert out.get("hit_count") == 1
