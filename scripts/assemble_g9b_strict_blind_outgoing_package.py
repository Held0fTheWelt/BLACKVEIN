#!/usr/bin/env python3
"""
Assemble the strict-blind external Evaluator B outgoing package per
docs/plans/PLAN_G9B_STRICT_BLIND_EXTERNAL_EVALUATOR_B_RUN.md

Copies only:
- docs/g9_evaluator_b_external_package/documents/
- docs/g9_evaluator_b_external_package/templates/
- docs/g9_evaluator_b_external_package/README.md -> PACKAGE_README.md
- exactly six frozen scenario JSON files from the authoritative evidence directory

Does NOT copy Evaluator A matrix, delta, reconciliation, G9B internal records, or validator outputs.

This script does not score, ingest evidence, compute delta, or update audit status.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

AUDIT_RUN_ID = "g9_level_a_fullsix_20260410"

SCENARIO_FILES: tuple[str, ...] = (
    "scenario_goc_roadmap_s1_direct_provocation.json",
    "scenario_goc_roadmap_s2_deflection_brevity.json",
    "scenario_goc_roadmap_s3_pressure_escalation.json",
    "scenario_goc_roadmap_s4_misinterpretation_correction.json",
    "scenario_goc_roadmap_s5_primary_failure_fallback.json",
    "scenario_goc_roadmap_s6_retrieval_heavy.json",
)

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_handoff_readme(out_root: Path, assembled_at_utc: str) -> None:
    text = f"""# Strict-blind external Evaluator B — outgoing handoff

**audit_run_id:** `{AUDIT_RUN_ID}`

**Assembled (UTC):** {assembled_at_utc}

## Governing plan

This folder was produced to support a **strict-blind** external Evaluator B run as defined in:

- `docs/plans/PLAN_G9B_STRICT_BLIND_EXTERNAL_EVALUATOR_B_RUN.md`

## What is included

- `documents/` — handoff docs from `docs/g9_evaluator_b_external_package/documents/`
- `templates/` — empty return templates from `docs/g9_evaluator_b_external_package/templates/`
- `scenarios/` — exactly six frozen scenario JSON files from `tests/reports/evidence/{AUDIT_RUN_ID}/`
- `PACKAGE_README.md` — copy of `docs/g9_evaluator_b_external_package/README.md`
- `optional_grounding/` — optional dramatic PDF only if present at `resources/Script-God-Of-Carnage-Script-by-Yazmina-Reza.pdf`

## What is excluded (default blind package)

Evaluator A matrix, Evaluator A rationales, delta, reconciliation, internal G9B attempt records,
validator outputs, and technical witness files (`run_metadata.json`, `pytest_g9_roadmap_bundle.txt`)
unless you intentionally opt in under a **documented exception** recorded before scoring and
returned with Evaluator B artifacts.

## Next steps (human / external process)

1. Review `documents/01_EVALUATOR_B_HANDOUT.md` and `documents/04_BLINDNESS_CONTAMINATION_CHECKLIST.md`.
2. Hand this folder (or a zip of it) to the external Evaluator B process with **no** pre-scoring access to Evaluator A scores or rationales.
3. Receive the three return JSON files named in `documents/07_FILENAME_AND_RETURN_LAYOUT.md`.

This assembly step **does not** create scores, **does not** compute delta, and **does not** assert G9B Level B or program closure.
"""
    out_root.joinpath("STRICT_BLIND_HANDOFF.md").write_text(text, encoding="utf-8")


def _write_readme_txt(out_root: Path) -> None:
    out_root.joinpath("README.txt").write_text(
        "Start with documents/01_EVALUATOR_B_HANDOUT.md\n"
        "Strict-blind policy: see STRICT_BLIND_HANDOFF.md\n",
        encoding="utf-8",
    )


def _write_assembly_notes(
    out_root: Path,
    evidence_dir: Path,
    assembled_at_utc: str,
    scenario_hashes: list[tuple[str, str]],
) -> None:
    lines = [
        f"audit_run_id: {AUDIT_RUN_ID}",
        f"assembled_at_utc: {assembled_at_utc}",
        f"source_evidence_dir: {evidence_dir.as_posix()}",
        "",
        "Included scenario files (SHA-256):",
    ]
    for name, digest in scenario_hashes:
        lines.append(f"  {name}  {digest}")
    lines.extend(
        [
            "",
            "Excluded by design from evidence dir: all non-scenario files "
            "(Evaluator A/B matrices, raw sheets, delta, attempt records, validators, witness logs).",
            "",
            "Governing plan: docs/plans/PLAN_G9B_STRICT_BLIND_EXTERNAL_EVALUATOR_B_RUN.md",
        ]
    )
    out_root.joinpath("ASSEMBLY_NOTES.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root (default: parent of scripts/)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: outgoing/g9b_strict_blind_external_evaluator_HANDOFF_<audit_run_id>/)",
    )
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Do not copy optional grounding PDF from resources/",
    )
    args = parser.parse_args()

    repo_root: Path = args.repo_root.resolve()
    evidence_dir = repo_root / "tests" / "reports" / "evidence" / AUDIT_RUN_ID
    pkg_src = repo_root / "docs" / "g9_evaluator_b_external_package"
    out_root = args.out_dir or (
        repo_root / "outgoing" / f"g9b_strict_blind_external_evaluator_HANDOFF_{AUDIT_RUN_ID}"
    )
    out_root = out_root.resolve()

    if not evidence_dir.is_dir():
        print(f"ERROR: evidence directory not found: {evidence_dir}", file=sys.stderr)
        return 2
    if not (pkg_src / "documents").is_dir() or not (pkg_src / "templates").is_dir():
        print(f"ERROR: package source incomplete: {pkg_src}", file=sys.stderr)
        return 2

    assembled_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)

    shutil.copytree(pkg_src / "documents", out_root / "documents")
    shutil.copytree(pkg_src / "templates", out_root / "templates")
    shutil.copy2(pkg_src / "README.md", out_root / "PACKAGE_README.md")

    scenarios_out = out_root / "scenarios"
    scenarios_out.mkdir(parents=True)

    scenario_hashes: list[tuple[str, str]] = []
    for name in SCENARIO_FILES:
        src = evidence_dir / name
        if not src.is_file():
            print(f"ERROR: missing scenario file: {src}", file=sys.stderr)
            return 2
        dst = scenarios_out / name
        shutil.copy2(src, dst)
        scenario_hashes.append((name, _sha256_file(dst)))

    if not args.skip_pdf:
        pdf = repo_root / "resources" / "Script-God-Of-Carnage-Script-by-Yazmina-Reza.pdf"
        if pdf.is_file():
            og = out_root / "optional_grounding"
            og.mkdir(parents=True)
            shutil.copy2(pdf, og / pdf.name)

    _write_handoff_readme(out_root, assembled_at)
    _write_readme_txt(out_root)
    _write_assembly_notes(out_root, evidence_dir, assembled_at, scenario_hashes)

    print(f"OK: strict-blind outgoing package -> {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
