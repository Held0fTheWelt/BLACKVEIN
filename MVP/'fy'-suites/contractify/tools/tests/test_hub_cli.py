import json

import contractify.tools.hub_cli as hub_cli
import contractify.tools.repo_paths as repo_paths
from contractify.tools.hub_cli import main


def test_discover_writes_json() -> None:
    root = repo_paths.repo_root()
    out_path = root / "'fy'-suites" / "contractify" / "reports" / "_pytest_contractify_discover.json"
    out_arg = out_path.relative_to(root).as_posix()
    try:
        code = main(["discover", "--out", out_arg, "--quiet", "--max-contracts", "15"])
        assert code == 0
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert "contracts" in data
        assert len(data["contracts"]) >= 1
    finally:
        if out_path.is_file():
            out_path.unlink()


def test_discover_can_emit_shared_envelope() -> None:
    root = repo_paths.repo_root()
    out_path = root / "'fy'-suites" / "contractify" / "reports" / "_pytest_contractify_discover_envelope.json"
    out_arg = out_path.relative_to(root).as_posix()
    try:
        code = main(["discover", "--max-contracts", "10", "--quiet", "--envelope-out", out_arg])
        assert code == 0
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["envelopeVersion"] == "1"
        assert data["suite"] == "contractify"
        assert "findings" in data
        assert "evidence" in data
        assert "stats" in data
    finally:
        if out_path.is_file():
            out_path.unlink()


def test_discover_writes_deprecation_evidence_when_manifest_missing(monkeypatch) -> None:
    root = repo_paths.repo_root()
    out = root / "'fy'-suites" / "contractify" / "reports" / "_pytest_contractify_discover_missing_manifest.json"
    env = root / "'fy'-suites" / "contractify" / "reports" / "_pytest_contractify_discover_missing_manifest.envelope.json"
    out_arg = out.relative_to(root).as_posix()
    env_arg = env.relative_to(root).as_posix()
    monkeypatch.setattr(hub_cli, "load_manifest", lambda _root: (None, []))
    try:
        code = main(["discover", "--out", out_arg, "--quiet", "--envelope-out", env_arg, "--max-contracts", "5"])
        assert code == 0
        env_payload = json.loads(env.read_text(encoding="utf-8"))
        assert env_payload["deprecations"]
        dep_md = out.with_suffix(out.suffix + ".deprecations.md")
        assert dep_md.is_file()
    finally:
        if out.is_file():
            out.unlink()
        if env.is_file():
            env.unlink()
