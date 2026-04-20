"""Contract tests for GoC scene_id → scene_guidance phase identity (ADR-0003)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.goc_scene_identity import (
    GOC_DEFAULT_GUIDANCE_PHASE_KEY,
    GOC_SCENE_ID_TO_GUIDANCE_PHASE,
    all_expected_guidance_phase_keys,
    guidance_phase_key_for_scene_id,
)
from ai_stack.goc_yaml_authority import load_goc_scene_guidance_yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_scenes_yaml_phase_ids() -> set[str]:
    try:
        import yaml
    except ModuleNotFoundError:  # pragma: no cover
        pytest.skip("PyYAML required")
    path = _repo_root() / "content" / "modules" / GOC_MODULE_ID / "scenes.yaml"
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    assert isinstance(data, dict)
    phases = data.get("scene_phases")
    assert isinstance(phases, dict)
    out: set[str] = set()
    for pid, block in phases.items():
        if isinstance(block, dict):
            bid = block.get("id")
            if isinstance(bid, str):
                out.add(bid)
            elif isinstance(pid, str):
                out.add(pid)
    return out


def test_every_mapping_target_exists_in_scene_guidance() -> None:
    sg = load_goc_scene_guidance_yaml()
    for scene_id, phase_key in GOC_SCENE_ID_TO_GUIDANCE_PHASE.items():
        assert phase_key in sg, f"scene_id {scene_id!r} maps to missing guidance key {phase_key!r}"


def test_guidance_phase_blocks_are_dicts() -> None:
    sg = load_goc_scene_guidance_yaml()
    for key in all_expected_guidance_phase_keys():
        block = sg.get(key)
        assert isinstance(block, dict), f"guidance key {key!r} must be a mapping block"


def test_scenes_yaml_phase_ids_resolve_through_canonical_map() -> None:
    """Runtime projection uses phase_1..phase_5 ids; each must map to a real guidance block."""
    for pid in sorted(_load_scenes_yaml_phase_ids()):
        resolved = guidance_phase_key_for_scene_id(pid)
        sg = load_goc_scene_guidance_yaml()
        assert resolved in sg, f"scenes.yaml id {pid!r} resolved to {resolved!r} missing from guidance"


def test_unknown_scene_id_uses_default() -> None:
    assert guidance_phase_key_for_scene_id("totally_unknown_scene_xyz") == GOC_DEFAULT_GUIDANCE_PHASE_KEY


def test_sole_definition_of_guidance_phase_key_for_scene_id() -> None:
    """No-local-remap: only goc_scene_identity may define the resolver (see tools/verify script)."""
    canon = Path(__file__).resolve().parents[1] / "goc_scene_identity.py"
    text = canon.read_text(encoding="utf-8")
    assert "def guidance_phase_key_for_scene_id" in text
    root = _repo_root()
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if "venv" in path.parts or ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        if ".cursor" in path.parts or "node_modules" in path.parts:
            continue
        rel = path.relative_to(root)
        if rel.parts[:1] == (".git",):
            continue
        if path.name == "goc_scene_identity.py" and "ai_stack" in path.parts:
            continue
        if path.name == "verify_goc_scene_identity_single_source.py":
            continue
        if path.name == "test_goc_scene_identity.py" and "ai_stack" in path.parts:
            continue
        body = path.read_text(encoding="utf-8", errors="replace")
        if "def guidance_phase_key_for_scene_id" in body:
            offenders.append(str(rel))
    assert offenders == [], f"Duplicate guidance_phase_key_for_scene_id definitions: {offenders}"
