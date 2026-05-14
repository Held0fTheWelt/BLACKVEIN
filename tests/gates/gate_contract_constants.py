"""Published contract IDs and model tokens referenced by ``tests/gates`` (wave 03 centralization).

Values mirror production contracts; gates import these names to avoid scattered literals without
weakening assertions (each check remains explicit against the constant).
"""

from __future__ import annotations

from story_runtime_core.experience_template_models import ParticipantMode
from story_runtime_core.goc_solo_builtin_roles_rooms import goc_solo_role_templates

# --- Actor / module identity (GoC live path) ---
FORBIDDEN_RUNTIME_ACTOR_ID = "visitor"
GOD_OF_CARNAGE_CONTENT_MODULE_ID = "god_of_carnage"
GOD_OF_CARNAGE_RUNTIME_PROFILE_ID = "god_of_carnage_solo"
GOD_OF_CARNAGE_SOLO_TEMPLATE_ID = "god_of_carnage_solo"

# --- Deterministic instrumentation model IDs (cost / span contracts) ---
LDSS_DETERMINISTIC_MODEL_ID = "ldss_deterministic"
NARRATIVE_RUNTIME_AGENT_DETERMINISTIC_MODEL_ID = "narrative_runtime_agent_deterministic"


def _goc_runtime_roles_by_mode(mode: ParticipantMode) -> tuple[str, ...]:
    return tuple(role.id for role in goc_solo_role_templates() if role.mode == mode)


def _goc_runtime_actor_ids() -> tuple[str, ...]:
    return tuple(role.id for role in goc_solo_role_templates())


GOD_OF_CARNAGE_PLAYABLE_HUMAN_IDS = _goc_runtime_roles_by_mode(ParticipantMode.HUMAN)
GOD_OF_CARNAGE_RUNTIME_NPC_IDS = _goc_runtime_roles_by_mode(ParticipantMode.NPC)
GOD_OF_CARNAGE_RUNTIME_ACTOR_IDS = _goc_runtime_actor_ids()


def goc_npc_actor_ids_for_selected(selected_human_actor_id: str) -> list[str]:
    """Actor-lane oracle from the runtime profile: every non-selected actor is AI-controlled."""
    return [actor_id for actor_id in GOD_OF_CARNAGE_RUNTIME_ACTOR_IDS if actor_id != selected_human_actor_id]


def goc_role_display_name(actor_id: str) -> str:
    for role in goc_solo_role_templates():
        if role.id == actor_id:
            return role.display_name
    raise KeyError(actor_id)
