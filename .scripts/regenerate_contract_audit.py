from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "'fy'-suites"))

from contractify.tools.hub_cli import main as contractify_main
from fy_platform.core.manifest import load_manifest, suite_config


def render_canonical_snapshot(discover_payload: dict[str, object], audit_payload: dict[str, object]) -> str:
    families = audit_payload.get("runtime_mvp_families", {})
    manual = audit_payload.get("manual_unresolved_areas", [])
    adr_stats = audit_payload.get("adr_governance", {}).get("stats", {})
    stats = audit_payload["stats"]
    lines = [
        "# Contractify canonical repo-root audit snapshot",
        "",
        "This file is the **tracked human-readable canonical evidence snapshot** for repo-root Contractify review.",
        "",
        "## Canonical evidence policy",
        "",
        "- Tracked canonical review evidence is markdown, not `reports/*.json` exports.",
        "- Local machine JSON exports remain ephemeral under `reports/_local_contract_audit.json` and `reports/_local_contract_discovery.json`.",
        "- `reports/committed/*.hermetic-fixture.json` remains the tracked fixture-only layer for stable shape regression, not the live repo-root audit backing artifact.",
        "",
        "## Canonical execution profile",
        "",
        "- Manifest anchor: `fy-manifest.yaml`",
        "- OpenAPI anchor: `docs/api/openapi.yaml`",
        f"- Contractify max contracts: **{audit_payload['execution_profile']['max_contracts']}**",
        "- Canonical repo-root commands:",
        "  - `python -m contractify.tools discover --json --out \"'fy'-suites/contractify/reports/_local_contract_discovery.json\"`",
        "  - `python -m contractify.tools audit --json --out \"'fy'-suites/contractify/reports/_local_contract_audit.json\"`",
        "  - `python .scripts/regenerate_contract_audit.py`",
        "",
        "## Fresh canonical discover snapshot",
        "",
        f"- Contracts discovered: **{len(discover_payload['contracts'])}**",
        f"- Projections discovered: **{len(discover_payload['projections'])}**",
        f"- Relations discovered: **{len(discover_payload['relations'])}**",
        f"- Manual unresolved areas kept explicit: **{len(discover_payload.get('manual_unresolved_areas', []))}**",
        "",
        "## Fresh canonical audit snapshot",
        "",
        f"- Contracts discovered in audit: **{stats['n_contracts']}**",
        f"- Projections discovered in audit: **{stats['n_projections']}**",
        f"- Relations discovered in audit: **{stats['n_relations']}**",
        f"- Drift findings in audit: **{stats['n_drifts']}**",
        f"- Conflicts in audit: **{stats['n_conflicts']}**",
        f"- Manual unresolved areas kept explicit: **{stats['n_manual_unresolved_areas']}**",
        "",
        "## ADR governance inventory from the canonical audit",
        "",
        f"- Canonical ADRs discovered: **{adr_stats.get('n_canonical_adrs', 0)}**",
        f"- ADR findings emitted: **{adr_stats.get('n_findings', 0)}**",
        f"- Total ADR-governance records: **{adr_stats.get('n_adrs', 0)}**",
        "",
        "## Runtime/MVP family visibility from the canonical run",
        "",
    ]
    for family, ids in families.items():
        lines.append(f"- `{family}`: {', '.join(ids)}")
    lines += ["", "## Explicit unresolved areas kept reviewable", ""]
    for item in manual:
        lines.append(f"- `{item['id']}` — {item['summary']}")
    lines += [
        "",
        "## Review workflow",
        "",
        "1. Read this file for the canonical tracked stats and execution profile.",
        "2. Read `runtime_mvp_attachment_report.md` for the bounded runtime/MVP narrative summary.",
        "3. Read `../state/RUNTIME_MVP_SPINE_ATTACHMENT.md` for restartable state and unresolved areas.",
        "4. Run `python .scripts/regenerate_contract_audit.py` whenever the canonical machine graph changes and commit the refreshed markdown outputs.",
        "5. Generate fresh local JSON only when you need machine-level detail or want to inspect the current machine payload directly.",
    ]
    return "\n".join(lines) + "\n"


def render_runtime_report(audit_payload: dict[str, object]) -> str:
    families = audit_payload.get("runtime_mvp_families", {})
    manual = audit_payload.get("manual_unresolved_areas", [])
    precedence = audit_payload.get("precedence_rules", [])
    stats = audit_payload["stats"]
    lines = [
        "# Runtime/MVP Contractify attachment report",
        "",
        "Generated from the canonical manifest-backed Contractify audit.",
        "",
        "## Outcome",
        "",
        "- Canonical tracked audit snapshot: `'fy'-suites/contractify/reports/CANONICAL_REPO_ROOT_AUDIT.md`",
        "- Local machine audit export: `'fy'-suites/contractify/reports/_local_contract_audit.json` (ephemeral, not tracked)",
        f"- Contracts discovered in audit: **{stats['n_contracts']}**",
        f"- Relations discovered in audit: **{stats['n_relations']}**",
        f"- Manual unresolved areas kept explicit: **{stats['n_manual_unresolved_areas']}**",
        "",
        "The runtime/MVP spine remains a **bounded family view** inside the larger canonical audit. Broader ADR-governance additions now contribute to the full audit totals above.",
        "",
        "## Precedence / weight handling",
        "",
    ]
    for row in precedence:
        lines.append(f"- **{row['tier']}** (rank {row['rank']}): {row['summary']}")
    lines += ["", "## Runtime/MVP family visibility", ""]
    for family, ids in families.items():
        lines.append(f"- `{family}`: {', '.join(ids)}")
    lines += ["", "## Explicit unresolved areas preserved", ""]
    for item in manual:
        lines.append(f"- `{item['id']}` — {item['summary']}")
        for src in item.get("sources", [])[:4]:
            lines.append(f"  - source: `{src}`")
    lines += [
        "",
        "## Notes",
        "",
        "- This report is regenerated from the same canonical manifest-backed run as `CANONICAL_REPO_ROOT_AUDIT.md`.",
        "- Use the canonical audit snapshot for repo-wide totals and this report for the bounded runtime/MVP reading path.",
        "- The broader ADR portfolio is visible in the canonical snapshot ADR-governance section and the ADR investigation state/report surfaces.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    manifest, warnings = load_manifest(root)
    if manifest is None:
        print("manifest missing")
        return 2
    cfg = suite_config(manifest, "contractify")
    discover_out = cfg.get("local_discover_out", "'fy'-suites/contractify/reports/_local_contract_discovery.json")
    audit_out = cfg.get("local_audit_out", "'fy'-suites/contractify/reports/_local_contract_audit.json")
    snapshot_md = cfg.get("canonical_audit_snapshot_md", "'fy'-suites/contractify/reports/CANONICAL_REPO_ROOT_AUDIT.md")
    runtime_md = cfg.get("runtime_mvp_report_md", "'fy'-suites/contractify/reports/runtime_mvp_attachment_report.md")

    rc = contractify_main(["discover", "--json", "--out", discover_out, "--quiet"])
    if rc != 0:
        print("discover exit", rc)
        return rc
    rc = contractify_main(["audit", "--json", "--out", audit_out, "--quiet"])
    if rc != 0:
        print("audit exit", rc)
        return rc

    discover_payload = json.loads((root / discover_out).read_text(encoding="utf-8"))
    audit_payload = json.loads((root / audit_out).read_text(encoding="utf-8"))

    (root / snapshot_md).write_text(render_canonical_snapshot(discover_payload, audit_payload), encoding="utf-8")
    (root / runtime_md).write_text(render_runtime_report(audit_payload), encoding="utf-8")

    print("discover_out", discover_out)
    print("audit_out", audit_out)
    print("snapshot_md", snapshot_md)
    print("runtime_md", runtime_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
