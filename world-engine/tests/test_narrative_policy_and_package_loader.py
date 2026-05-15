"""Contract tests for narrative policy resolution and package loader file I/O."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.narrative.package_loader import NarrativePackageLoader
from app.narrative.package_models import NarrativePackage, NarrativePackageManifest
from app.narrative.policy_resolver import resolve_effective_policy


@pytest.mark.contract
def test_resolve_effective_policy_scene_and_actor_overrides() -> None:
    layers = {
        "global_policy": {"tone": "global"},
        "module_policy": {"tone": "module"},
        "scene_policy": {
            "scene_1": {"pace": "fast"},
            "other": {"pace": "slow"},
        },
        "actor_policy": {
            "npc_a": {"voice": "sharp"},
        },
    }
    resolved = resolve_effective_policy(
        policy_layers=layers,
        scene_id="scene_1",
        actor_id="npc_a",
    )
    assert resolved["tone"] == "module"
    assert resolved["pace"] == "fast"
    assert resolved["voice"] == "sharp"


@pytest.mark.contract
def test_narrative_package_loader_reload_and_preview(tmp_path: Path) -> None:
    module_id = "fixture_mod"
    version = "v1"
    preview_id = "prev_a"
    root = tmp_path / "content" / "compiled_packages" / module_id
    pkg_body = NarrativePackage(
        manifest=NarrativePackageManifest(
            module_id=module_id,
            package_version=version,
            source_revision="rev1",
            build_created_at="2026-05-15T00:00:00Z",
            build_id="build1",
            policy_profile="default",
            trigger_map_version="tm1",
            legality_table_version="lt1",
            package_schema_version="1",
            build_status="ok",
            validation_status="ok",
        ),
        system_directive="test",
    )
    active_path = root / "versions" / version / "package.json"
    active_path.parent.mkdir(parents=True)
    active_path.write_text(pkg_body.model_dump_json(), encoding="utf-8")
    preview_path = root / "previews" / preview_id / "package.json"
    preview_path.parent.mkdir(parents=True)
    preview_path.write_text(pkg_body.model_dump_json(), encoding="utf-8")

    loader = NarrativePackageLoader(repo_root=tmp_path)
    assert loader.reload_active(module_id=module_id, expected_active_version=version)["loaded_version"] == version
    assert loader.load_preview(module_id=module_id, preview_id=preview_id)["load_status"] == "loaded"
    with pytest.raises(ValueError, match="preview_already_loaded"):
        loader.load_preview(module_id=module_id, preview_id=preview_id)
    assert loader.unload_preview(module_id=module_id, preview_id=preview_id)["unload_status"] == "accepted"
    state = loader.state(module_id)
    assert state["active_version"] == version
    assert preview_id not in state["loaded_previews"]


@pytest.mark.contract
def test_narrative_package_loader_missing_file_raises(tmp_path: Path) -> None:
    loader = NarrativePackageLoader(repo_root=tmp_path)
    with pytest.raises(FileNotFoundError):
        loader.reload_active(module_id="missing", expected_active_version="v0")
