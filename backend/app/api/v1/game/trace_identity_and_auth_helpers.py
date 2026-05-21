"""Game routes implementation concern: trace identity and auth helpers.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''
def _flush_langfuse_background(adapter: Any, *, context: str) -> None:
    """Optionally flush Langfuse outside player-facing response flow."""
    if (os.getenv("WOS_LANGFUSE_REQUEST_FLUSH") or "").strip().lower() not in {"1", "true", "yes", "on"}:
        return

    def _run() -> None:
        try:
            adapter.flush()
        except Exception:
            logger.warning("Langfuse background flush failed during %s", context, exc_info=True)

    try:
        threading.Thread(target=_run, name=f"langfuse-flush-{context}", daemon=True).start()
    except Exception:
        logger.warning("Could not schedule Langfuse background flush during %s", context, exc_info=True)


class GameIdentityContext(dict):
    display_name: str
    character_id: str | None
    character_name: str | None



def _trace_classification(*, canonical_player_flow: bool, runtime_mode: str = "solo_story") -> dict[str, Any]:
    current_test = str(os.environ.get("PYTEST_CURRENT_TEST") or "").lower()
    if current_test:
        tier = "integration_test" if "integration" in current_test else "contract_test"
        return {
            "trace_origin": "pytest",
            "execution_tier": tier,
            "canonical_player_flow": canonical_player_flow,
            "test_case_id": current_test or None,
            "runtime_mode": runtime_mode,
        }
    if canonical_player_flow and is_local_langfuse_evidence_context():
        return {
            "trace_origin": "player_ui_local",
            "execution_tier": "local",
            "canonical_player_flow": canonical_player_flow,
            "test_case_id": None,
            "runtime_mode": runtime_mode,
        }
    return {
        "trace_origin": "live_ui" if canonical_player_flow else "unknown",
        "execution_tier": "live" if canonical_player_flow else "diagnostic",
        "canonical_player_flow": canonical_player_flow,
        "test_case_id": None,
        "runtime_mode": runtime_mode,
    }


def _current_user() -> User | None:
    uid = session.get("user_id")
    if uid is not None:
        return db.session.get(User, int(uid))

    try:
        verify_jwt_in_request(optional=True)
    except Exception:
        return None
    uid = get_jwt_identity()
    if uid is None:
        return None
    return db.session.get(User, int(uid))



def _require_game_user() -> User:
    user = _current_user()
    if user is None:
        raise PermissionError("Authentication required.")
    if getattr(user, "is_banned", False):
        raise PermissionError("Account is restricted.")
    return user
'''
