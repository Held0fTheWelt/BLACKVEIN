"""Smoke tests for ``scripts/inventory_w5_legacy_consumers.py``.

The inventory script is intentionally non-failing — these tests verify that
the script runs to completion, finds the expected substrate keywords, and
flags no forbidden package references in the working tree.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "inventory_w5_legacy_consumers.py"


def _load_module():
    name = "inventory_w5_legacy_consumers"
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before execution so @dataclass can resolve ``cls.__module__``.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def inventory_module():
    return _load_module()


def test_script_exists() -> None:
    assert SCRIPT_PATH.is_file(), f"missing script at {SCRIPT_PATH}"


def test_legacy_surfaces_are_declared(inventory_module) -> None:
    keys = {key for key, _ in inventory_module.LEGACY_SURFACES}
    # The Phase 6A inventory requires every surface listed in the migration
    # plan to be scanned for.
    required = {
        "current_room",
        "current_room_id",
        "current_area",
        "previous_room_id",
        "actor_locations",
        "visible_room_ids",
        "visible_occupants",
        "complete_actor_locations_for_gathering",
        "gathering_scene_id",
        "transition_from_previous",
        "location_changed",
        "forbidden_ai_stack_actor_situation",
        "forbidden_ai_stack_w5_actor_situation",
    }
    missing = required - keys
    assert not missing, f"inventory script is missing surfaces: {sorted(missing)}"


def test_scan_completes_and_finds_substrate_consumers(inventory_module) -> None:
    report = inventory_module.scan(REPO_ROOT)
    assert report.files_scanned > 0
    counts = report.by_surface()
    # The substrate writer + dataclass + tests guarantee these are present.
    assert counts["current_room_id"] > 0
    assert counts["actor_locations"] > 0


def test_no_forbidden_package_references(inventory_module) -> None:
    """Phase 6A guarantees: no active import of ``ai_stack/actor_situation``
    or ``ai_stack/w5_actor_situation`` exists."""
    report = inventory_module.scan(REPO_ROOT)
    forbidden = [
        f
        for f in report.findings
        if f.surface
        in {
            "forbidden_ai_stack_actor_situation",
            "forbidden_ai_stack_w5_actor_situation",
        }
    ]
    # Permit the term to appear inside the inventory documents themselves
    # (they discuss the forbidden packages by name) and inside this script.
    allowed_paths = {
        "docs/MVPs/w5_legacy_consumer_removal_inventory.md",
        "docs/MVPs/w5_actor_tracking_migration.md",
        "scripts/inventory_w5_legacy_consumers.py",
        "tests/test_inventory_w5_legacy_consumers.py",
    }
    unexpected = [f for f in forbidden if f.path not in allowed_paths]
    assert not unexpected, (
        "Forbidden package references found outside allowed documentation: "
        + ", ".join(f"{f.path}:{f.line}" for f in unexpected)
    )


def test_main_returns_zero_and_emits_json(inventory_module) -> None:
    buffer = io.StringIO()
    saved_argv = sys.argv[:]
    try:
        sys.argv = ["inventory_w5_legacy_consumers.py", "--root", str(REPO_ROOT), "--json"]
        with redirect_stdout(buffer):
            rc = inventory_module.main(["--root", str(REPO_ROOT), "--json"])
    finally:
        sys.argv = saved_argv
    assert rc == 0
    payload = json.loads(buffer.getvalue())
    assert payload["root"]
    assert payload["files_scanned"] > 0
    assert "counts_by_surface" in payload
