# Contractify `reports/`

This directory holds **machine-generated JSON** from `discover` / `audit` runs plus bounded generated markdown summaries for specific governed passes.

## Ephemeral vs tracked visibility

- `reports/*.json` — local/current machine exports from ad-hoc runs. Useful for execution and re-audit.
- `reports/*.md` — optional human-readable generated summaries for a bounded pass when that visibility materially helps governance review.
- `reports/committed/*.hermetic-fixture.json` — tracked fixture-level report evidence for stable output shapes.

## State-tracked companion files

Report files are not the only visibility layer.
Tracked state for major Contractify waves should also be reflected in:

- `../contract_governance_input.md`
- `../state/ATTACHMENT_PASS_INDEX.md`
- relevant pass files under `../state/*.md`

The current runtime/MVP attachment wave is tracked through both:

- `runtime_mvp_attachment_report.md` (generated summary)
- `../state/RUNTIME_MVP_SPINE_ATTACHMENT.md` (tracked state record)

## Git tracking note

Root `.gitignore` ignores `**/contractify/reports/*.json` **only for files directly under** `reports/` (single path segment). The subdirectory `committed/` holds tracked `*.hermetic-fixture.json` files.

## Regenerate locally

From the **repository root**:

```bash
python -m contractify.tools discover --json --out "'fy'-suites/contractify/reports/contract_discovery.json"
python -m contractify.tools audit --json --out "'fy'-suites/contractify/reports/contract_audit.json"
```

## Review order for the runtime/MVP attachment wave

1. `../state/RUNTIME_MVP_SPINE_ATTACHMENT.md`
2. `runtime_mvp_attachment_report.md`
3. `contract_audit.json`
4. `committed/` fixture reports if report-shape verification is needed
