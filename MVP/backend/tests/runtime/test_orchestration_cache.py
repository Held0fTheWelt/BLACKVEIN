"""Focused tests for orchestration per-turn cache behavior."""

from app.runtime.orchestration_cache import OrchestrationTurnCache


def test_turn_cache_records_hits_and_misses():
    cache = OrchestrationTurnCache(max_entries=2)
    key = cache.make_tool_key("wos.read.current_scene", {})

    assert cache.get(key) is None
    cache.put(key, {"result": {"scene_id": "scene_1"}})
    assert cache.get(key) == {"result": {"scene_id": "scene_1"}}

    summary = cache.summary()
    assert summary["scope"] == "turn"
    assert summary["hits"] == 1
    assert summary["misses"] == 1


def test_turn_cache_evicts_oldest_entry_when_bounded():
    cache = OrchestrationTurnCache(max_entries=1)
    key_a = cache.make_tool_key("wos.read.current_scene", {"turn": 1})
    key_b = cache.make_tool_key("wos.read.current_scene", {"turn": 2})

    cache.put(key_a, {"result": {"turn": 1}})
    cache.put(key_b, {"result": {"turn": 2}})

    assert cache.get(key_a) is None
    assert cache.get(key_b) == {"result": {"turn": 2}}
    assert cache.summary()["evictions"] >= 1
