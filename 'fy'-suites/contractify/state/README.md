# Contractify `state/`

This folder is the tracked restart and review layer for Contractify governance work.

Use it for **human-visible state tracking** of bounded Contractify waves, while local machine-generated audit payloads may be regenerated under `../reports/` as ephemeral JSON.

## What is tracked here

- **Pass state documents** — bounded wave records, decisions, evidence links, and unresolved areas.
- **State index** — one visible entry point for the currently relevant Contractify passes.
- **Pre/post artifact paths** — optional tracked anchor directories for future pre/post evidence snapshots when a pass needs them.

## Canonical visibility model

1. `contract_governance_input.md` — backlog and follow-up items (`CG-*`).
2. `state/ATTACHMENT_PASS_INDEX.md` — visible index of major Contractify state passes.
3. Pass state files under `state/*.md` — tracked narrative of what was actually done.
4. `reports/CANONICAL_REPO_ROOT_AUDIT.md` — tracked human-readable canonical audit/discover snapshot.
5. `reports/*.md` and `investigations/**` — bounded generated summaries and maps.
6. local `reports/_local_contract_audit.json` / `reports/_local_contract_discovery.json` — machine-readable outputs for the current machine run.
7. `reports/committed/*.hermetic-fixture.json` — committed fixture-level evidence for stable report shapes.

## Current dedicated state surfaces

- Runtime / MVP spine: `RUNTIME_MVP_SPINE_ATTACHMENT.md`
- ADR governance / investigation: `ADR_GOVERNANCE_INVESTIGATION.md`
