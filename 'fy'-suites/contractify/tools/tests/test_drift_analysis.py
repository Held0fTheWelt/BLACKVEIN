import json
from pathlib import Path

from contractify.tools.drift_analysis import drift_postman_openapi_manifest
from contractify.tools.repo_paths import repo_root


def test_postman_openapi_hash_match_is_clean() -> None:
    root = repo_root()
    mf = root / "postman" / "postmanify-manifest.json"
    if not mf.is_file():
        return
    data = json.loads(mf.read_text(encoding="utf-8"))
    rel = str(data.get("openapi_path", "")).replace("\\", "/")
    openapi = root / rel if rel else root / "docs" / "api" / "openapi.yaml"
    if not openapi.is_file():
        return
    findings = drift_postman_openapi_manifest(root)
    declared = data.get("openapi_sha256", "")
    import hashlib

    actual = hashlib.sha256(openapi.read_bytes()).hexdigest()
    if declared == actual:
        assert not any(f.id == "DRF-POSTMAN-OPENAPI-SHA-001" for f in findings)
