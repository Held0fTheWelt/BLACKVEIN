from __future__ import annotations

from ai_stack.hierarchical_memory_contracts import (
    build_hierarchical_memory_write,
    merge_hierarchical_memory_snapshot,
    normalize_hierarchical_memory_policy,
    project_hierarchical_memory_context,
)
from ai_stack.runtime_aspect_ledger import (
    ASPECT_BEAT,
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_COMMIT,
    initialize_runtime_aspect_ledger,
    make_aspect_record,
    set_aspect_record,
)


def _policy() -> dict:
    return {
        "schema_version": "hierarchical_memory_policy.v1",
        "enabled": True,
        "write_requires_committed_turn": True,
        "allow_uncommitted_writes": False,
        "tiers": [
            {"id": "turn", "enabled": True, "max_items": 4, "max_context_items": 2},
            {"id": "session", "enabled": True, "max_items": 3, "max_context_items": 2},
            {"id": "actor", "enabled": True, "max_items": 4, "max_context_items": 2},
            {"id": "module", "enabled": True, "max_items": 1, "max_context_items": 1},
        ],
    }


def _ledger() -> dict:
    ledger = initialize_runtime_aspect_ledger(
        session_id="session-memory",
        module_id="module_alpha",
        runtime_profile_id="profile_alpha",
        turn_number=1,
        turn_kind="player",
        raw_player_input="A secret-looking player sentence must not enter memory.",
        turn_id="session-memory:turn:1",
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_BEAT,
        make_aspect_record(
            applicable=True,
            status="passed",
            selected={"selected_beat_id": "beat_alpha"},
            actual={"realized": True},
            source="runtime",
        ),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_CAPABILITY_SELECTION,
        make_aspect_record(
            applicable=True,
            status="passed",
            selected={"selected_capabilities": ["player.speech.request"]},
            actual={"realized_capabilities": ["player.speech.request"]},
            source="runtime",
        ),
    )
    return set_aspect_record(
        ledger,
        ASPECT_COMMIT,
        make_aspect_record(
            applicable=True,
            status="passed",
            actual={"commit_applied": True},
            source="runtime",
        ),
    )


def _committed_turn() -> dict:
    return {
        "canonical_turn_id": "session-memory:turn:1",
        "module_id": "module_alpha",
        "runtime_profile_id": "profile_alpha",
        "turn_number": 1,
        "turn_outcome": "ok",
        "model_prompt": "this prompt must never be stored",
        "narrative_commit": {
            "allowed": True,
            "situation_status": "continue",
            "committed_scene_id": "scene_alpha",
            "committed_consequences": ["bounded consequence token"],
            "open_pressures": ["bounded pressure token"],
        },
        "actor_turn_summary": {
            "primary_responder_id": "actor_alpha",
            "secondary_responder_ids": ["actor_beta"],
            "spoken_line_count": 1,
            "action_line_count": 0,
        },
        "turn_aspect_ledger": _ledger(),
    }


def test_hierarchical_memory_policy_is_json_safe_and_module_neutral() -> None:
    policy = normalize_hierarchical_memory_policy(_policy())

    assert policy["schema_version"] == "hierarchical_memory_policy.v1"
    assert policy["enabled"] is True
    assert [tier["id"] for tier in policy["tiers"]][:3] == ["turn", "session", "actor"]
    assert "god_of_carnage" not in str(policy)


def test_memory_write_uses_committed_turn_evidence_without_raw_prompt_payloads() -> None:
    write = build_hierarchical_memory_write(
        memory_policy=_policy(),
        committed_turn=_committed_turn(),
        runtime_policy={"module_id": "module_alpha", "content_sources": ["module"]},
    )

    assert write["status"] == "passed"
    assert write["source_canonical_turn_id"] == "session-memory:turn:1"
    assert write["written_items"]
    payload = str(write)
    assert "this prompt must never be stored" not in payload
    assert "secret-looking player sentence" not in payload
    assert all("canonical_turn_id" not in str(item.get("data")) for item in write["written_items"])


def test_memory_write_skips_recoverable_turns_without_creating_truth() -> None:
    turn = {**_committed_turn(), "turn_outcome": "recoverable_rejection", "recoverable_outcome": True}

    write = build_hierarchical_memory_write(
        memory_policy=_policy(),
        committed_turn=turn,
        runtime_policy={"module_id": "module_alpha"},
    )

    assert write["status"] == "not_applicable"
    assert write["write_allowed"] is False
    assert write["written_items"] == []
    assert write["uncommitted_write_detected"] is False


def test_memory_snapshot_merge_and_context_projection_are_bounded() -> None:
    write = build_hierarchical_memory_write(
        memory_policy=_policy(),
        committed_turn=_committed_turn(),
        runtime_policy={"module_id": "module_alpha", "content_sources": ["module"]},
    )

    snapshot = merge_hierarchical_memory_snapshot(
        prior_snapshot=None,
        write_result=write,
        memory_policy=_policy(),
        module_id="module_alpha",
        runtime_profile_id="profile_alpha",
    )
    context = project_hierarchical_memory_context(snapshot=snapshot, memory_policy=_policy())

    assert snapshot["item_count"] >= 3
    assert context["bounded"] is True
    assert context["memory_present"] is True
    assert context["item_count"] <= context["available_item_count"]
    assert context["context_lines"]
