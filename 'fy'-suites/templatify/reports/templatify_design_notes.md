# Templatify design notes

## Why this suite exists

The current repository already has strong Jinja inheritance patterns across these areas:

- `frontend/templates/`
- `administration-tool/templates/`
- `administration-tool/templates/manage/`
- `backend/app/info/templates/`
- `writers-room/app/templates/`

That means a shell-integration tool can safely work at the **base-template layer** instead of rewriting page templates.

## Current documentation implications

The documentation surface is already broad, but the generated `documentify` outputs are still much thinner than the actual repository documentation.

Practical next-wave direction:

- **easy** docs should imitate the calm, stepwise style already visible under `docs/easy/` and `docs/start-here/`.
- **technical** docs should grow toward a layered industrial suite: architecture, runtime, integrations, operations, testing, reference, ADRs.
- **role** docs should become richer but easier to scan, with explicit task maps, first actions, routine actions, failure actions, and key URLs/commands.
- **AI-facing** docs should gain machine-friendly indexes, chunk manifests, concept maps, and canonical path registries.

## Templatify scope

Templatify does not replace Documentify. It provides a repeatable way to:

1. consume a designer-owned source shell,
2. map it onto existing Jinja block names,
3. generate safe area adapters,
4. preserve child-template content.

That makes it a useful companion for both UI implementation and documentation screenshots/examples later.
