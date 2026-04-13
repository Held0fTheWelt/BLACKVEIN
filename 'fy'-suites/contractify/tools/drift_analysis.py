"""Drift analysis (``driftify`` sub-capability) — deterministic and heuristic checks.

Each finding records ``deterministic`` plus ``confidence``; callers must not treat heuristics as proof.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from contractify.tools.discovery import (
    OPENAPI_DEFAULT,
    POSTMAN_MANIFEST,
    projection_backref_ok,
)
from contractify.tools.models import ConflictFinding, DriftFinding, DriftSeverity

DOCIFY_AUDIT_ROOTS_MARKER = "'fy'-suites/contractify"


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    try:
        h.update(path.read_bytes())
    except OSError:
        return None
    return h.hexdigest()


def _norm_manifest_path(repo: Path, raw: str) -> Path:
    s = raw.replace("\\", "/").strip()
    return (repo / s).resolve()


def drift_postman_openapi_manifest(repo: Path) -> list[DriftFinding]:
    """A: Anchor ↔ projection drift — OpenAPI bytes vs postmanify manifest fingerprint (deterministic)."""
    out: list[DriftFinding] = []
    mf = repo / POSTMAN_MANIFEST
    if not mf.is_file():
        return out
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [
            DriftFinding(
                id="DRF-MANIFEST-JSON-001",
                drift_class="anchor_projection",
                summary="postmanify-manifest.json is not valid JSON; Postman projections cannot be trusted.",
                evidence_sources=[POSTMAN_MANIFEST],
                confidence=1.0,
                severity="high",
                deterministic=True,
                recommended_follow_up="Regenerate manifest with postmanify generate or repair JSON.",
                involved_contract_ids=["CTR-API-OPENAPI-001"],
            )
        ]

    declared = str(data.get("openapi_sha256", "")).lower().strip()
    rel = str(data.get("openapi_path", "")).replace("\\", "/")
    openapi_path = _norm_manifest_path(repo, rel) if rel else repo / OPENAPI_DEFAULT
    if not openapi_path.is_file():
        out.append(
            DriftFinding(
                id="DRF-OPENAPI-MISSING-001",
                drift_class="api_runtime",
                summary=f"Manifest references OpenAPI path that is missing on disk: {rel or OPENAPI_DEFAULT}",
                evidence_sources=[POSTMAN_MANIFEST, rel or OPENAPI_DEFAULT],
                confidence=1.0,
                severity="critical",
                deterministic=True,
                recommended_follow_up="Restore OpenAPI file or regenerate manifest after fixing openapi_path.",
                involved_contract_ids=["CTR-API-OPENAPI-001"],
            )
        )
        return out

    actual = _sha256_file(openapi_path)
    if not declared or not actual:
        return out
    if declared != actual:
        out.append(
            DriftFinding(
                id="DRF-POSTMAN-OPENAPI-SHA-001",
                drift_class="api_runtime",
                summary="Postmanify manifest openapi_sha256 does not match current OpenAPI file hash "
                "(collections likely stale vs normative schema).",
                evidence_sources=[
                    POSTMAN_MANIFEST,
                    str(openapi_path.relative_to(repo)),
                    f"manifest={declared[:16]}…",
                    f"actual={actual[:16]}…",
                ],
                confidence=1.0,
                severity="high",
                deterministic=True,
                recommended_follow_up="Run postmanify generate after OpenAPI changes; verify CI gate.",
                involved_contract_ids=["CTR-API-OPENAPI-001"],
            )
        )
    return out


def drift_audience_projection_backrefs(repo: Path) -> list[DriftFinding]:
    """A/B: Anchor ↔ projection — easy/start-here markdown should cite normative index or markers."""
    out: list[DriftFinding] = []
    for folder in (repo / "docs" / "easy", repo / "docs" / "start-here"):
        if not folder.is_dir():
            continue
        for md in sorted(folder.glob("*.md"))[:20]:
            ok, reason = projection_backref_ok(md)
            if ok:
                continue
            rel = md.relative_to(repo).as_posix()
            short = hashlib.sha256(rel.encode("utf-8")).hexdigest()[:12]
            out.append(
                DriftFinding(
                    id=f"DRF-PROJ-BACKREF-{short}",
                    drift_class="anchor_projection",
                    summary=f"Audience markdown may lack explicit normative back-reference: {rel}",
                    evidence_sources=[rel, reason],
                    confidence=0.45,
                    severity="low",
                    deterministic=False,
                    recommended_follow_up="Add link to docs/dev/contracts/normative-contracts-index.md or "
                    "embed `contractify-projection:` YAML block (see contractify README).",
                    involved_contract_ids=["CTR-NORM-INDEX-001"],
                )
            )
    return out


def drift_docify_contractify_scan_root(repo: Path) -> list[DriftFinding]:
    """H: suite_handoff — docify default AST roots should include contractify for self-governance."""
    readme = repo / "'fy'-suites" / "docify" / "README.md"
    audit_py = repo / "'fy'-suites" / "docify" / "tools" / "python_documentation_audit.py"
    sources = []
    hit = False
    for p in (readme, audit_py):
        if not p.is_file():
            continue
        sources.append(str(p.relative_to(repo)))
        if DOCIFY_AUDIT_ROOTS_MARKER in p.read_text(encoding="utf-8", errors="replace"):
            hit = True
            break
    if hit:
        return []
    return [
        DriftFinding(
            id="DRF-DOCIFY-ROOT-001",
            drift_class="suite_handoff",
            summary="Docify default documentation scan roots omit contractify; suite Python may evade AST audit.",
            evidence_sources=sources or ["'fy'-suites/docify/README.md"],
            confidence=0.85,
            severity="informational",
            deterministic=True,
            recommended_follow_up="Add `'fy'-suites/contractify` to DEFAULT_RELATIVE_ROOTS and README default roots.",
            involved_contract_ids=["CTR-CONTRACTIFY-SELF-001"],
        )
    ]


def drift_despag_setup_derived_json(repo: Path) -> list[DriftFinding]:
    """Reference despaghettify normative rule: spaghetti-setup.json is derived — flag if missing."""
    out: list[DriftFinding] = []
    md = repo / "'fy'-suites" / "despaghettify" / "spaghetti-setup.md"
    js = repo / "'fy'-suites" / "despaghettify" / "spaghetti-setup.json"
    if not md.is_file():
        return out
    if js.is_file():
        return out
    out.append(
        DriftFinding(
            id="DRF-DESPAG-JSON-001",
            drift_class="missing_propagation",
            summary="spaghetti-setup.md exists but spaghetti-setup.json is absent (may be fine before setup-sync).",
            evidence_sources=[
                "'fy'-suites/despaghettify/spaghetti-setup.md",
                "'fy'-suites/despaghettify/spaghetti-setup.json",
            ],
            confidence=0.55,
            severity="informational",
            deterministic=True,
            recommended_follow_up="If tooling expects JSON, run despaghettify setup-sync; else ignore.",
            involved_contract_ids=["CTR-DESPAG-SETUP-001"],
        )
    )
    return out


def detect_conflicts(repo: Path) -> list[ConflictFinding]:
    """Surface ambiguity without silent winners (lightweight v1)."""
    conflicts: list[ConflictFinding] = []
    # Example: multiple ADR files referencing "single source of truth" for same subsystem — heuristic only
    adr_dir = repo / "docs" / "governance"
    if not adr_dir.is_dir():
        return conflicts
    bodies: list[tuple[str, str]] = []
    for adr in sorted(adr_dir.glob("adr-*.md")):
        text = adr.read_text(encoding="utf-8", errors="replace")
        if re.search(r"scene identity|session surface|runtime authority", text, re.IGNORECASE):
            bodies.append((adr.name, text[:4000]))
    if len(bodies) >= 2:
        conflicts.append(
            ConflictFinding(
                id="CNF-ADR-OVERLAP-001",
                conflict_type="potential_normative_overlap",
                summary="Multiple ADRs touch overlapping runtime/session vocabulary; review for supersession links.",
                sources=[n for n, _ in bodies],
                confidence=0.4,
                requires_human_review=True,
                notes="Heuristic keyword overlap only — not semantic proof of contradiction.",
            )
        )
    return conflicts


def run_all_drifts(repo: Path) -> list[DriftFinding]:
    """Ordered drift passes (cheap first)."""
    findings: list[DriftFinding] = []
    for fn in (
        drift_postman_openapi_manifest,
        drift_audience_projection_backrefs,
        drift_docify_contractify_scan_root,
        drift_despag_setup_derived_json,
    ):
        findings.extend(fn(repo))
    # de-dup by id
    seen: set[str] = set()
    uniq: list[DriftFinding] = []
    for f in findings:
        if f.id in seen:
            continue
        seen.add(f.id)
        uniq.append(f)
    return uniq
