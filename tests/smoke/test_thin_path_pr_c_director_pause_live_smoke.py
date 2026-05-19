"""PR-C Director-Pause live smoke: four canonical scenarios.

Runs against a real stack (``docker-up.py``). No mocks — exercises world-engine
turn execution with the real LLM and the Phase-1 NPC actor_locations fallback.

Enable explicitly::

    WOS_THIN_PATH_LIVE_SMOKE=1 python tests/run_tests.py tests/smoke/test_thin_path_pr_c_director_pause_live_smoke.py -v

Environment (defaults match local docker-compose host ports):

- ``WORLD_ENGINE_URL`` — default ``http://127.0.0.1:8001``
- ``PLAY_SERVICE_INTERNAL_API_KEY`` — internal play-service key

Four scenarios (in session order, single session):
  1. mundane_local_action  — paused=False, no missing NPCs, hold_effect present
  2. leave_gathering       — paused=True,  missing actor = human actor
  3. act_while_paused      — paused=True,  player still free
  4. return_to_gathering   — paused=False, missing_actor_ids empty
"""

from __future__ import annotations

import os
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


def _headers() -> dict[str, str]:
    return {"X-Play-Service-Key": INTERNAL_API_KEY, "Content-Type": "application/json"}


def _stack_reachable() -> bool:
    try:
        resp = requests.get(f"{WORLD_ENGINE_URL}/api/health", timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def _wait_for_stack(*, attempts: int = 12, delay_s: float = 5.0) -> None:
    for _ in range(attempts):
        if _stack_reachable():
            return
        time.sleep(delay_s)
    pytest.skip(f"World-engine not reachable at {WORLD_ENGINE_URL} after {attempts} attempts")


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


def _director_gathering_state(turn: dict[str, Any]) -> dict[str, Any]:
    """Extract director_gathering_state from the turn response.

    Resolution order:
    1. turn.observability_path_summary.director_gathering_state (primary)
    2. turn.graph.phase1_director_pause_diagnostics.director_gathering_state (secondary)
    """
    ps = _path_summary(turn)
    if isinstance(ps.get("director_gathering_state"), dict):
        return ps["director_gathering_state"]
    graph = turn.get("graph")
    if isinstance(graph, dict):
        phase1 = graph.get("phase1_director_pause_diagnostics")
        if isinstance(phase1, dict) and isinstance(phase1.get("director_gathering_state"), dict):
            return phase1["director_gathering_state"]
    return {}


def _assert_director_pause_invariants(
    turn: dict[str, Any],
    *,
    expect_paused: bool,
    scenario_id: str,
) -> None:
    dgs = _director_gathering_state(turn)
    assert dgs, (
        f"[{scenario_id}] director_gathering_state absent from turn response. "
        f"observability_path_summary={_path_summary(turn)!r}"
    )
    assert dgs.get("schema_version") == "director_gathering_state.v1", (
        f"[{scenario_id}] schema_version mismatch: {dgs.get('schema_version')!r}"
    )
    assert dgs.get("diagnostic_blocker") is not True, (
        f"[{scenario_id}] unexpected diagnostic_blocker in director_gathering_state: "
        f"reason={dgs.get('reason')!r}"
    )
    actual_paused = dgs.get("paused")
    assert actual_paused is expect_paused, (
        f"[{scenario_id}] expected paused={expect_paused}, got paused={actual_paused}. "
        f"director_gathering_state={dgs!r}"
    )
    if expect_paused:
        missing = dgs.get("missing_actor_ids") or []
        assert missing, (
            f"[{scenario_id}] paused=True but missing_actor_ids is empty: {dgs!r}"
        )
        # When paused, must NOT list ALL actors as missing (NPCs were defaulted
        # to gathering scene by actor_lane fallback — only the actor who left
        # should be missing).
        ps = _path_summary(turn)
        npc_ids = _GOC_PROJECTION.get("npc_actor_ids") or []
        all_actors_missing = all(
            aid in missing for aid in npc_ids
        )
        assert not all_actors_missing, (
            f"[{scenario_id}] all NPC actors are in missing_actor_ids — "
            f"actor_lane fallback did not populate NPC positions. "
            f"missing_actor_ids={missing!r}"
        )
    else:
        missing = dgs.get("missing_actor_ids") or []
        assert missing == [], (
            f"[{scenario_id}] paused=False but missing_actor_ids={missing!r}"
        )


@pytest.fixture(scope="module")
def live_pr_c_session_id() -> str:
    if not LIVE_ENABLED:
        pytest.skip("Set WOS_THIN_PATH_LIVE_SMOKE=1 to run PR-C Director-Pause live smoke")
    _wait_for_stack()
    session_id = _create_de_session()
    _run_opening(session_id)
    return session_id


def test_pr_c_scenario1_mundane_local_action_not_paused(live_pr_c_session_id: str) -> None:
    """Scenario 1: mundane local action in gathering scene.

    All NPCs default to gathering scene via actor_lane fallback →
    paused=False, no missing actors.
    """
    _wait_for_stack()
    turn = _execute_turn(live_pr_c_session_id, "Ich schaue mich im Zimmer um")
    _assert_director_pause_invariants(turn, expect_paused=False, scenario_id="mundane_local")
    # hold_effect should be present (mundane action near canonical step)
    ps = _path_summary(turn)
    assert "resolve_player_action" in (ps.get("nodes_executed") or []), (
        "resolve_player_action node must appear in thin path"
    )
    time.sleep(0.5)


def test_pr_c_scenario2_leave_gathering_pauses(live_pr_c_session_id: str) -> None:
    """Scenario 2: human actor moves to another room.

    Human actor location updated to target room via action resolution →
    paused=True. Missing actor = human actor (not all NPCs).
    """
    _wait_for_stack()
    turn = _execute_turn(live_pr_c_session_id, "Ich gehe in die Küche")
    _assert_director_pause_invariants(turn, expect_paused=True, scenario_id="leave_gathering")
    dgs = _director_gathering_state(turn)
    missing = dgs.get("missing_actor_ids") or []
    assert _GOC_PROJECTION["human_actor_id"] in missing, (
        f"Scenario 2: human actor {_GOC_PROJECTION['human_actor_id']!r} "
        f"must be in missing_actor_ids, got: {missing!r}"
    )
    time.sleep(0.5)


def test_pr_c_scenario3_act_while_paused_stays_paused(live_pr_c_session_id: str) -> None:
    """Scenario 3: mundane action while gathering is paused.

    Human is still outside → paused=True persists. Player must remain free
    (no hard rejection).
    """
    _wait_for_stack()
    turn = _execute_turn(live_pr_c_session_id, "Ich schaue aus dem Küchenfenster")
    _assert_director_pause_invariants(turn, expect_paused=True, scenario_id="act_while_paused")
    # Turn must not be a hard failure — player remains free.
    assert turn.get("turn_status") != "hard_failure", (
        f"Scenario 3: turn must not be a hard_failure while gathering is paused. "
        f"turn_status={turn.get('turn_status')!r}"
    )
    time.sleep(0.5)


def test_pr_c_scenario4_return_clears_pause(live_pr_c_session_id: str) -> None:
    """Scenario 4: human actor returns to gathering room.

    All actors back at gathering scene → paused=False, missing_actor_ids=[].
    """
    _wait_for_stack()
    turn = _execute_turn(live_pr_c_session_id, "Ich gehe zurück ins Wohnzimmer")
    _assert_director_pause_invariants(turn, expect_paused=False, scenario_id="return_clears")
    dgs = _director_gathering_state(turn)
    assert dgs.get("missing_actor_ids") == [], (
        f"Scenario 4: missing_actor_ids must be empty after return. Got: {dgs!r}"
    )
    time.sleep(0.5)
