from __future__ import annotations

from ai_stack.contracts.consequence_cascade_contracts import (
    CONSEQUENCE_CASCADE_FAILURE_CODES,
    CONSEQUENCE_CASCADE_POLICY_SCHEMA_VERSION,
    consequence_cascade_aspect_blocks,
    consequence_cascade_bounds_from_policy,
    normalize_consequence_cascade_policy,
    validate_consequence_cascade_record,
)


def _policy() -> dict:
    first_class = next(iter(sorted(CONSEQUENCE_CASCADE_FAILURE_CODES))).replace(
        "consequence_cascade_", "class_"
    )
    return normalize_consequence_cascade_policy(
        {
            "enabled": True,
            "schema_version": CONSEQUENCE_CASCADE_POLICY_SCHEMA_VERSION,
            "max_atoms": 8,
            "max_edges": 8,
            "max_graph_items": 2,
            "max_evidence_refs_per_consequence": 3,
            "decay_after_turns": 2,
            "allowed_continuity_classes": [first_class],
        }
    )


def _record(policy: dict) -> dict:
    continuity_class = policy["allowed_continuity_classes"][0]
    return {
        "schema_version": "consequence_cascade_record.v1",
        "cascade_id": "cascade-alpha",
        "story_session_id": "session-alpha",
        "derived_from_committed_truth": True,
        "mutates_canonical_state": False,
        "inactive_branches_authoritative": False,
        "atoms": [
            {
                "consequence_id": "cons-alpha",
                "source_turn_id": "turn-alpha",
                "continuity_class": continuity_class,
                "evidence": {"source_fields": ["narrative_commit"], "signal_hashes": ["abc"]},
                "derived_from_committed_truth": True,
                "mutates_canonical_state": False,
            }
        ],
        "edges": [],
        "snapshot": {
            "cascade_id": "cascade-alpha",
            "atom_count": 1,
            "edge_count": 0,
            "active_atom_count": 1,
            "continuity_classes": [continuity_class],
        },
    }


def test_consequence_cascade_policy_normalizes_bounds() -> None:
    policy = _policy()
    bounds = consequence_cascade_bounds_from_policy(policy)

    assert policy["schema_version"] == CONSEQUENCE_CASCADE_POLICY_SCHEMA_VERSION
    assert policy["enabled"] is True
    assert bounds["max_atoms"] == policy["max_atoms"]
    assert bounds["max_edges"] == policy["max_edges"]
    assert bounds["max_evidence_refs"] == policy["max_evidence_refs"]


def test_consequence_cascade_validation_accepts_bounded_committed_record() -> None:
    policy = _policy()
    validation = validate_consequence_cascade_record(_record(policy), policy=policy)

    assert validation["contract_pass"] is True
    assert validation["failure_codes"] == []
    assert validation["atom_count"] == 1


def test_consequence_cascade_validation_rejects_unbounded_or_mutating_record() -> None:
    policy = _policy()
    record = _record(policy)
    record["mutates_canonical_state"] = True
    record["atoms"][0]["continuity_class"] = f"{policy['allowed_continuity_classes'][0]}_outside"
    record["atoms"][0]["evidence"]["signal_hashes"] = ["a", "b", "c"]

    validation = validate_consequence_cascade_record(record, policy=policy)

    assert validation["contract_pass"] is False
    assert "consequence_cascade_authority_mutation" in validation["failure_codes"]
    assert "consequence_cascade_forbidden_continuity_class" in validation["failure_codes"]
    assert "consequence_cascade_unbounded_evidence" in validation["failure_codes"]


def test_consequence_cascade_aspect_blocks_project_validation_and_selection() -> None:
    policy = _policy()
    record = _record(policy)
    export = {
        "selected_consequence_ids": ["cons-alpha"],
        "selected_edge_ids": [],
        "selected_continuity_classes": [policy["allowed_continuity_classes"][0]],
        "selected_statuses": ["active"],
        "exported_item_count": 1,
    }
    validation = validate_consequence_cascade_record(record, policy=policy)

    blocks = consequence_cascade_aspect_blocks(
        record=record,
        graph_export=export,
        validation=validation,
        policy=policy,
    )

    assert blocks["expected"]["policy_enabled"] is True
    assert blocks["selected"]["selected_consequence_ids"] == export["selected_consequence_ids"]
    assert blocks["actual"]["cascade_id"] == record["cascade_id"]
    assert blocks["actual"]["contract_pass"] is True
