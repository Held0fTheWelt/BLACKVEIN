# Contractify `state/`

This folder is the tracked restart and review layer for Contractify governance work.

Use it for **human-visible state tracking** of bounded Contractify waves, while machine-generated audit payloads continue to live under `../reports/`.

## What is tracked here

- **Pass state documents** — bounded wave records, decisions, evidence links, and unresolved areas.
- **State index** — one visible entry point for the currently relevant Contractify passes.
- **Pre/post artifact paths** — optional tracked anchor directories for future pre/post evidence snapshots when a pass needs them.

## What is not tracked here

- Full ephemeral audit JSON exports from ad-hoc local runs. Those stay under `../reports/*.json` and may remain uncommitted.
- Product/runtime truth. Contractify state documents describe governance work; they do not replace normative runtime contracts, ADRs, or code.

## Canonical visibility model

1. `contract_governance_input.md` — backlog and follow-up items (`CG-*`).
2. `state/ATTACHMENT_PASS_INDEX.md` — visible index of major Contractify state passes.
3. Pass state files under `state/*.md` — tracked narrative of what was actually done.
4. `reports/runtime_mvp_attachment_report.md` — concise generated attachment summary.
5. `reports/contract_audit.json` — machine-readable current audit output for the local run.
6. `reports/committed/*.hermetic-fixture.json` — committed fixture-level evidence for stable report shapes.

## Current dedicated pre/post path

- Runtime/MVP spine attachment pre: `state/artifacts/runtime_mvp_spine/pre/`
- Runtime/MVP spine attachment post: `state/artifacts/runtime_mvp_spine/post/`

These directories may stay empty between waves. Their purpose is visibility and restart continuity, not bureaucracy.
