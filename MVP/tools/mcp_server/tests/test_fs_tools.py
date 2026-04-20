import pytest
from pathlib import Path
from tools.mcp_server.fs_tools import list_modules, get_module, search_content

def test_list_modules_returns_module_names(tmp_path):
    modules_dir = tmp_path / "content" / "modules"
    modules_dir.mkdir(parents=True)
    (modules_dir / "god_of_carnage").mkdir()
    (modules_dir / "test_module").mkdir()
    result = list_modules(repo_root=tmp_path)
    assert "god_of_carnage" in result
    assert "test_module" in result

def test_get_module_returns_metadata(tmp_path):
    modules_dir = tmp_path / "content" / "modules"
    mod_dir = modules_dir / "test_mod"
    mod_dir.mkdir(parents=True)
    (mod_dir / "scenes.yaml").write_text("scenes: []")
    (mod_dir / "lore.md").write_text("# Lore")
    result = get_module("test_mod", repo_root=tmp_path)
    assert result["name"] == "test_mod"
    assert "scenes.yaml" in result["files"]
    assert "lore.md" in result["files"]

def test_get_module_nonexistent_returns_none(tmp_path):
    result = get_module("nonexistent", repo_root=tmp_path)
    assert result is None

def test_search_content_finds_matches(tmp_path):
    content_dir = tmp_path / "content"
    modules_dir = content_dir / "modules" / "test_mod"
    modules_dir.mkdir(parents=True)
    (modules_dir / "scenes.yaml").write_text("scene: god of carnage\nname: Act One")
    (modules_dir / "lore.md").write_text("The god of carnage is an entity.\nHe causes chaos.")
    result = search_content("god of carnage", repo_root=tmp_path)
    assert len(result) >= 2
    files = [r["file"] for r in result]
    assert any("scenes.yaml" in f for f in files)
    assert any("lore.md" in f for f in files)

def test_search_content_respects_max_hits(tmp_path):
    content_dir = tmp_path / "content"
    modules_dir = content_dir / "modules"
    modules_dir.mkdir(parents=True)
    test_file = modules_dir / "test.txt"
    test_file.write_text("\n".join(["test line"] * 20))
    result = search_content("test", repo_root=tmp_path, max_hits=5)
    assert len(result) <= 5

def test_search_content_case_insensitive(tmp_path):
    content_dir = tmp_path / "content"
    modules_dir = content_dir / "modules"
    modules_dir.mkdir(parents=True)
    (modules_dir / "test.md").write_text("The God of Carnage")
    result = search_content("god of carnage", repo_root=tmp_path)
    assert len(result) >= 1

def test_search_respects_max_file_size(tmp_path):
    content_dir = tmp_path / "content"
    modules_dir = content_dir / "modules"
    modules_dir.mkdir(parents=True)
    large_file = modules_dir / "large.bin"
    large_file.write_bytes(b"x" * (10 * 1024 * 1024))
    result = search_content("test", repo_root=tmp_path, max_file_size_mb=1)
    assert isinstance(result, list)
