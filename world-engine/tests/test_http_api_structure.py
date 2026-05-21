from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FACADE = ROOT / "app" / "api" / "http.py"
IMPLEMENTATION_DIR = ROOT / "app" / "api" / "http_routes"


def test_http_api_facade_stays_thin_and_import_based() -> None:
    source = FACADE.read_text(encoding="utf-8")

    assert "importlib.util" not in source
    assert "exec(" not in source
    assert "@router." not in source
    assert "http_routes.common" in source
    assert "http_routes.story_turn_routes" in source
    assert "http_routes.narrative_runtime_routes" in source


def test_http_route_modules_use_clear_names() -> None:
    module_names = {path.name for path in IMPLEMENTATION_DIR.glob("*.py")}

    assert "story_session_routes.py" not in module_names
    assert "story_session_lifecycle_routes.py" in module_names
    assert "story_turn_routes.py" in module_names
    for name in module_names:
        assert not name[0].isdigit()
        assert "continuation" not in name
        assert "mvp" not in name.lower()


def test_http_route_package_has_no_source_string_loader() -> None:
    for path in IMPLEMENTATION_DIR.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "importlib.util.spec_from_file_location" not in source
        assert "SourceFileLoader" not in source
