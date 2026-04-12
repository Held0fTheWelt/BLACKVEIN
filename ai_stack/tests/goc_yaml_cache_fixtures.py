"""Autouse fixture: clear GoC YAML LRU caches between tests (DS-002 / C6 — single fixture definition)."""

from __future__ import annotations

import pytest

from ai_stack.goc_yaml_authority import cached_goc_yaml_title, clear_goc_yaml_slice_cache


@pytest.fixture(autouse=True)
def goc_yaml_authority_cache_autoclear() -> None:
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()
    yield
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()
