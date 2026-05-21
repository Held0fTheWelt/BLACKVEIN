"""Game routes implementation concern: runtime profile handoff validation.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''

_RUNTIME_HANDOFF_FIELDS = (
    "content_module_id",
    "runtime_profile_id",
    "runtime_module_id",
    "runtime_mode",
    "selected_player_role",
    "human_actor_id",
    "npc_actor_ids",
    "actor_lanes",
    "visitor_present",
    "content_hash",
)


def _runtime_profile_handoff_from_run_payload(run_payload: dict[str, Any]) -> dict[str, Any]:
    handoff = {key: run_payload.get(key) for key in _RUNTIME_HANDOFF_FIELDS if key in run_payload}
    if not handoff:
        return {}

    required = (
        "content_module_id",
        "runtime_profile_id",
        "runtime_module_id",
        "selected_player_role",
        "human_actor_id",
        "npc_actor_ids",
        "actor_lanes",
    )
    missing = [key for key in required if handoff.get(key) in (None, "", [], {})]
    if missing:
        raise GameServiceError(
            f"Play run is missing runtime profile handoff fields: {', '.join(missing)}",
            status_code=502,
        )

    npc_actor_ids = handoff.get("npc_actor_ids")
    actor_lanes = handoff.get("actor_lanes")
    if not isinstance(npc_actor_ids, list) or not all(isinstance(actor_id, str) and actor_id.strip() for actor_id in npc_actor_ids):
        raise GameServiceError("Play run runtime profile handoff has invalid npc_actor_ids.", status_code=502)
    if not isinstance(actor_lanes, dict):
        raise GameServiceError("Play run runtime profile handoff has invalid actor_lanes.", status_code=502)

    human_actor_id = str(handoff["human_actor_id"]).strip()

    if actor_lanes.get(human_actor_id) != "human":
        raise GameServiceError("Play run runtime profile handoff does not mark human_actor_id as human.", status_code=502)
    invalid_npcs = [actor_id for actor_id in npc_actor_ids if actor_lanes.get(actor_id) != "npc"]
    if invalid_npcs:
        raise GameServiceError(
            f"Play run runtime profile handoff does not mark NPC actors correctly: {', '.join(invalid_npcs)}",
            status_code=502,
        )
    if "visitor" in actor_lanes or "visitor" in npc_actor_ids or human_actor_id == "visitor":
        raise GameServiceError("Play run runtime profile handoff must not include visitor as a story actor.", status_code=502)
    return handoff
'''
