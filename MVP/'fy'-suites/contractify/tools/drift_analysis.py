"""Drift analysis (``driftify`` sub-capability) — deterministic and heuristic checks.

Each finding records ``deterministic`` plus ``confidence``; callers must not treat heuristics as proof.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from fy_platform.core.manifest import load_manifest, suite_config
from contractify.tools.discovery import (
    OPENAPI_DEFAULT,
    POSTMAN_MANIFEST,
    projection_backref_ok,
)
from contractify.tools.models import ContractRecord, DriftFinding, DriftSeverity

DOCIFY_AUDIT_ROOTS_MARKER = "'fy'-suites/contractify"


def _openapi_default(repo: Path) -> str:
    manifest, _warnings = load_manifest(repo)
    cfg = suite_config(manifest, "contractify")
    rel = str(cfg.get("openapi", "")).strip() if cfg else ""
    return rel or OPENAPI_DEFAULT


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
    openapi_default = _openapi_default(repo)
    openapi_path = _norm_manifest_path(repo, rel) if rel else repo / openapi_default
    if not openapi_path.is_file():
        out.append(
            DriftFinding(
                id="DRF-OPENAPI-MISSING-001",
                drift_class="api_runtime",
                summary=f"Manifest references OpenAPI path that is missing on disk: {rel or openapi_default}",
                evidence_sources=[POSTMAN_MANIFEST, rel or openapi_default],
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


def drift_implementation_paths_missing(repo: Path, contracts: list[ContractRecord]) -> list[DriftFinding]:
    """Normative contract lists ``implemented_by`` paths that are absent on disk (bounded structural check)."""
    out: list[DriftFinding] = []
    repo = repo.resolve()
    for c in contracts:
        if not c.implemented_by:
            continue
        for raw in c.implemented_by:
            p = (repo / raw.rstrip("/")).resolve()
            try:
                p.relative_to(repo)
            except ValueError:
                continue
            if p.exists():
                continue
            short = hashlib.sha256(f"{c.id}:{raw}".encode()).hexdigest()[:10]
            out.append(
                DriftFinding(
                    id=f"DRF-IMPL-MISS-{short}",
                    drift_class="planning_implementation",
                    summary=f"Contract {c.id} declares implemented_by path missing on disk: {raw}",
                    evidence_sources=[c.anchor_location, raw],
                    confidence=0.88,
                    severity="medium",
                    deterministic=True,
                    recommended_follow_up="Restore the path, narrow implemented_by to existing trees, or fix discovery metadata.",
                    involved_contract_ids=[c.id],
                )
            )
    return out


def drift_postmanify_task_openapi_path_alignment(repo: Path) -> list[DriftFinding]:
    """Postmanify task prose vs manifest ``openapi_path`` (deterministic string alignment when both exist)."""
    task = repo / "'fy'-suites/postmanify/postmanify-sync-task.md"
    mf = repo / POSTMAN_MANIFEST
    if not task.is_file() or not mf.is_file():
        return []
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    manifest_path = str(data.get("openapi_path", "")).replace("\\", "/").strip()
    if not manifest_path:
        return []
    body = task.read_text(encoding="utf-8", errors="replace")[:32_000]
    found = re.findall(r"(docs/[a-zA-Z0-9_./-]+\.ya?ml)", body)
    if not found:
        return []
    doc_claim = found[0].replace("\\", "/")
    try:
        norm_man = (repo / manifest_path).resolve().relative_to(repo).as_posix()
        norm_doc = (repo / doc_claim).resolve().relative_to(repo).as_posix()
    except ValueError:
        return []
    if norm_man == norm_doc:
        return []
    return [
        DriftFinding(
            id="DRF-POSTMANIFY-TASK-OPENAPI-001",
            drift_class="suite_handoff",
            summary="Postmanify sync task prose references a different OpenAPI-relative path than postmanify-manifest.json.",
            evidence_sources=[str(task.relative_to(repo)), POSTMAN_MANIFEST, doc_claim, manifest_path],
            confidence=0.95,
            severity="medium",
            deterministic=True,
            recommended_follow_up="Align task documentation with manifest openapi_path or regenerate manifest.",
            involved_contract_ids=["CTR-POSTMANIFY-TASK-001", "CTR-API-OPENAPI-001"],
        )
    ]


def run_all_drifts(repo: Path, contracts: list[ContractRecord] | None = None) -> list[DriftFinding]:
    """Ordered drift passes (cheap first)."""
    findings: list[DriftFinding] = []
    for fn in (
        drift_postman_openapi_manifest,
        drift_audience_projection_backrefs,
        drift_docify_contractify_scan_root,
        drift_despag_setup_derived_json,
    ):
        findings.extend(fn(repo))
    findings.extend(drift_postmanify_task_openapi_path_alignment(repo))
    if contracts is not None:
        findings.extend(drift_implementation_paths_missing(repo, contracts))
    # de-dup by id
    seen: set[str] = set()
    uniq: list[DriftFinding] = []
    for f in findings:
        if f.id in seen:
            continue
        seen.add(f.id)
        uniq.append(f)
    return uniq
