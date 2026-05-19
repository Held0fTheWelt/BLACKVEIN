"""PR-A live smoke: Resolver → Director → Narrator thin path (A-10).

Runs against a real stack (``docker-up.py``). No mocks — exercises world-engine
turn execution with live LLM when the play service is configured for it.

Enable explicitly::

    WOS_THIN_PATH_LIVE_SMOKE=1 python tests/run_tests.py tests/smoke/test_thin_path_pr_a_live_smoke.py -v

Environment (defaults match local docker-compose host ports):

- ``WORLD_ENGINE_URL`` — default ``http://127.0.0.1:8001``
- ``PLAY_SERVICE_INTERNAL_API_KEY`` — internal play-service key
"""

from __future__ import annotations

import os
import re
import time
from typing import Any

import pytest
import requests

pytestmark = pytest.mark.smoke

WORLD_ENGINE_URL = os.getenv("WORLD_ENGINE_URL", "http://127.0.0.1:8001").rstrip("/")
INTERNAL_API_KEY = os.getenv("PLAY_SERVICE_INTERNAL_API_KEY", "internal-api-key-for-ops")
LIVE_ENABLED = os.getenv("WOS_THIN_PATH_LIVE_SMOKE", "").strip().lower() in {"1", "true", "yes"}

_GOC_PROJECTION: dict[str, Any] = {
    "module_id": "god_of_carnage",
    "runtime_profile_id": "god_of_carnage_solo",
    "runtime_module_id": "solo_story_runtime",
    "runtime_mode": "solo_story",
    "start_scene_id": "scene_1",
    "scenes": [],
    "selected_player_role": "annette_reille",
    "human_actor_id": "annette_reille",
    "npc_actor_ids": ["alain_reille", "veronique_vallon", "michel_longstreet"],
    "actor_lanes": {
        "annette_reille": "human",
        "alain_reille": "npc",
        "veronique_vallon": "npc",
        "michel_longstreet": "npc",
    },
}

# Acceptance inputs from RESOLVER_DIRECTOR_NARRATOR_THIN_PATH_PLAN.md §3 PR-A
_SMOKE_CASES: list[dict[str, Any]] = [
    {
        "id": "movement_kitchen",
        "player_input": "Gehe in die Küche",
        "expect_capability": "narrator.location_transition.describe",
        "expect_kanon_break": False,
        "expect_committed": True,
    },
    {
        "id": "movement_bathroom",
        "player_input": "Ich gehe ins Bad",
        "expect_capability": "narrator.location_transition.describe",
        "expect_kanon_break": False,
        "expect_committed": True,
    },
    {
        "id": "movement_return_living_room",
        "player_input": "Ich gehe zurück ins Wohnzimmer",
        "expect_capability": "narrator.location_transition.describe",
        "expect_kanon_break": False,
        "expect_committed": True,
    },
    {
        "id": "movement_sneak_kitchen",
        "player_input": "Ich schleiche in Richtung Küche",
        "expect_capability": "narrator.location_transition.describe",
        "expect_kanon_break": False,
        "expect_committed": True,
    },
    {
        "id": "kanon_break_wall",
        "player_input": "Ich gehe durch die Wand",
        "expect_capability": "narrator.kanon_break_refusal.describe",
        "expect_kanon_break": True,
        "expect_committed": False,
    },
]

_ENGLISH_BLEED_RE = re.compile(
    r"\b(A connected domestic|A private regrouping|service room|regrouping space)\b",
    re.IGNORECASE,
)


def _headers() -> dict[str, str]:
    return {"X-Play-Service-Key": INTERNAL_API_KEY, "Content-Type": "application/json"}


def _stack_reachable() -> bool:
    try:
        resp = requests.get(f"{WORLD_ENGINE_URL}/api/health", timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def _create_de_session() -> str:
    resp = requests.post(
        f"{WORLD_ENGINE_URL}/api/story/sessions",
        headers=_headers(),
        json={
            "module_id": "god_of_carnage",
            "runtime_projection": _GOC_PROJECTION,
            "session_output_language": "de",
        },
        timeout=60,
    )
    resp.raise_for_status()
    session_id = resp.json().get("session_id")
    assert isinstance(session_id, str) and session_id.strip()
    return session_id


def _run_opening(session_id: str) -> None:
    resp = requests.post(
        f"{WORLD_ENGINE_URL}/api/story/sessions/{session_id}/opening",
        headers=_headers(),
        json={},
        timeout=180,
    )
    resp.raise_for_status()


def _execute_turn(session_id: str, player_input: str) -> dict[str, Any]:
    last_exc: requests.RequestException | None = None
    for attempt in range(2):
        try:
            resp = requests.post(
                f"{WORLD_ENGINE_URL}/api/story/sessions/{session_id}/turns",
                headers=_headers(),
                json={"player_input": player_input},
                timeout=180,
            )
        except requests.RequestException as exc:
            last_exc = exc
            if attempt == 0:
                _wait_for_stack(attempts=6, delay_s=10.0)
                continue
            raise
        if resp.status_code >= 500:
            pytest.fail(f"turn HTTP {resp.status_code}: {resp.text[:400]}")
        body = resp.json()
        turn = body.get("turn") if isinstance(body.get("turn"), dict) else body
        assert isinstance(turn, dict), f"unexpected turn payload: {body!r}"
        return turn
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("unreachable")


def _path_summary(turn: dict[str, Any]) -> dict[str, Any]:
    ps = turn.get("observability_path_summary")
    if isinstance(ps, dict):
        return ps
    diag = turn.get("diagnostics")
    if isinstance(diag, dict) and isinstance(diag.get("observability_path_summary"), dict):
        return diag["observability_path_summary"]
    return {}


def _visible_german_text(turn: dict[str, Any]) -> str:
    chunks: list[str] = []
    bundle = turn.get("visible_output_bundle")
    if isinstance(bundle, dict):
        for block in bundle.get("scene_blocks") or []:
            if isinstance(block, dict):
                chunks.append(str(block.get("text") or ""))
        chunks.extend(str(x) for x in bundle.get("gm_narration") or [])
    chunks.append(str(turn.get("player_visible_message") or ""))
    return " ".join(c for c in chunks if c.strip())


def _assert_thin_path_invariants(path_summary: dict[str, Any], *, expect_capability: str) -> None:
    plan = path_summary.get("realization_plan") or {}
    assert plan.get("schema_version") == "realization_plan.v1"
    caps = plan.get("capabilities_selected") or path_summary.get("selected_capabilities") or []
    assert caps, "selected_capabilities must be non-empty on thin path"
    assert expect_capability in caps
    used = path_summary.get("realize_via_capabilities_used_capability")
    assert used == expect_capability, f"used capability {used!r} != {expect_capability!r}"
    assert path_summary.get("director_path_mode") in {
        "director_realization_composer",
        None,
    } or isinstance(path_summary.get("realization_plan"), dict)
    nodes = path_summary.get("nodes_executed") or []
    for required in (
        "resolve_player_action",
        "director_compose_realization",
        "realize_via_capabilities",
    ):
        assert required in nodes, f"missing thin-path node {required} in {nodes}"
    assert "authoritative_action_resolution" not in nodes


def _wait_for_stack(*, attempts: int = 12, delay_s: float = 5.0) -> None:
    for _ in range(attempts):
        if _stack_reachable():
            return
        time.sleep(delay_s)
    pytest.skip(f"World-engine not reachable at {WORLD_ENGINE_URL} after {attempts} attempts")


@pytest.fixture
def live_session_id() -> str:
    if not LIVE_ENABLED:
        pytest.skip("Set WOS_THIN_PATH_LIVE_SMOKE=1 to run PR-A live smoke")
    _wait_for_stack()
    session_id = _create_de_session()
    _run_opening(session_id)
    return session_id


@pytest.mark.parametrize("case", _SMOKE_CASES, ids=[c["id"] for c in _SMOKE_CASES])
def test_pr_a_thin_path_live_smoke_case(live_session_id: str, case: dict[str, Any]) -> None:
    """Each acceptance input must traverse Director → realize and avoid English bleed."""
    _wait_for_stack()
    turn = _execute_turn(live_session_id, case["player_input"])
    path_summary = _path_summary(turn)

    _assert_thin_path_invariants(
        path_summary,
        expect_capability=str(case["expect_capability"]),
    )

    if case["expect_kanon_break"]:
        assert path_summary.get("kanon_break") is True
        assert turn.get("turn_status") != "hard_failure"
    else:
        assert path_summary.get("kanon_break") is not True
        if case.get("expect_committed"):
            assert turn.get("ok") is True or turn.get("turn_status") == "committed"

    visible = _visible_german_text(turn)
    if visible and case["expect_capability"].startswith("narrator."):
        assert not _ENGLISH_BLEED_RE.search(visible), (
            f"English bleed in visible text: {visible[:200]!r}"
        )
        assert any(ch in visible for ch in "äöüßÄÖÜ"), (
            "expected German visible output (umlaut or eszett) for DE session"
        )

    time.sleep(0.5)
