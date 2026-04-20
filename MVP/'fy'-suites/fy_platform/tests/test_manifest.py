from __future__ import annotations

from pathlib import Path

from fy_platform.core.manifest import load_manifest, roots_for_suite


def test_load_manifest_reads_versioned_manifest(tmp_path: Path) -> None:
    p = tmp_path / "fy-manifest.yaml"
    p.write_text(
        "manifestVersion: 1\n"
        "suites:\n"
        "  docify:\n"
        "    roots:\n"
        "      - src\n",
        encoding="utf-8",
    )
    manifest, warnings = load_manifest(tmp_path)
    assert manifest is not None
    assert warnings == []
    assert roots_for_suite(manifest=manifest, suite_name="docify") == ["src"]


def test_load_manifest_reports_missing_version(tmp_path: Path) -> None:
    (tmp_path / "fy-manifest.yaml").write_text("suites: {}\n", encoding="utf-8")
    _manifest, warnings = load_manifest(tmp_path)
    assert "manifest_missing_manifestVersion" in warnings
