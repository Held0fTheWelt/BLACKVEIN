# Contractify `reports/`

This directory holds **ephemeral machine-generated JSON** from `discover` / `audit` runs plus **tracked human-readable markdown** for canonical review snapshots and bounded governed passes.

## Ephemeral vs tracked visibility

- `reports/*_local*.json` and other `reports/*.json` files directly under this directory — local/current machine exports from ad-hoc runs. Useful for execution and re-audit, but **not** canonical tracked evidence.
- `reports/*.md` — tracked human-readable governance evidence and bounded generated summaries. These are the canonical review surfaces for repo-visible Contractify runs.
- `reports/committed/*.hermetic-fixture.json` — tracked fixture-level report evidence for stable output shapes.

## State-tracked companion files

Report files are not the only visibility layer.
Tracked state for major Contractify waves should also be reflected in:

- `../contract_governance_input.md`
- `../state/ATTACHMENT_PASS_INDEX.md`
- relevant pass files under `../state/*.md`

The current runtime/MVP attachment wave is tracked through both:

- `CANONICAL_REPO_ROOT_AUDIT.md` (tracked repo-root audit/discover snapshot)
- `runtime_mvp_attachment_report.md` (generated runtime/MVP summary)
- `../state/RUNTIME_MVP_SPINE_ATTACHMENT.md` (tracked state record)

ADR governance visibility is split similarly:

- `../investigations/adr/ADR_GOVERNANCE_INVESTIGATION.md`
- `../investigations/adr/ADR_RELATION_MAP.mmd`
- `../investigations/adr/ADR_CONFLICT_MAP.mmd`
- `../state/ADR_GOVERNANCE_INVESTIGATION.md`

## Git tracking note

Root `.gitignore` ignores `**/contractify/reports/*.json` **only for files directly under** `reports/` (single path segment). Those JSON files are intentionally ephemeral. The subdirectory `committed/` holds tracked `*.hermetic-fixture.json` files for hermetic fixture validation only.

## Regenerate locally

From the **repository root** use the helper script when you want the tracked markdown evidence refreshed from the canonical machine run:

```bash
python .scripts/regenerate_contract_audit.py
```

If you only need ephemeral machine exports, generate them directly:

```bash
python -m contractify.tools discover --json --out "'fy'-suites/contractify/reports/_local_contract_discovery.json"
python -m contractify.tools audit --json --out "'fy'-suites/contractify/reports/_local_contract_audit.json"
python -m contractify.tools adr-investigation --out-dir "'fy'-suites/contractify/investigations/adr"
```

## Review order

1. `CANONICAL_REPO_ROOT_AUDIT.md`
2. `../state/RUNTIME_MVP_SPINE_ATTACHMENT.md`
3. `runtime_mvp_attachment_report.md`
4. `../investigations/adr/ADR_GOVERNANCE_INVESTIGATION.md`
5. local `_local_contract_audit.json` / `_local_contract_discovery.json` exports when machine detail is needed
6. `committed/` fixture reports if report-shape verification is needed
