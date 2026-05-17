"""Dispatch path guards for the director capability manager."""

from __future__ import annotations

from ai_stack.director_capability_manager import (
    DEFAULT_MAX_CAPABILITY_PATH_DEPTH,
    audit_director_capability_paths,
    executable_capabilities_from_manager_plan,
)
from ai_stack.dramatic_capability_contracts import (
    NPC_DIRECT_ANSWER_ALLOWED,
    NPC_SOCIAL_REACTION_OPTIONAL,
)


def test_capability_audit_accepts_individual_terminal_paths() -> None:
    audit = audit_director_capability_paths(
        selected_capabilities=[
            NPC_SOCIAL_REACTION_OPTIONAL,
            NPC_DIRECT_ANSWER_ALLOWED,
        ],
        capability_steps=[
            {"capability": NPC_SOCIAL_REACTION_OPTIONAL, "mode": "required", "source": "speech_policy"},
            {"capability": NPC_DIRECT_ANSWER_ALLOWED, "mode": "optional", "source": "speech_policy"},
        ],
    )

    assert audit["status"] == "passed"
    assert audit["dispatch_queue"] == [NPC_SOCIAL_REACTION_OPTIONAL, NPC_DIRECT_ANSWER_ALLOWED]
    assert len(audit["paths"]) == 2
    for path in audit["paths"]:
        assert path["status"] == "passed"
        assert path["cycle_detected"] is False
        assert path["depth"] <= DEFAULT_MAX_CAPABILITY_PATH_DEPTH
        assert path["terminal_node"] == "terminal"


def test_capability_audit_rejects_cycle_in_single_path() -> None:
    audit = audit_director_capability_paths(
        selected_capabilities=[NPC_SOCIAL_REACTION_OPTIONAL],
        path_registry={
            NPC_SOCIAL_REACTION_OPTIONAL: (
                "director_tick",
                "npc.response",
                "director_tick",
                "terminal",
            )
        },
    )

    assert audit["status"] == "failed"
    assert audit["dispatch_queue"] == []
    assert audit["paths"][0]["cycle_detected"] is True
    assert "cycle_detected" in audit["paths"][0]["reason_codes"]


def test_capability_audit_rejects_suppressed_capability() -> None:
    audit = audit_director_capability_paths(
        selected_capabilities=[NPC_DIRECT_ANSWER_ALLOWED],
        suppressed_capabilities=[NPC_DIRECT_ANSWER_ALLOWED],
    )

    assert audit["status"] == "failed"
    assert audit["executable_capabilities"] == []
    assert "suppressed_capability_selected" in audit["paths"][0]["reason_codes"]


def test_capability_audit_rejects_unregistered_capability_path() -> None:
    audit = audit_director_capability_paths(
        selected_capabilities=["npc.unregistered.branch"],
    )

    assert audit["status"] == "failed"
    assert audit["dispatch_queue"] == []
    assert audit["rejected_capabilities"] == ["npc.unregistered.branch"]
    assert "capability_not_enabled" in audit["paths"][0]["reason_codes"]
    assert "missing_dispatch_path" in audit["paths"][0]["reason_codes"]


def test_executable_capabilities_fall_back_for_older_plans() -> None:
    plan = {
        "selected_capabilities": [NPC_SOCIAL_REACTION_OPTIONAL, NPC_SOCIAL_REACTION_OPTIONAL],
    }

    assert executable_capabilities_from_manager_plan(plan) == [NPC_SOCIAL_REACTION_OPTIONAL]
