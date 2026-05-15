"""Gate: ADR-0039 runtime surface inventory exists, parses, and stays complete.

Includes mandatory **story_runtime_core** surfaces (input interpretation, recovery,
branching) so shared library paths stay inside the same false-green boundary as
ai_stack / world-engine / backend / frontend / administration-tool.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORY = REPO_ROOT / "docs/MVPs/adr0039_runtime_surface_governance_inventory.md"
ADR0039 = REPO_ROOT / "docs/ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md"

AUTHORITY_LEVELS = frozenset(
    {"canonical", "co_authority", "preview", "sidecar", "diagnostic", "display_only"}
)

REQUIRED_SURFACE_IDS = frozenset(
    {
        "ai_stack_langgraph_runtime_executor",
        "ai_stack_goc_validation_seam",
        "ai_stack_runtime_aspect_ledger",
        "adr0041_scoped_co_authority_and_readiness_consumer",
        "world_engine_story_runtime_manager",
        "backend_game_player_session_bundle",
        "frontend_play_shell_routes_templates",
        "story_runtime_core_input_interpretation",
        "story_runtime_core_no_dead_end_recovery",
        "story_runtime_core_branching_and_consequences",
        "administration_tool_operator_ui_and_proxy",
    }
)

STORY_RUNTIME_CORE_PREFIX = "story_runtime_core_"


def _load_inventory_front_matter() -> dict:
    yaml = pytest.importorskip("yaml")
    text = INVENTORY.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise AssertionError("inventory must begin with YAML front matter ---")
    end = text.find("\n---\n", 3)
    if end == -1:
        raise AssertionError("inventory must close front matter with ---")
    return yaml.safe_load(text[3:end])


def test_adr0039_runtime_surface_inventory_exists() -> None:
    assert INVENTORY.is_file(), f"missing {INVENTORY.relative_to(REPO_ROOT)}"


def test_adr0039_runtime_surface_inventory_yaml_structure() -> None:
    doc = _load_inventory_front_matter()
    assert doc.get("inventory_version") == 1
    surfaces = doc.get("surfaces")
    assert isinstance(surfaces, list) and surfaces
    ids = {s.get("surface_id") for s in surfaces if isinstance(s, dict)}
    missing = REQUIRED_SURFACE_IDS - ids
    assert not missing, f"missing required surface_id rows: {sorted(missing)}"

    story_core = [
        s
        for s in surfaces
        if isinstance(s, dict) and str(s.get("surface_id", "")).startswith(STORY_RUNTIME_CORE_PREFIX)
    ]
    assert len(story_core) >= 3, (
        "story_runtime_core must have dedicated inventory rows "
        "(input interpretation, recovery, branching/consequences)"
    )


def test_each_surface_has_authority_and_paths() -> None:
    doc = _load_inventory_front_matter()
    for surf in doc["surfaces"]:
        assert isinstance(surf, dict)
        sid = surf.get("surface_id")
        assert isinstance(sid, str) and sid.strip()
        level = surf.get("authority_level")
        assert level in AUTHORITY_LEVELS, f"{sid}: bad authority_level {level!r}"
        files = surf.get("primary_files")
        assert isinstance(files, list) and files, f"{sid}: primary_files required"
        for rel in files:
            assert (REPO_ROOT / rel).is_file(), f"{sid}: missing file {rel}"


def test_frontend_play_shell_is_display_only_for_mutation_flags() -> None:
    doc = _load_inventory_front_matter()
    fe = next(
        s
        for s in doc["surfaces"]
        if isinstance(s, dict) and s.get("surface_id") == "frontend_play_shell_routes_templates"
    )
    assert fe.get("authority_level") == "display_only"
    assert fe.get("can_mutate_validation_outcome") is False
    assert fe.get("can_mutate_commit") is False
    assert fe.get("can_mutate_readiness") is False


def test_administration_tool_surface_is_display_only_for_mutation_flags() -> None:
    doc = _load_inventory_front_matter()
    adm = next(
        s
        for s in doc["surfaces"]
        if isinstance(s, dict) and s.get("surface_id") == "administration_tool_operator_ui_and_proxy"
    )
    assert adm.get("authority_level") == "display_only"
    assert adm.get("can_mutate_validation_outcome") is False
    assert adm.get("can_mutate_commit") is False
    assert adm.get("can_mutate_readiness") is False


def test_adr0039_document_links_runtime_surface_inventory_and_story_runtime_core() -> None:
    body = ADR0039.read_text(encoding="utf-8")
    assert "adr0039_runtime_surface_governance_inventory.md" in body
    assert "story_runtime_core" in body
    assert "administration-tool" in body
