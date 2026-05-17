"""Smoke tests for the reusable content module template.

The template should prevent accidental parallel description databases by making
reference-based authoring the default shape.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


MODULE_ROOT = Path(__file__).parent.parent.parent / "content" / "modules" / "_template"


def _read_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    assert isinstance(data, dict), f"{path} should parse to a mapping"
    return data


def test_template_yaml_files_parse() -> None:
    assert MODULE_ROOT.is_dir(), "Template module is missing"
    yaml_files = sorted(MODULE_ROOT.rglob("*.yaml"))
    assert yaml_files, "Template should include YAML files"
    for path in yaml_files:
        try:
            with path.open(encoding="utf-8") as f:
                list(yaml.safe_load_all(f))
        except yaml.YAMLError as exc:
            pytest.fail(f"YAML parse error in {path.relative_to(MODULE_ROOT)}: {exc}")


def test_template_has_reference_authority_surfaces() -> None:
    required = [
        "knowledge/modularity_policy.yaml",
        "knowledge/opening_quote_anchors.yaml",
        "canonical_path/index.yaml",
        "canonical_path/001_opening_anchor.yaml",
        "canonical_path/002_pressure_turn.yaml",
        "canonical_path/003_handover_to_play.yaml",
        "locations/index.yaml",
        "locations/opening/opening_anchor.yaml",
        "locations/building/threshold.yaml",
        "locations/appartment/main_room.yaml",
        "locations/appartment/apartment_layout.yaml",
        "objects/index.yaml",
        "objects/appartment/main_room/focal_table.yaml",
        "objects/building/threshold_door.yaml",
    ]
    for rel in required:
        assert (MODULE_ROOT / rel).is_file(), f"Missing template file: {rel}"

    policy = _read_yaml(MODULE_ROOT / "knowledge" / "modularity_policy.yaml")["modularity_policy"]
    assert policy["authority_boundaries"]["locations"]["root"] == "locations/"
    assert "place_description" in policy["authority_boundaries"]["canonical_path"]["must_not_own"]
    assert "environment" in policy["authoring_checks"]["forbidden_outside_locations"]


def test_template_keeps_objects_out_of_locations() -> None:
    assert not (MODULE_ROOT / "locations" / "appartment" / "apartment_objects.yaml").exists()
    assert not (MODULE_ROOT / "objects" / "appartment" / "apartment_objects.yaml").exists()

    locations_index = _read_yaml(MODULE_ROOT / "locations" / "index.yaml")["locations"]
    assert locations_index["object_authority_ref"] == "objects/index.yaml"
    for place_file in locations_index.get("place_files") or []:
        assert str(place_file).startswith("locations/"), f"Location index must not list object file: {place_file}"

    object_index = _read_yaml(MODULE_ROOT / "objects" / "index.yaml")["objects"]
    assert object_index["placement_policy"]["objects_are_not_locations"] is True
    assert object_index["placement_policy"]["objects_must_declare_portable"] is True
    assert object_index["placement_policy"]["apartment_objects_grouped_by_location_subfolder"] is True
    assert object_index["location_object_folders"]["main_room"] == "objects/appartment/main_room/"
    assert "objects/appartment/main_room/focal_table.yaml" in object_index["object_files"]
    assert "objects/building/threshold_door.yaml" in object_index["object_files"]
    assert not list((MODULE_ROOT / "objects" / "appartment").glob("*.yaml"))
    for rel_path in object_index["object_files"]:
        object_doc = _read_yaml(MODULE_ROOT / rel_path)["object"]
        assert isinstance(object_doc.get("portable"), bool), f"{rel_path} must declare boolean portable"


def test_template_keeps_old_orchestration_files_out() -> None:
    obsolete = [
        "scenes.yaml",
        "transitions.yaml",
        "triggers.yaml",
        "endings.yaml",
        "escalation_axes.yaml",
        "direction/scene_guidance.yaml",
        "locale",
        "runtime/action_outcome_map.yaml",
    ]
    for rel in obsolete:
        assert not (MODULE_ROOT / rel).exists(), f"Template should not include obsolete file: {rel}"


def test_template_canonical_path_is_reference_only() -> None:
    index = _read_yaml(MODULE_ROOT / "canonical_path" / "index.yaml")["canonical_path"]
    ref_policy = index["reference_policy"]
    assert ref_policy["steps_must_reference_location_files"] is True
    assert ref_policy["steps_must_not_duplicate_location_descriptions"] is True
    assert ref_policy["quote_anchors_live_under"] == "knowledge/opening_quote_anchors.yaml"

    for rel in index["paths"]["opening"]["step_files"]:
        path = MODULE_ROOT / rel
        step = _read_yaml(path)["canonical_path_step"]
        assert isinstance(step.get("location_ref"), dict), f"{rel} missing location_ref"
        source = step["location_ref"].get("source")
        assert source and (MODULE_ROOT / source).is_file(), f"{rel} has invalid location_ref.source"
        assert "path_point" in step, f"{rel} must keep beats under path_point"
        for forbidden in ("point", "environment", "visible_world", "spatial_model", "location_prose"):
            assert forbidden not in step, f"{rel} must not define {forbidden}"


def test_template_scene_graph_is_runtime_index_not_description_surface() -> None:
    graph = _read_yaml(MODULE_ROOT / "scene_graph.yaml")["scene_graph"]
    assert graph["authority"] == "module_runtime_scene_index"
    assert graph["primary_direction_document"] == "canonical_path/index.yaml"
    assert graph["node_authoring_policy"]["must_not_duplicate_location_descriptions"] is True

    for node in graph["nodes"]:
        assert node.get("location_id"), f"{node.get('id')} missing location_id"
        assert "runtime_note" in node, f"{node.get('id')} should use runtime_note"
        assert "summary" not in node, f"{node.get('id')} should not use summary as a description surface"


def test_template_direction_and_knowledge_use_refs_for_opening() -> None:
    opening_sequence = _read_yaml(MODULE_ROOT / "direction" / "opening_sequence.yaml")
    assert opening_sequence["canonical_path_ref"].startswith("canonical_path/")
    assert opening_sequence["quote_anchor_policy_ref"] == "knowledge/opening_quote_anchors.yaml"
    for part_id, part in opening_sequence["parts"].items():
        if part_id == "part_3_player_anchor":
            continue
        assert part.get("canonical_path_refs"), f"{part_id} missing canonical_path_refs"
        assert part.get("location_refs"), f"{part_id} missing location_refs"

    opening_contract = _read_yaml(MODULE_ROOT / "knowledge" / "opening_scene_sequence.yaml")[
        "opening_scene_sequence"
    ]
    for event in opening_contract["narrative_events"]:
        assert event.get("location_id"), f"{event.get('id')} missing location_id"
        assert event.get("canonical_path_refs"), f"{event.get('id')} missing canonical_path_refs"
        assert event.get("location_refs"), f"{event.get('id')} missing location_refs"
        assert "duplicate_location_description" in (event.get("forbidden_moves") or [])
