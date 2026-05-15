from __future__ import annotations

from pathlib import Path

import pytest

from app.repo_root import resolve_wos_repo_root


def test_resolve_prefers_full_monorepo_from_story_runtime_package() -> None:
    story_runtime_dir = Path(__file__).resolve().parents[1] / "app" / "story_runtime"
    root = resolve_wos_repo_root(start=story_runtime_dir)
    assert (root / "backend" / "app").is_dir()


def test_resolve_slim_world_engine_container_layout(tmp_path: Path) -> None:
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True)
    (app_dir / "main.py").write_text("# stub", encoding="utf-8")
    (app_dir / "story_runtime").mkdir()
    start = tmp_path / "app" / "story_runtime"
    assert resolve_wos_repo_root(start=start) == tmp_path.resolve()


def test_wos_repo_root_env_when_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True)
    (app_dir / "main.py").write_text("# stub", encoding="utf-8")
    (app_dir / "story_runtime").mkdir()
    monkeypatch.setenv("WOS_REPO_ROOT", str(tmp_path))
    assert resolve_wos_repo_root() == tmp_path.resolve()


def test_wos_repo_root_env_ignored_when_not_a_recognized_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid WOS_REPO_ROOT must not win over ancestor discovery from a real package path."""
    orphan = tmp_path / "orphan_only"
    orphan.mkdir()
    monkeypatch.setenv("WOS_REPO_ROOT", str(orphan))
    story_runtime_dir = Path(__file__).resolve().parents[1] / "app" / "story_runtime"
    root = resolve_wos_repo_root(start=story_runtime_dir)
    assert (root / "backend" / "app").is_dir()


def test_resolve_raises_when_no_repo_markers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WOS_REPO_ROOT", raising=False)
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    with pytest.raises(RuntimeError, match="Cannot resolve WOS repository root"):
        resolve_wos_repo_root(start=deep)
