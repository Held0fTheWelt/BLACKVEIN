"""Roadmap §6.9 / §8.2 S4 — misinterpretation / correction (frozen scenario id S4)."""

from __future__ import annotations

import pytest
from ai_stack.goc_s4_misinterpretation_scenario import (
    assert_roadmap_s4_truth,
    run_roadmap_s4_misinterpretation_chain,
)
from ai_stack.goc_yaml_authority import cached_goc_yaml_title, clear_goc_yaml_slice_cache

pytest.importorskip(
    "ai_stack.langgraph_runtime",
    reason="LangGraph/LangChain stack required for GoC runtime graph tests",
)


@pytest.fixture(autouse=True)
def _clear_goc_caches() -> None:
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()
    yield
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()


def test_roadmap_s4_misinterpretation_correction_chain(tmp_path) -> None:
    results = run_roadmap_s4_misinterpretation_chain(tmp_path)
    assert_roadmap_s4_truth(results)
