# Task 2 — Audience Taxonomy and Placement Map

## Audience-first target roots

- `docs/dev/`
- `docs/admin/`
- `docs/user/`

These roots are role-primary. Subject folders may exist under these roots but cannot replace role-first navigation.

## Placement rules

## Rule A — Primary audience fit

A document is correctly placed only when its primary consumer role matches the root audience contract.

## Rule B — Authority and boundary clarity

A document belongs in curated audience roots only if it provides durable, current guidance and explicitly states:

- responsibility
- authority/source-of-truth
- boundaries

## Rule C — Non-curated control surfaces

Execution-control and process-history docs are not curated audience docs. They must be separated and explicitly marked.

## Rule D — Duplicate location handling

If duplicate tracked documents exist across roots, one canonical owner location must be declared, and mirrors must be explicitly marked as mirrors.

## Taxonomy mapping from current surfaces

| Current surface | Target audience root | Placement status | Action |
|---|---|---|---|
| `docs/architecture/*` | `docs/dev/architecture/*` | mixed | split active architecture from closure-history docs |
| `docs/api/*` | `docs/dev/api/*` | mostly valid content, wrong root shape | relocate by taxonomy phase |
| `docs/development/*` | `docs/dev/development/*` | mostly valid content, wrong root shape | relocate by taxonomy phase |
| `docs/testing/*` | split `docs/dev/testing/*` and `docs/admin/release/*` | mixed audience | split execution details vs release governance |
| `docs/operations/*` | `docs/admin/operations/*` | mostly valid content, wrong root shape | relocate by taxonomy phase |
| `docs/security/*` | mostly `docs/admin/governance/*`, some `docs/dev/security/*` | mixed audience | split policy vs implementation guidance |
| `docs/features/*` | `docs/user/features/*` + selected `docs/dev/contracts/*` references | mixed audience | keep user-facing behavior in user root |
| `docs/forum/ModerationWorkflow.md` | `docs/admin/moderation/*` | misplaced under generic subject root | relocate |
| `audits/*.md` | `docs/admin/governance/audits/*` or demote | outside docs root and mixed intent | classify then relocate/demote |
| `docs/g9_evaluator_b_external_package/*` | non-curated distribution/control surface | mixed into docs root | mark as external-package mirror |
| `outgoing/**` docs | non-curated external distribution root | correctly non-curated | keep outside curated audience map |
| `docs/mcp/*` | non-curated AI execution-control root, unless explicitly audience-stable | mixed | split stable reference from execution-control program docs |
| `docs/archive/superpowers-legacy-execution-2026/**` | archived AI execution-control sources | mixed | exclude from curated audience navigation |
| `docs/audit/*` | non-curated audit baseline root | mixed | keep as governance baseline and evidence control |

## Additional top-level roots policy

An additional top-level docs root is allowed only if all are true:

1. It does not fit cleanly under `dev`, `admin`, or `user`.
2. It serves a strict non-audience function (for example external package distribution or AI execution control).
3. It has explicit owner and inclusion policy.
4. It is excluded from curated audience navigation.

## AI execution-control separation policy

AI execution-control docs must be either:

- stored in an explicit non-curated root; or
- labeled with a control-plane banner and excluded from audience maps.

They must not appear as first-line onboarding material for dev/admin/user readers.
