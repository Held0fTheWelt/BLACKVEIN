"""
Compare MVP/<domain> snapshot trees to active repo domains and emit
reconciliation_report.md + integration_conflict_register.md under the
canonical MVP bundle directory.
"""

from __future__ import annotations

import argparse
from pathlib import Path

DOMAINS = ["backend", "world-engine", "ai_stack", "frontend", "administration-tool", "docs"]
SKIP_SNIPPETS = [
    "/.pytest_cache/",
    "/.fydata/",
    "/generated/",
    "/.egg-info/",
    "/__pycache__/",
    "/var/",
    "/runtime_data/",
    "/evidence/",
    "/node_modules/",
    "/instance/",
]


def should_skip(path: str) -> bool:
    p = path.replace("\\", "/")
    if any(s in p for s in SKIP_SNIPPETS):
        return True
    pl = p.lower()
    if pl.endswith("/.coverage") or pl.rsplit("/", 1)[-1] == ".coverage":
        return True
    return False


def classify_conflict(domain: str, rel: str) -> str:
    rp = rel.lower()
    if rp.endswith((".md", ".rst", ".txt")):
        return "documentation"
    if "test" in rp or rp.endswith("pytest.ini") or "conftest.py" in rp:
        return "test"
    if "config" in rp or rp.endswith((".yml", ".yaml", ".toml", ".ini", ".env", ".json")):
        return "config"
    if domain in ("backend", "world-engine", "ai_stack", "frontend", "administration-tool"):
        return "behavior"
    return "architecture"


def run_reconcile(root: Path) -> tuple[int, int]:
    mvp = root / "MVP"
    bundle = root / "docs" / "MVPs" / "MVP_World_Of_Shadows_Canonical_Implementation_Bundle"
    recon_rows: list[tuple] = []
    conflict_rows: list[tuple] = []
    conflict_id = 1
    recon_id = 1

    for domain in DOMAINS:
        src_root = mvp / domain
        dst_root = root / domain
        if not src_root.exists() or not dst_root.exists():
            continue
        for src in src_root.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(src_root).as_posix()
            src_rel = src.relative_to(root).as_posix()
            dst = dst_root / rel
            dst_rel = dst.relative_to(root).as_posix()
            if should_skip(src_rel):
                continue
            if not dst.exists():
                recon_rows.append(
                    (
                        f"REC-{recon_id:05d}",
                        src_rel,
                        dst_rel,
                        "missing target file",
                        "target file absent",
                        "none",
                        "migrate_direct_or_merge",
                        "n/a",
                        "pending",
                    )
                )
                recon_id += 1
                continue

            try:
                same = src.read_bytes() == dst.read_bytes()
            except OSError:
                same = False

            existing_state = "identical" if same else "divergent"
            conflicts = "none" if same else "content divergence"
            strategy = "no_change" if same else "reconcile_merge_required"
            unchanged = "keep active behavior unless reconciled evidence requires change"

            recon_rows.append(
                (
                    f"REC-{recon_id:05d}",
                    src_rel,
                    dst_rel,
                    existing_state,
                    "review semantic deltas",
                    conflicts,
                    strategy,
                    unchanged,
                    "resolved" if same else "pending",
                )
            )
            recon_id += 1

            if not same:
                ctype = classify_conflict(domain, rel)
                conflict_rows.append(
                    (
                        f"CON-{conflict_id:05d}",
                        src_rel,
                        dst_rel,
                        ctype,
                        "merge_after_reconciliation",
                        "Active file diverges from MVP source; no blind overwrite allowed.",
                        "pending",
                    )
                )
                conflict_id += 1

    reconciliation = [
        "# reconciliation_report",
        "",
        f"Total reconciliation entries: {len(recon_rows)}",
        "",
        "| reconciliation ID | source file | active destination file | existing state | missing elements | conflicts | chosen merge strategy | must remain unchanged | status |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in recon_rows:
        reconciliation.append(
            f"| `{r[0]}` | `{r[1]}` | `{r[2]}` | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} | `{r[8]}` |"
        )

    conflicts = [
        "# integration_conflict_register",
        "",
        "## Global reconciliation policy",
        "",
        "Rows record **byte-level divergence** between `MVP/<domain>/...` snapshots and the active repository. Until a row is individually reviewed, the **active tree remains authoritative** for shipped runtime and docs; `merge_after_reconciliation` forbids blind overwrite, not automatic MVP adoption.",
        "",
        "Validation status `pending` means no owner has signed merge, selective cherry-pick, or explicit MVP replacement for that path yet.",
        "",
        "## Paths excluded from comparison",
        "",
        "The following are **not** compared and do not appear as reconciliation or conflict rows: cache and tool output (`.pytest_cache/`, `__pycache__/`, `.egg-info/`, `.fydata/`, `node_modules/`), local/runtime trees (`var/`, `runtime_data/`, `evidence/`, `instance/`), generated bundles (`generated/`), and coverage marker files named `.coverage`. Treat MVP copies of those paths as non-authoritative snapshot noise.",
        "",
        f"Total meaningful conflicts: {len(conflict_rows)}",
        "",
        "| conflict ID | affected source files | affected active destination files | conflict type | chosen resolution | justification | validation status |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in conflict_rows:
        conflicts.append(
            f"| `{c[0]}` | `{c[1]}` | `{c[2]}` | `{c[3]}` | {c[4]} | {c[5]} | `{c[6]}` |"
        )

    if not conflict_rows:
        conflicts.extend(
            [
                "",
                "## Current status",
                "",
                "No byte-level divergences remain among compared paths (`backend`, `world-engine`, `ai_stack`, `frontend`, `administration-tool`, `docs`). Re-run `python scripts/mvp_reconcile.py` after substantive edits on either side of a compared pair.",
            ]
        )

    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "reconciliation_report.md").write_text("\n".join(reconciliation) + "\n", encoding="utf-8")
    (bundle / "integration_conflict_register.md").write_text("\n".join(conflicts) + "\n", encoding="utf-8")
    return len(recon_rows), len(conflict_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="MVP vs active tree reconciliation")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root containing MVP/ and domain trees (default: parent of scripts/).",
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()
    n_recon, n_conf = run_reconcile(root)
    print(f"reconciliation={n_recon} conflicts={n_conf} root={root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
