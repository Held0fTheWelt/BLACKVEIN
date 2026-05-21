"""Phase 6B-1 default-on flag matrix.

Pins the five W5 Actor Tracking consumer flags as default-on with explicit
opt-out semantics. These tests are deliberately scoped to the resolver
functions themselves so they can run independently of the StoryRuntimeManager
and World-Engine PYTHONPATH; runtime wiring is covered by the targeted
narrator / player-view / NPC / validation / Director tests under
``world-engine/tests/`` and ``ai_stack/tests/``.

Assertions are semantic: each test verifies the actual boolean returned by
the live resolver, not just the presence of a flag key.
"""

from __future__ import annotations

import pytest

from ai_stack.actor_tracking.diagnostics import (
    _flag_enabled,
    w5_projection_flag_states,
)
from ai_stack.actor_tracking.validation import w5_ast_validation_enabled


W5_FLAGS = (
    "W5_AST_DIRECTOR_PROJECTION_ENABLED",
    "W5_AST_NARRATOR_PROJECTION_ENABLED",
    "W5_AST_NPC_PROJECTION_ENABLED",
    "W5_AST_VALIDATION_ENABLED",
    "W5_AST_FRONTEND_PLAYER_VIEW_ENABLED",
)


def _clear_w5_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in W5_FLAGS:
        monkeypatch.delenv(name, raising=False)


def test_w5_validation_resolver_is_default_on_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("W5_AST_VALIDATION_ENABLED", raising=False)
    assert w5_ast_validation_enabled() is True


@pytest.mark.parametrize("opt_out_value", ["0", "false", "no", "off", "False", "OFF"])
def test_w5_validation_resolver_explicit_opt_out_disables(
    monkeypatch: pytest.MonkeyPatch, opt_out_value: str
) -> None:
    monkeypatch.setenv("W5_AST_VALIDATION_ENABLED", opt_out_value)
    assert w5_ast_validation_enabled() is False


@pytest.mark.parametrize("opt_in_value", ["1", "true", "yes", "on", "True", "YES"])
def test_w5_validation_resolver_explicit_opt_in_still_enabled(
    monkeypatch: pytest.MonkeyPatch, opt_in_value: str
) -> None:
    monkeypatch.setenv("W5_AST_VALIDATION_ENABLED", opt_in_value)
    assert w5_ast_validation_enabled() is True


@pytest.mark.parametrize(
    "flag_name",
    [
        "W5_AST_NARRATOR_PROJECTION_ENABLED",
        "W5_AST_DIRECTOR_PROJECTION_ENABLED",
        "W5_AST_NPC_PROJECTION_ENABLED",
        "W5_AST_FRONTEND_PLAYER_VIEW_ENABLED",
    ],
)
def test_projection_flag_helper_default_on_when_env_unset(
    monkeypatch: pytest.MonkeyPatch, flag_name: str
) -> None:
    monkeypatch.delenv(flag_name, raising=False)
    assert _flag_enabled(flag_name) is True


@pytest.mark.parametrize(
    "flag_name",
    [
        "W5_AST_NARRATOR_PROJECTION_ENABLED",
        "W5_AST_DIRECTOR_PROJECTION_ENABLED",
        "W5_AST_NPC_PROJECTION_ENABLED",
        "W5_AST_FRONTEND_PLAYER_VIEW_ENABLED",
    ],
)
@pytest.mark.parametrize("opt_out_value", ["0", "false", "no", "off"])
def test_projection_flag_helper_explicit_opt_out_disables(
    monkeypatch: pytest.MonkeyPatch, flag_name: str, opt_out_value: str
) -> None:
    monkeypatch.setenv(flag_name, opt_out_value)
    assert _flag_enabled(flag_name) is False


def test_w5_projection_flag_states_reports_all_default_on_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_w5_env(monkeypatch)
    monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
    states = w5_projection_flag_states()
    # Semantic: all five W5 consumer flags must be default-on. The
    # Phase 6B-3B opt-in narrator-strict flag is reported alongside as
    # default-off.
    assert states == {
        "narrator": True,
        "narrator_strict": False,
        "director": True,
        "npc": True,
        "player_shell": True,
        "validation": True,
    }


def test_w5_projection_flag_states_honors_per_flag_explicit_opt_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_w5_env(monkeypatch)
    monkeypatch.setenv("W5_AST_NARRATOR_PROJECTION_ENABLED", "0")
    monkeypatch.setenv("W5_AST_VALIDATION_ENABLED", "off")
    states = w5_projection_flag_states()
    assert states["narrator"] is False
    assert states["validation"] is False
    # The other three remain default-on.
    assert states["director"] is True
    assert states["npc"] is True
    assert states["player_shell"] is True


def test_director_projection_resolver_is_default_on_via_public_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The SOURCE_LINES-assembled Director resolver must default-on.

    Verifies the public.py-assembled runtime executor exposes a working
    ``w5_ast_director_projection_enabled`` callable that follows the
    Phase 6B-1 default-on contract.
    """

    monkeypatch.delenv("W5_AST_DIRECTOR_PROJECTION_ENABLED", raising=False)
    from ai_stack.langgraph.runtime_executor import public as runtime_public

    assert runtime_public.w5_ast_director_projection_enabled() is True
    monkeypatch.setenv("W5_AST_DIRECTOR_PROJECTION_ENABLED", "0")
    assert runtime_public.w5_ast_director_projection_enabled() is False


def test_npc_projection_resolver_is_default_on_via_public_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The SOURCE_LINES-assembled NPC resolver must default-on."""

    monkeypatch.delenv("W5_AST_NPC_PROJECTION_ENABLED", raising=False)
    from ai_stack.langgraph.runtime_executor import public as runtime_public

    assert runtime_public.w5_ast_npc_projection_enabled() is True
    monkeypatch.setenv("W5_AST_NPC_PROJECTION_ENABLED", "off")
    assert runtime_public.w5_ast_npc_projection_enabled() is False
