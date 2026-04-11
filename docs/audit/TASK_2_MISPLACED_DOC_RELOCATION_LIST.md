# Task 2 — Misplaced Documentation Relocation List

## Relocation rules

- Relocate when audience root mismatches primary consumer.
- Relocate when doc is durable and active but currently mixed with non-curated process/control surfaces.
- Do not relocate by preference alone; each relocation needs audience and authority rationale.

## Priority relocation candidates

| Current path | Problem | Target path class | Priority | Rationale |
|---|---|---|---|---|
| `docs/forum/ModerationWorkflow.md` | admin operational doc in generic subject bucket | `docs/admin/moderation/` | P0 | admin audience primary |
| `audits/AUDIT_ADMIN_LOGS_ROLES.md` | governance doc outside docs taxonomy | `docs/admin/governance/audits/` | P0 | admin governance truth |
| `audits/AUDIT_ROLES_ACCESS_CONTROL.md` | governance doc outside docs taxonomy | `docs/admin/governance/audits/` | P0 | admin governance truth |
| `docs/testing/QUALITY_GATES.md` | mixed admin release and dev execution semantics | split `docs/admin/release/` + `docs/dev/testing/` references | P0 | audience separation |
| `docs/testing/RELEASE_GATE_POLICY.md` | admin release policy mixed in dev/testing subtree | `docs/admin/release/` | P0 | release governance |
| `docs/security/AUDIT_REPORT.md` | operational security evidence in generic security root | `docs/admin/governance/security/` | P1 | admin compliance audience |
| `docs/g9_evaluator_b_external_package/documents/*` | external package mirror mixed in curated docs tree | non-curated external package root or explicit mirror namespace | P1 | separate audience docs vs distribution control |
| `docs/reports/PATCH_NOTES_FLASK_PLAY_INTEGRATION.md` (relocated from repo root) | process note under reports | demote to historical archive | P1 | not curated active guidance |

## Non-relocation by design (with explicit marking)

- `outgoing/**`: remains non-curated external distribution root.
- `docs/audit/**`: remains governance/audit baseline root, linked as non-curated.
- `docs/archive/superpowers-legacy-execution-2026/**`: archived non-curated AI execution-control sources (former `docs/superpowers/**`, moved 2026-04-10).

## Verification fields required during relocation

- source path
- destination path
- audience classification (dev/admin/user/non-curated)
- owner
- link repairs completed (yes/no)
- claim-audit impact checked (yes/no)
