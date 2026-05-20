from __future__ import annotations

from ai_stack.contracts.callback_web_contracts import (
    CALLBACK_WEB_ASPECT_CONTRACT,
    CALLBACK_WEB_POLICY_SCHEMA_VERSION,
    CALLBACK_WEB_VALIDATION_SCHEMA_VERSION,
    callback_web_aspect_blocks,
    callback_web_bounds_from_policy,
    normalize_callback_web_policy,
    validate_callback_web_record,
)
from story_runtime_core.callbacks import (
    CALLBACK_EDGE_KIND_REPEATED_CONTINUITY_CLASS,
    CALLBACK_WEB_RECORD_SCHEMA_VERSION,
    build_callback_web_record,
    build_graph_callback_web_export,
)


SESSION_ID = "callback-contract-session"
CONTINUITY_CLASS = "continuity.fixture"


def _history_row(turn_number: int) -> dict:
    return {
        "canonical_turn_id": f"{SESSION_ID}:turn:{turn_number}",
        "turn_number": turn_number,
        "narrative_commit": {
            "turn_number": turn_number,
            "committed_scene_id": "scene.fixture",
            "planner_truth": {
                "continuity_impacts": [{"class": CONTINUITY_CLASS}],
                "primary_responder_id": "actor.fixture",
            },
        },
    }


def _callback_record() -> dict:
    return build_callback_web_record(
        story_session_id=SESSION_ID,
        module_id="module.fixture",
        runtime_profile_id="profile.fixture",
        history=[_history_row(1), _history_row(2)],
        bounds={"max_edges": 8, "max_observations": 4, "max_evidence_refs": 8},
    )


def test_callback_web_policy_normalizes_bounded_contract() -> None:
    policy = normalize_callback_web_policy(
        {
            "enabled": True,
            "max_edges": 999,
            "max_observations": 1,
            "max_graph_edges": 99,
            "max_evidence_refs_per_candidate": 99,
            "allowed_continuity_classes": [CONTINUITY_CLASS, CONTINUITY_CLASS],
        }
    )

    assert policy["schema_version"] == CALLBACK_WEB_POLICY_SCHEMA_VERSION
    assert policy["enabled"] is True
    assert policy["max_edges"] == 500
    assert policy["max_observations"] == 4
    assert policy["max_graph_edges"] == 16
    assert policy["max_evidence_refs"] == 32
    assert policy["allowed_continuity_classes"] == [CONTINUITY_CLASS]
    assert callback_web_bounds_from_policy(policy) == {
        "max_edges": policy["max_edges"],
        "max_observations": policy["max_observations"],
        "max_evidence_refs": policy["max_evidence_refs"],
    }


def test_callback_web_validation_and_aspect_blocks_use_contract_fields() -> None:
    record = _callback_record()
    policy = normalize_callback_web_policy(
        {
            "enabled": True,
            "max_edges": 8,
            "max_observations": 4,
            "max_graph_edges": 1,
            "max_evidence_refs": 8,
        }
    )

    validation = validate_callback_web_record(record, policy=policy)
    graph_export = build_graph_callback_web_export(record, max_edges=policy["max_graph_edges"])
    blocks = callback_web_aspect_blocks(
        record=record,
        graph_export=graph_export,
        validation=validation,
        policy=policy,
    )

    assert record["schema_version"] == CALLBACK_WEB_RECORD_SCHEMA_VERSION
    assert validation["schema_version"] == CALLBACK_WEB_VALIDATION_SCHEMA_VERSION
    assert validation["status"] == "passed"
    assert validation["contract_pass"] is True
    assert validation["edge_count"] == len(record["edges"])
    assert graph_export["selected_callback_kind"] == CALLBACK_EDGE_KIND_REPEATED_CONTINUITY_CLASS
    assert blocks["contract"] == CALLBACK_WEB_ASPECT_CONTRACT
    assert blocks["actual"]["contract_pass"] is True
    assert blocks["actual"]["graph_edge_count"] == graph_export["exported_edge_count"] == 1
    assert blocks["selected"]["selected_callback_kind"] == CALLBACK_EDGE_KIND_REPEATED_CONTINUITY_CLASS


def test_callback_web_validation_rejects_authority_mutation_and_unbounded_edges() -> None:
    record = _callback_record()
    bad_record = dict(record)
    bad_record["non_authoritative"] = False
    bad_record["edges"] = list(record["edges"]) * 9
    policy = normalize_callback_web_policy(
        {
            "enabled": True,
            "max_edges": 8,
            "max_observations": 4,
            "max_evidence_refs": 8,
        }
    )

    validation = validate_callback_web_record(bad_record, policy=policy)

    assert validation["status"] == "failed"
    assert validation["contract_pass"] is False
    assert set(validation["failure_codes"]) == {
        "callback_authority_mutation",
        "callback_unbounded_evidence",
    }
