"""Verify MVP source-to-destination mapping rows and replace pending statuses.

This is intentionally conservative: it does not copy files or infer semantic merges.
It only records evidence available from the current filesystem snapshot:

- source file exists under MVP/
- destination target exists for direct/merge/reference mappings
- direct file destinations are byte-identical or need reconciliation
- omitted rows have an explicit omission justification

The script updates the canonical mapping table in place and writes a compact
Markdown summary for deletion-gate review.
"""

from __future__ import annotations

import argparse
import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


BUNDLE_REL = Path("docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle")
MAPPING_NAME = "source_to_destination_mapping_table.md"
REPORT_NAME = "mapping_verification_report.md"


TRIAGE_GUIDANCE = {
    "nested_suite_snapshot": "Treat as duplicate nested suite snapshot; omit or preserve only as non-canonical evidence after review.",
    "generated_output": "Treat as generated report/output; do not migrate blindly into active source paths.",
    "runtime_state_or_database": "Treat as runtime state, run output, or local database material; keep out of active source unless a schema/fixture need is proven.",
    "nested_repo_snapshot": "Treat as nested repository snapshot evidence, not an active `repo/` subtree destination.",
    "validation_evidence": "Treat as historical validation evidence; preserve in canonical evidence docs only if still useful.",
    "legacy_mvp_reference": "Treat as legacy MVP/governance reference material; reconcile into canonical docs or preserve as reference, not as a new root runtime subtree.",
    "fy_source_or_docs": "Review as repo-local fy suite source/docs/config parity candidate.",
    "source_or_config": "Review as active source/config/test parity candidate.",
}


@dataclass
class MappingRow:
    line_index: int
    cells: list[str]
    source: str
    classification: str
    destination: str
    omission: str


def _strip_cell(cell: str) -> str:
    value = cell.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1]
    return value


def _format_cell(value: str) -> str:
    return f"`{value}`"


def _parse_row(line_index: int, line: str) -> MappingRow | None:
    if not line.startswith("| `MVP/"):
        return None
    parts = [p.strip() for p in line.strip().strip("|").split("|")]
    if len(parts) != 10:
        raise ValueError(f"unexpected mapping table column count on line {line_index + 1}: {len(parts)}")
    return MappingRow(
        line_index=line_index,
        cells=parts,
        source=_strip_cell(parts[0]),
        classification=_strip_cell(parts[3]),
        destination=_strip_cell(parts[5]),
        omission=_strip_cell(parts[8]),
    )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _text_matches_with_normalized_eol(source_path: Path, target_path: Path) -> bool:
    source_bytes = source_path.read_bytes()
    target_bytes = target_path.read_bytes()
    if b"\0" in source_bytes or b"\0" in target_bytes:
        return False
    return (
        source_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        == target_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    )


def _triage_bucket(source: str, destination: str) -> str:
    source_rel = source.removeprefix("MVP/")
    dest_rel = destination if destination != "n/a" else ""
    source_parts = [part for part in Path(source_rel).parts if part]
    combined = f"{source_rel}/{dest_rel}".replace("\\", "/")
    suffix = Path(source_rel).suffix.lower()

    if source_rel.startswith("'fy'-suites/'fy'-suites/"):
        return "nested_suite_snapshot"
    if source_rel.startswith("repo/"):
        return "nested_repo_snapshot"
    if source_rel.startswith(("evidence/", "validation/")) or "raw_test_outputs" in combined:
        return "validation_evidence"
    if source_rel.startswith(("mvp/", "governance/")) or source_rel == "FINAL_SUPPLIED_ARCHIVE_AUDIT_PACKAGE_NOTE.md":
        return "legacy_mvp_reference"
    if (
        "/generated/" in f"/{combined}/"
        or "/reports/" in f"/{combined}/"
        or "/report/" in f"/{combined}/"
        or "/__pycache__/" in f"/{combined}/"
        or ".egg-info/" in combined
    ):
        return "generated_output"
    if (
        "/var/" in f"/{combined}/"
        or "/instance/" in f"/{combined}/"
        or source_rel.startswith("runtime_data/")
        or suffix in {".db", ".sqlite", ".sqlite3"}
    ):
        return "runtime_state_or_database"
    if source_parts and source_parts[0] == "'fy'-suites":
        return "fy_source_or_docs"
    return "source_or_config"


def _verify_row(root: Path, row: MappingRow) -> str:
    if not row.source.startswith("MVP/"):
        return "needs_source_path_review"

    source_rel = row.source.removeprefix("MVP/")
    source_path = root / "MVP" / Path(source_rel)
    if not source_path.is_file():
        return "blocked_missing_source"

    cls = row.classification
    dest = row.destination

    if cls == "OMIT_WITH_JUSTIFICATION":
        if row.omission and row.omission != "n/a":
            return "verified_omit_with_justification"
        return "needs_omit_justification"

    if cls == "PRESERVE_AS_REFERENCE":
        if dest == "n/a":
            return "needs_reference_target"
        target = root / Path(dest)
        return "verified_reference_target_present" if target.exists() else "blocked_missing_reference_target"

    if cls == "MERGE_INTO_SECTION":
        if dest == "n/a":
            return "needs_merge_target"
        target = root / Path(dest)
        return "verified_merge_target_present" if target.exists() else "blocked_missing_merge_target"

    if cls == "MIGRATE_DIRECT":
        if dest == "n/a":
            return "needs_direct_target"
        target = root / Path(dest)
        if not target.exists():
            return "blocked_missing_active_target"
        if target.is_dir():
            return "verified_destination_directory_present"
        if not target.is_file():
            return "needs_destination_type_review"
        if source_path.stat().st_size == target.stat().st_size and _sha256(source_path) == _sha256(target):
            return "verified_byte_match"
        if _text_matches_with_normalized_eol(source_path, target):
            return "verified_text_match_normalized_eol"
        return "needs_reconcile_bytes"

    return "needs_classification_review"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify canonical MVP source-to-destination mapping rows.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--limit-report-samples", type=int, default=25)
    args = parser.parse_args()

    root = args.repo_root.resolve()
    bundle = root / BUNDLE_REL
    mapping_path = bundle / MAPPING_NAME
    report_path = bundle / REPORT_NAME

    lines = mapping_path.read_text(encoding="utf-8").splitlines()
    rows: list[MappingRow] = []
    for i, line in enumerate(lines):
        row = _parse_row(i, line)
        if row is not None:
            rows.append(row)

    status_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    followup_by_domain: Counter[tuple[str, str]] = Counter()
    followup_by_triage: Counter[tuple[str, str]] = Counter()
    samples: dict[str, list[tuple[str, str]]] = defaultdict(list)
    triage_samples: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    priority_candidates: list[tuple[str, str, str, str]] = []

    for row in rows:
        status = _verify_row(root, row)
        row.cells[9] = _format_cell(status)
        lines[row.line_index] = "| " + " | ".join(row.cells) + " |"
        status_counts[status] += 1
        class_counts[row.classification] += 1
        if status.startswith("blocked_") or status.startswith("needs_"):
            source_rel = row.source.removeprefix("MVP/")
            top = source_rel.split("/", 1)[0]
            followup_by_domain[(status, top)] += 1
            bucket = _triage_bucket(row.source, row.destination)
            followup_by_triage[(status, bucket)] += 1
            if len(triage_samples[(status, bucket)]) < args.limit_report_samples:
                triage_samples[(status, bucket)].append((row.source, row.destination))
            if bucket in {"source_or_config", "fy_source_or_docs"}:
                priority_candidates.append((status, bucket, row.source, row.destination))
        if len(samples[status]) < args.limit_report_samples:
            samples[status].append((row.source, row.destination))

    mapping_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report = [
        "# mapping_verification_report",
        "",
        "Generated by `scripts/mvp_verify_mapping_table.py` from the current workspace filesystem.",
        "",
        "This report verifies mapping mechanics only. It does not perform semantic review, copy files, or waive domain validation gates.",
        "",
        f"**Total mapping rows verified:** {len(rows)}",
        "",
        "## Classification Counts",
        "",
        "| classification | rows |",
        "|---|---:|",
    ]
    for key, count in sorted(class_counts.items()):
        report.append(f"| `{key}` | {count} |")

    report.extend(["", "## Verification Status Counts", "", "| status | rows |", "|---|---:|"])
    for key, count in sorted(status_counts.items()):
        report.append(f"| `{key}` | {count} |")

    if followup_by_domain:
        report.extend(
            [
                "",
                "## Follow-Up Breakdown By Top-Level Source Domain",
                "",
                "| status | top-level source domain | rows |",
                "|---|---|---:|",
            ]
        )
        for (status, top), count in sorted(
            followup_by_domain.items(), key=lambda item: (-item[1], item[0][0], item[0][1])
        ):
            report.append(f"| `{status}` | `{top}` | {count} |")

    if followup_by_triage:
        report.extend(
            [
                "",
                "## Follow-Up Triage Breakdown",
                "",
                "These buckets are conservative routing hints. They do not waive mapping rows or authorize deletion of `MVP/`.",
                "",
                "| status | triage bucket | rows | recommended next action |",
                "|---|---|---:|---|",
            ]
        )
        for (status, bucket), count in sorted(
            followup_by_triage.items(), key=lambda item: (-item[1], item[0][0], item[0][1])
        ):
            report.append(f"| `{status}` | `{bucket}` | {count} | {TRIAGE_GUIDANCE[bucket]} |")

    report.extend(["", "## Status Samples"])
    for key in sorted(samples):
        report.extend(["", f"### `{key}`", "", "| source path | destination |", "|---|---|"])
        for source, dest in samples[key]:
            report.append(f"| `{source}` | `{dest}` |")

    if triage_samples:
        report.extend(["", "## Follow-Up Triage Samples"])
        for (status, bucket) in sorted(triage_samples):
            report.extend(
                [
                    "",
                    f"### `{status}` / `{bucket}`",
                    "",
                    "| source path | destination |",
                    "|---|---|",
                ]
            )
            for source, dest in triage_samples[(status, bucket)]:
                report.append(f"| `{source}` | `{dest}` |")

    if priority_candidates:
        report.extend(
            [
                "",
                "## Prioritized Reconciliation Candidate Index",
                "",
                "This table lists every follow-up row whose triage bucket is active source/config or fy suite source/docs. It is the first-pass human/agent reconciliation surface before considering generated output, runtime state, validation evidence, or nested snapshot rows.",
                "",
                "| status | triage bucket | source path | destination |",
                "|---|---|---|---|",
            ]
        )
        for status, bucket, source, dest in sorted(priority_candidates):
            report.append(f"| `{status}` | `{bucket}` | `{source}` | `{dest}` |")

    blocking = sum(
        count
        for status, count in status_counts.items()
        if status.startswith("blocked_") or status.startswith("needs_")
    )
    report.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            f"- Non-pending rows: **{len(rows)}**",
            f"- Rows requiring follow-up (`blocked_*` or `needs_*`): **{blocking}**",
            "- `verified_*` rows close the mapping-table status field mechanically.",
            "- `blocked_*` and `needs_*` rows remain deletion-gate blockers until reconciled or explicitly waived in the canonical records.",
        ]
    )
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"updated {mapping_path.relative_to(root)} rows={len(rows)}")
    print(f"wrote {report_path.relative_to(root)}")
    for key, count in sorted(status_counts.items()):
        print(f"{key}={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
