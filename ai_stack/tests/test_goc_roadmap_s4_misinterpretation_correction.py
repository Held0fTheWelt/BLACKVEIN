"""Roadmap §6.9 / §8.2 S4 — misinterpretation / correction (frozen scenario id S4)."""

from __future__ import annotations

pytest_plugins = ("ai_stack.tests.goc_yaml_cache_fixtures",)

import pytest
from ai_stack.goc_s4_misinterpretation_scenario import (
    assert_roadmap_s4_truth,
    run_roadmap_s4_misinterpretation_chain,
)
pytest.importorskip(
    "ai_stack.langgraph_runtime",
    reason="LangGraph/LangChain stack required for GoC runtime graph tests",
)


def test_roadmap_s4_misinterpretation_correction_chain(tmp_path) -> None:
    results = run_roadmap_s4_misinterpretation_chain(tmp_path)
    assert_roadmap_s4_truth(results)
