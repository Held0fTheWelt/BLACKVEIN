"""Legacy manager source loader.

Assembles ordered legacy source chunks into callable manager methods while larger manager responsibilities are still being promoted into normal modules.
"""
from __future__ import annotations

import sys
from importlib import import_module

from ._legacy_sources.manifest import SOURCE_CHUNKS


def load_source(name: str) -> str:
    parts = []
    for module_name in SOURCE_CHUNKS[name]:
        module = import_module(f"{__package__}._legacy_sources.{module_name}")
        parts.append(module.SOURCE)
    return "".join(parts)


def exec_top_level(module_name: str, source_name: str) -> None:
    module = sys.modules[module_name]
    filename = f"app/story_runtime/manager/{source_name}.py"
    exec(compile(load_source(source_name), filename, "exec"), module.__dict__)


__all__ = ["exec_top_level", "load_source"]
