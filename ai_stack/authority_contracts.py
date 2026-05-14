"""Generic narrator, NPC, and player agency authority contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


AUTHORITY_CONTRACT_SCHEMA_VERSION = "authority_contract.v1"

AUTHORITY_OWNER_NARRATOR = "narrator"
AUTHORITY_OWNER_NPC = "npc"
AUTHORITY_OWNER_PLAYER = "player"
AUTHORITY_OWNER_SYSTEM = "system"

NPC_POLICY_NONE = "none"
NPC_POLICY_OPTIONAL_SOCIAL_REACTION = "optional_social_reaction"
NPC_POLICY_DIRECT_RESPONSE = "direct_response"
NPC_POLICY_OFFSCREEN_BACKGROUND = "offscreen_background"


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


@dataclass(frozen=True)
class NarratorAuthorityContract:
    schema_version: str = AUTHORITY_CONTRACT_SCHEMA_VERSION
    required: bool = False
    expected_owner: str = AUTHORITY_OWNER_NARRATOR
    required_capabilities: list[str] = field(default_factory=list)
    actual_owners: list[str] = field(default_factory=list)
    fulfilled: bool = False
    evidence_blocks: list[dict[str, Any]] = field(default_factory=list)
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class NpcAuthorityContract:
    schema_version: str = AUTHORITY_CONTRACT_SCHEMA_VERSION
    policy: str = NPC_POLICY_NONE
    allowed_actors: list[str] = field(default_factory=list)
    actual_actors: list[str] = field(default_factory=list)
    allowed_capabilities: list[str] = field(default_factory=list)
    forbidden_capabilities: list[str] = field(default_factory=list)
    takeover_detected: bool = False
    offending_blocks: list[dict[str, Any]] = field(default_factory=list)
    status: str = "not_applicable"
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class PlayerAgencyContract:
    schema_version: str = AUTHORITY_CONTRACT_SCHEMA_VERSION
    selected_human_actor_id: str | None = None
    forced_speech_detected: bool = False
    forced_decision_detected: bool = False
    agency_violation_detected: bool = False
    evidence_blocks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


def default_authority_policy() -> dict[str, Any]:
    """Return module-neutral authority defaults used when content is silent."""
    return {
        "schema_version": AUTHORITY_CONTRACT_SCHEMA_VERSION,
        "narrator_required_for": [
            "movement_transition",
            "perception_result",
            "environmental_description",
            "object_state_revealed_by_player_action",
            "opening_scenic_narration",
            "local_context_establishment",
            "offscreen_separation",
        ],
        "npc_policies": [
            NPC_POLICY_NONE,
            NPC_POLICY_OPTIONAL_SOCIAL_REACTION,
            NPC_POLICY_DIRECT_RESPONSE,
            NPC_POLICY_OFFSCREEN_BACKGROUND,
        ],
        "forbidden_npc_capabilities": [
            "npc.execute_player_action.forbidden",
            "npc.narrate_player_perception.forbidden",
            "npc.force_player_speech.forbidden",
            "npc.explain_environment_as_narrator.forbidden",
        ],
    }
