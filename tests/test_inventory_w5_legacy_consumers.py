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


# ---------------------------------------------------------------------------
# Phase 6B-0 rename guarantees (R1–R5)
# ---------------------------------------------------------------------------


def test_renamed_validation_function_is_importable() -> None:
    """R1: ``validate_w5_actor_tracking`` is the live name and reachable from
    the package public API."""

    from ai_stack.actor_tracking import validate_w5_actor_tracking
    from ai_stack.actor_tracking.validation import (
        validate_w5_actor_tracking as direct,
    )

    assert callable(validate_w5_actor_tracking)
    assert validate_w5_actor_tracking is direct


def test_old_validation_function_is_absent() -> None:
    """R1: the deprecated ``validate_w5_actor_situation`` symbol must no
    longer exist as an importable name. We deliberately do not retain a
    backward alias — the call graph is enumerated and small."""

    import ai_stack.actor_tracking as pkg
    import ai_stack.actor_tracking.validation as validation_module

    assert not hasattr(pkg, "validate_w5_actor_situation")
    assert not hasattr(validation_module, "validate_w5_actor_situation")
    assert "validate_w5_actor_situation" not in pkg.__all__
    assert "validate_w5_actor_situation" not in validation_module.__all__


def test_no_production_callsite_references_old_validation_name() -> None:
    """R1: no production (non-test, non-doc, non-inventory) code references
    the old function name. The historical sentence in
    ``ai_stack/actor_tracking/__init__.py`` does not name the function."""

    report = _load_module().scan(REPO_ROOT)
    findings = [
        f for f in report.findings if f.surface == "validate_w5_actor_situation_old"
    ]
    allowed_paths = {
        # Inventory + planning surfaces are allowed to reference the old name.
        "docs/MVPs/w5_legacy_consumer_removal_inventory.md",
        "docs/MVPs/w5_actor_tracking_migration.md",
        "scripts/inventory_w5_legacy_consumers.py",
        "tests/test_inventory_w5_legacy_consumers.py",
    }
    unexpected = [
        f
        for f in findings
        if f.path not in allowed_paths and not f.path.startswith("'fy'-suites/")
    ]
    assert not unexpected, (
        "Old function name still referenced outside allowed inventory surfaces: "
        + ", ".join(f"{f.path}:{f.line}" for f in unexpected)
    )


def test_new_validation_failure_class_string_is_in_use() -> None:
    """R2: production code emits the new failure_class string."""

    from ai_stack.story_runtime.turn import god_of_carnage_turn_seams_validation as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert '"w5_actor_tracking_validation"' in src
    assert '"w5_actor_situation_validation"' not in src


def test_no_production_callsite_references_old_failure_class_string() -> None:
    """R2: the old failure_class literal must not appear in production code.
    Inventory docs and the script may reference the historical name."""

    report = _load_module().scan(REPO_ROOT)
    findings = [
        f
        for f in report.findings
        if f.surface == "w5_actor_situation_validation_old"
    ]
    allowed_paths = {
        "docs/MVPs/w5_legacy_consumer_removal_inventory.md",
        "docs/MVPs/w5_actor_tracking_migration.md",
        "scripts/inventory_w5_legacy_consumers.py",
        "tests/test_inventory_w5_legacy_consumers.py",
    }
    unexpected = [
        f
        for f in findings
        if f.path not in allowed_paths and not f.path.startswith("'fy'-suites/")
    ]
    assert not unexpected, (
        "Old failure_class string still present outside allowed inventory surfaces: "
        + ", ".join(f"{f.path}:{f.line}" for f in unexpected)
    )


def test_renamed_docstring_paths_point_at_current_files() -> None:
    """R3, R4, R5: docstrings must reference the current ADR + migration
    doc filenames, not the renamed-away historical filenames."""

    import ai_stack.actor_tracking as pkg
    import ai_stack.actor_tracking.models as models
    import ai_stack.actor_tracking.extractor as extractor
    import ai_stack.actor_tracking.projection as projection

    # Current names are present.
    assert "adr-0063-w5-actor-tracking.md" in (models.__doc__ or "")
    assert "w5_actor_tracking_migration.md" in (pkg.__doc__ or "")
    assert "w5_actor_tracking_migration.md" in (extractor.__doc__ or "")
    assert "w5_actor_tracking_migration.md" in (projection.__doc__ or "")

    # Renamed-away historical filenames must not appear as current refs.
    for mod_doc in (
        models.__doc__,
        extractor.__doc__,
        projection.__doc__,
    ):
        assert "adr-0063-w5-actor-situation-tracker.md" not in (mod_doc or "")
        assert "w5_actor_situation_migration.md" not in (mod_doc or "")


def test_current_code_uses_actor_tracking_package() -> None:
    """The production validation seam imports from ``ai_stack.actor_tracking``
    only — never from any of the forbidden historical packages."""

    from ai_stack.story_runtime.turn import god_of_carnage_turn_seams_validation as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "from ai_stack.actor_tracking" in src
    assert "from ai_stack.actor_situation" not in src
    assert "from ai_stack.w5_actor_situation" not in src
    assert "import ai_stack.actor_situation" not in src
    assert "import ai_stack.w5_actor_situation" not in src
