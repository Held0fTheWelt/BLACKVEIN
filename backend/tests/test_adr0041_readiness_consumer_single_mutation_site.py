"""ADR-0041: assert the mutating runtime readiness consumer stays a single backend anchor."""

from __future__ import annotations

import pathlib

# Only this module may call ``resolve_runtime_readiness_with_adr0041`` under ``backend/app``.
_ALLOWED_CALLER = pathlib.Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "game_routes.py"
_SYMBOL = "resolve_runtime_readiness_with_adr0041"


def test_adr0041_readiness_consumer_only_wired_in_player_session_bundle() -> None:
    app_root = pathlib.Path(__file__).resolve().parents[1] / "app"
    offenders: list[str] = []
    for path in sorted(app_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if path.resolve() == _ALLOWED_CALLER.resolve():
            continue
        text = path.read_text(encoding="utf-8")
        if _SYMBOL not in text:
            continue
        offenders.append(str(path.relative_to(app_root.parent)))
    assert not offenders, (
        f"ADR-0041 final readiness consumer must remain only in {_ALLOWED_CALLER.name}; "
        f"unexpected references in: {offenders}"
    )


def test_adr0041_mutating_consumer_path_constant_matches_game_routes() -> None:
    from ai_stack.story_runtime.runtime_readiness_consumer import ADR0041_MUTATING_FINAL_READINESS_CONSUMER_PATH

    assert ADR0041_MUTATING_FINAL_READINESS_CONSUMER_PATH == (
        "backend.app.api.v1.game_routes._player_session_bundle"
    )
