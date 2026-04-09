# God of Carnage Canonical Path (Block 3 — Gate)

## Canonical Decision

- **Primary operational path:** published backend experience content.
- **Secondary path only:** World-Engine builtin `god_of_carnage_solo` for fallback, tests, and local demo/offline behavior.
- Builtin content must not evolve as an equal primary source.

## Authoritative Runtime Context

The live run executes in **World-Engine / Play-Service**. Backend is orchestration/content/auth/admin and publishes playable experience templates consumed by World-Engine.

## Canonical Load Flow

`Published Backend Content -> World-Engine Content Loading -> Runtime Execution`

1. Backend exposes published templates via `GET /api/v1/game/content/published` as `{ "templates": [...] }`.
2. World-Engine `backend_loader.load_published_templates()` validates payloads as `ExperienceTemplate`.
3. `RuntimeManager.sync_templates()` overlays matching IDs and marks source as `backend_published`.
4. Runs are created from the resolved template and executed only in Play-Service.

## MCP Position (Explicit)

- For this run-lifecycle/content-load path, MCP is **not** in the direct runtime execution chain.
- MCP is used on backend operator/session surfaces where explicitly defined (for example protected session diagnostics/snapshot endpoints), but not for `GET/POST/DELETE /api/runs*` play-service runtime operations.
- Therefore, this gate validates MCP truthfully by documenting it as **out of scope** for the direct run-lifecycle path and **in scope** for dedicated backend operator/session paths.

## Fallback Semantics

- If backend content feed is unavailable or invalid, World-Engine keeps builtin templates active.
- Fallback is intentional for resilience, but it is non-primary and must not become a second publication authority.

## Drift Controls

- Tests must prove:
  - published content overrides builtin when available for the same template ID,
  - builtin remains available when upstream feed fails,
  - source attribution remains explicit (`backend_published` vs `builtin`).
- Documentation and code comments must keep these source roles explicit.
