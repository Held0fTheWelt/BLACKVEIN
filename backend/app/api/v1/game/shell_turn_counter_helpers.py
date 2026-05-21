"""Game routes implementation concern: shell turn counter helpers.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''

def _shell_committed_turn_display_counter(state: dict[str, Any]) -> int:
    """Return the count of **committed canonical turns** for the play shell (ADR-0038 Phase A).

    World-Engine ``turn_counter`` advances only on ``execute_turn`` (player path); Turn 0 opening is
    committed to ``session.history`` without incrementing ``turn_counter``, which produced
    ``committed turns 0`` in the shell while ``story_window`` already showed opening content.

    Prefer ``history_count`` (``len(session.history)``) when present — it is the row-count truth
    surface for canonical commits. Then ``total_canonical_turns`` / ``committed_canonical_turn_count``,
    then ``turn_counter`` for older play-service payloads.
    """
    hc = state.get("history_count")
    if isinstance(hc, int) and hc >= 0:
        return hc
    total = state.get("total_canonical_turns")
    if isinstance(total, int) and total >= 0:
        return total
    raw = state.get("committed_canonical_turn_count")
    if isinstance(raw, int) and raw >= 0:
        return raw
    tc = state.get("turn_counter")
    if isinstance(tc, int) and tc >= 0:
        return tc
    return 0


def _shell_turn_counter_projection(state: dict[str, Any]) -> dict[str, Any]:
    """Project opening vs player canonical counts for shell / API parity (TURN-COUNTER-STATE-PROJECTION-01).

    World-Engine is authoritative when it emits explicit fields; otherwise derive a conservative
    estimate from ``history_count`` for older payloads (assume at most one opening row).
    """
    opening = state.get("opening_committed")
    if not isinstance(opening, bool):
        opening = bool(
            isinstance(state.get("history_count"), int) and int(state["history_count"]) >= 1
        )
    player_turns = state.get("player_committed_turns")
    if not isinstance(player_turns, int) or player_turns < 0:
        hc = state.get("history_count")
        if isinstance(hc, int) and hc >= 0:
            player_turns = max(0, hc - 1)
        else:
            player_turns = 0
    total = state.get("total_canonical_turns")
    if not isinstance(total, int) or total < 0:
        hc = state.get("history_count")
        if isinstance(hc, int) and hc >= 0:
            total = hc
        else:
            cc = state.get("committed_canonical_turn_count")
            total = int(cc) if isinstance(cc, int) and cc >= 0 else _shell_committed_turn_display_counter(state)
    latest = state.get("latest_canonical_turn_id")
    if latest is not None and not isinstance(latest, str):
        latest = str(latest).strip() or None
    elif isinstance(latest, str):
        latest = latest.strip() or None
    last_turn = state.get("last_committed_turn")
    if not latest and isinstance(last_turn, dict):
        lid = str(last_turn.get("canonical_turn_id") or "").strip()

        latest = lid or None
    return {
        "opening_committed": opening,
        "player_committed_turns": player_turns,
        "total_canonical_turns": total,
        "latest_canonical_turn_id": latest,
    }

'''
