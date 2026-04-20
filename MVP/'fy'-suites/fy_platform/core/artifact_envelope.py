"""Versioned machine-readable artifact envelope helpers."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_envelope(
    *,
    suite: str,
    suite_version: str,
    payload: dict[str, Any],
    manifest_ref: str = "",
    compat_mode: str = "transitional",
    deprecations: list[dict[str, str]] | None = None,
    findings: list[dict[str, Any]] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    stats: dict[str, Any] | None = None,
    envelope_version: str = "1",
) -> dict[str, Any]:
    """Build canonical envelope around an existing suite payload."""
    return {
        "envelopeVersion": envelope_version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "suite": suite,
        "suiteVersion": suite_version,
        "manifest_ref": manifest_ref,
        "compatMode": compat_mode,
        "findings": findings or [],
        "evidence": evidence or [],
        "stats": stats or {},
        "deprecations": deprecations or [],
        "payload": payload,
    }


def dump_envelope_json(envelope: dict[str, Any]) -> str:
    """Return canonical JSON representation for golden file stability."""
    return json.dumps(envelope, indent=2, sort_keys=True) + "\n"


def write_envelope(path: Path, envelope: dict[str, Any]) -> None:
    """Write envelope with canonical serialization."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_envelope_json(envelope), encoding="utf-8")
