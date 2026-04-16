from __future__ import annotations

import io
import json
from contextlib import redirect_stderr
from pathlib import Path

import contractify.tools.repo_paths as repo_paths
from contractify.tools.hub_cli import main as contractify_main
from fy_platform.core.manifest import load_manifest, suite_config
from fy_platform.tools.cli import main as fy_main


def _tmp_report(root: Path, stem: str) -> Path:
    return root / "'fy'-suites" / "contractify" / "reports" / stem


def test_repo_root_manifest_exists_and_validates(capsys) -> None:
    root = repo_paths.repo_root()
    manifest, warnings = load_manifest(root)
    assert manifest is not None
    assert warnings == []
    cfg = suite_config(manifest, "contractify")
    assert cfg.get("openapi") == "docs/api/openapi.yaml"
    assert cfg.get("max_contracts") == 60

    code = fy_main(["validate-manifest", "--project-root", str(root)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_canonical_audit_cli_uses_manifest_profile_without_fallback() -> None:
    root = repo_paths.repo_root()
    out = _tmp_report(root, "_pytest_manifest_first_audit.json")
    out_arg = out.relative_to(root).as_posix()
    stderr = io.StringIO()
    try:
        with redirect_stderr(stderr):
            code = contractify_main(["audit", "--out", out_arg, "--quiet"])
        assert code == 0
        assert "legacy fallback" not in stderr.getvalue().lower()
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["execution_profile"]["max_contracts"] == 60
        ids = {c["id"] for c in payload["contracts"]}
        assert "CTR-RUNTIME-AUTHORITY-STATE-FLOW" in ids
        assert "CTR-RAG-GOVERNANCE" in ids
    finally:
        if out.is_file():
            out.unlink()


def test_tracked_contract_audit_matches_fresh_canonical_run() -> None:
    root = repo_paths.repo_root()
    tracked = root / "'fy'-suites" / "contractify" / "reports" / "contract_audit.json"
    assert tracked.is_file()
    fresh = _tmp_report(root, "_pytest_manifest_first_fresh_audit.json")
    fresh_arg = fresh.relative_to(root).as_posix()
    try:
        code = contractify_main(["audit", "--out", fresh_arg, "--quiet"])
        assert code == 0
        tracked_payload = json.loads(tracked.read_text(encoding="utf-8"))
        fresh_payload = json.loads(fresh.read_text(encoding="utf-8"))
        assert tracked_payload["stats"] == fresh_payload["stats"]
        assert tracked_payload["execution_profile"] == fresh_payload["execution_profile"]
        assert tracked_payload["runtime_mvp_families"] == fresh_payload["runtime_mvp_families"]
    finally:
        if fresh.is_file():
            fresh.unlink()


def test_tracked_runtime_mvp_report_mentions_canonical_stats() -> None:
    root = repo_paths.repo_root()
    tracked = root / "'fy'-suites" / "contractify" / "reports" / "contract_audit.json"
    report = root / "'fy'-suites" / "contractify" / "reports" / "runtime_mvp_attachment_report.md"
    payload = json.loads(tracked.read_text(encoding="utf-8"))
    body = report.read_text(encoding="utf-8")
    assert f"Contracts discovered in audit: **{payload['stats']['n_contracts']}**" in body
    assert f"Relations discovered in audit: **{payload['stats']['n_relations']}**" in body
    assert f"Manual unresolved areas kept explicit: **{payload['stats']['n_manual_unresolved_areas']}**" in body
