from __future__ import annotations

import pytest

from ai_stack.research_contract import CopyrightPosture, ResearchSourceRecord
from ai_stack.research_exploration import run_bounded_exploration
from ai_stack.research_ingestion import enforce_mvp_copyright_posture
from ai_stack.research_store import ResearchStore
from ai_stack.research_validation import verify_and_promote_claims


def test_exploration_requires_budget_object():
    with pytest.raises(ValueError, match="exploration_budget_required"):
        run_bounded_exploration(seed_aspects=[], budget=None)


def test_verification_blocks_unknown_anchor_reference(tmp_path):
    store = ResearchStore(tmp_path / "research_store.json")
    result = verify_and_promote_claims(
        store=store,
        work_id="god_of_carnage",
        candidate_payloads=[
            {
                "claim_type": "dramatic_function",
                "statement": "supported claim with unknown anchor",
                "evidence_anchor_ids": ["anchor_missing"],
                "perspective": "playwright",
                "canon_relevance_hint": True,
            }
        ],
        support_threshold=0.1,
    )
    assert result["claims"] == []
    assert result["decisions"][0]["decision"] == "blocked"
    assert result["decisions"][0]["reason"] == "unknown_evidence_anchor"


def test_store_rejects_empty_provenance_dict(tmp_path):
    store = ResearchStore(tmp_path / "research_store.json")
    with pytest.raises(ValueError, match="empty_required_object:provenance"):
        store.upsert_source(
            ResearchSourceRecord(
                source_id="source_1",
                work_id="god_of_carnage",
                source_type="scene_note",
                title="x",
                provenance={},
                visibility="internal",
                copyright_posture=CopyrightPosture.INTERNAL_APPROVED,
                segment_index_status="indexed",
                metadata={"fixture": "neg"},
            )
        )


def test_external_posture_blocked_in_mvp():
    with pytest.raises(ValueError, match="copyright_posture_blocked_in_mvp"):
        enforce_mvp_copyright_posture(CopyrightPosture.EXTERNAL_BLOCKED)
