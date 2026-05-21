from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "test_changed.py"
spec = importlib.util.spec_from_file_location("test_changed_script", MODULE_PATH)
assert spec and spec.loader
test_changed = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = test_changed
spec.loader.exec_module(test_changed)


def test_backend_service_path_selects_matching_service_suite() -> None:
    selection = test_changed.select_for_paths(
        ["backend/app/services/governance/governance_runtime_service.py"]
    )

    assert selection.suites == {"backend_service_governance"}


def test_ai_stack_story_runtime_path_selects_package_suite() -> None:
    selection = test_changed.select_for_paths(
        ["ai_stack/story_runtime/semantic_planner/semantic_scene_planner.py"]
    )

    assert selection.suites == {"ai_stack_story_runtime_semantic_planner"}


def test_world_engine_actor_tracking_path_selects_w5_direct_targets() -> None:
    selection = test_changed.select_for_paths(
        ["world-engine/app/story_runtime/manager/actor_tracking/narrator_projection.py"]
    )

    assert "tests/test_story_runtime_w5_admin_diagnostics.py" in selection.world_engine_targets
    assert "tests/test_story_runtime_w5_narrator_projection.py" in selection.world_engine_targets
    assert "tests/test_story_runtime_w5_player_view.py" in selection.world_engine_targets


def test_world_engine_narrative_web_route_selects_http_and_observability() -> None:
    selection = test_changed.select_for_paths(
        ["world-engine/app/api/http_routes/narrative_web_routes.py"]
    )

    assert selection.suites == {"engine_http_ws", "engine_observability"}


def test_changed_test_file_runs_directly() -> None:
    selection = test_changed.select_for_paths(["backend/tests/test_game_routes.py"])

    assert selection.backend_targets == {"tests/test_game_routes.py"}
    assert not selection.suites
