"""Game routes implementation concern: session slot and run identity helpers.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''



def _player_session_slot_key(run_id: str) -> str:
    digest = hashlib.sha1(run_id.encode("utf-8")).hexdigest()[:24]
    return f"player-{digest}"


def _find_player_session_slot(user_id: int, run_id: str) -> GameSaveSlot | None:
    return db.session.scalar(
        select(GameSaveSlot).where(
            GameSaveSlot.user_id == user_id,
            GameSaveSlot.slot_key == _player_session_slot_key(run_id),
        )
    )


def _run_template_id(payload: dict[str, Any]) -> str:
    run = payload.get("run") if isinstance(payload.get("run"), dict) else {}
    template = payload.get("template") if isinstance(payload.get("template"), dict) else {}
    template_id = str(run.get("template_id") or template.get("id") or payload.get("template_id") or "").strip()
    if not template_id:
        raise GameServiceError("Play run did not include a template id.", status_code=502)
    return template_id


def _run_id(payload: dict[str, Any]) -> str:
    run = payload.get("run") if isinstance(payload.get("run"), dict) else {}
    run_id = str(run.get("id") or payload.get("run_id") or "").strip()
    if not run_id:
        raise GameServiceError("Play run did not include a run id.", status_code=502)
    return run_id


def _story_window_from_state(state: dict[str, Any]) -> dict[str, Any]:
    story_window = state.get("story_window") if isinstance(state.get("story_window"), dict) else {}
    entries = story_window.get("entries") if isinstance(story_window.get("entries"), list) else []
    return {
        "contract": story_window.get("contract") or "authoritative_story_window_v1",
        "source": story_window.get("source") or "world_engine_story_runtime",
        "entries": entries,
        "entry_count": len(entries),
        "latest_entry": entries[-1] if entries else None,
    }
'''
