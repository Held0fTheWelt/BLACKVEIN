"""Copy active domain files listed in integration_conflict_register into MVP/<domain>/.

Policy: the active repository remains authoritative for shipped code and docs; the MVP
snapshot is refreshed so compared paths become byte-identical (clears `CON-*` rows on
the next `mvp_reconcile.py` run).

Example:
  python scripts/mvp_sync_domain_snapshot_from_register.py --repo-root . \\
      --mvp-prefix MVP/backend/ --active-prefix backend/
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--mvp-prefix",
        default="MVP/backend/",
        help="Literal prefix as in the conflict register, e.g. MVP/backend/ or MVP/world-engine/",
    )
    parser.add_argument(
        "--active-prefix",
        default="backend/",
        help="Active destination prefix, e.g. backend/ or world-engine/",
    )
    args = parser.parse_args()
    root: Path = args.repo_root.resolve()
    mvp_prefix: str = args.mvp_prefix
    active_prefix: str = args.active_prefix
    if not mvp_prefix.endswith("/"):
        mvp_prefix += "/"
    if not active_prefix.endswith("/"):
        active_prefix += "/"

    md = (
        root / "docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/integration_conflict_register.md"
    ).read_text(encoding="utf-8")
    esc_mvp = re.escape(mvp_prefix)
    esc_act = re.escape(active_prefix)
    row_re = re.compile(rf"\| `CON-\d+` \| `({esc_mvp}[^`]+)` \| `({esc_act}[^`]+)` \|")

    seen: set[str] = set()
    n = 0
    missing: list[str] = []
    for m in row_re.finditer(md):
        mvp_m, be_m = m.group(1), m.group(2)
        rel = mvp_m[len(mvp_prefix) :]
        if rel in seen:
            continue
        seen.add(rel)
        src = root.joinpath(*be_m.split("/"))
        dst = root.joinpath(*mvp_prefix.rstrip("/").split("/"), *rel.split("/"))
        if not src.is_file():
            missing.append(str(src))
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        n += 1
    print(f"synced {n} unique paths for {mvp_prefix} from {active_prefix}")
    if missing:
        print(f"missing {len(missing)} source files (first 10): {missing[:10]}")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
