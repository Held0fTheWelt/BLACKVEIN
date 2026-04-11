# World Engine console — low-fi wireframes (text)

Grounding: diagnose-first UX plan; implementation lives under `administration-tool` (`/manage/world-engine-console`), backend proxy `GET/POST /api/v1/admin/world-engine/*`, engine-near page `GET /ops` on the play service.

## 1. Engine-near: `/ops` (world-engine)

```
┌─────────────────────────────────────────────┐
│ ← Play prototype                            │
│ World Engine — lightweight ops              │
│ [status banner: live region]                │
├─────────────────────────────────────────────┤
│ Health payloads                             │
│ ┌─────────────────────────────────────────┐ │
│ │ { "status": "ok" }                      │ │
│ └─────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────┐ │
│ │ { "status": "ready", "store": … }       │ │
│ └─────────────────────────────────────────┘ │
│ [ Refresh ]                                 │
└─────────────────────────────────────────────┘
```

No authentication; only public `GET /api/health` and `GET /api/health/ready`.

## 2. Admin: dashboard card

Card title: **World Engine console**. Subcopy: readiness, runs, story sessions, hierarchical flags. Shown when user has any of `manage.world_engine_observe|operate|author` (`data-feature-any`).

## 3. Admin: `/manage/world-engine-console`

**Header row:** eyebrow Operations · H1 · lead copy · links (Play-Service control, Diagnosis, Game ops) · actions: Refresh, Poll checkbox.

**Row 2 (two panels):** Readiness JSON | Capabilities line (effective observe → operate → author).

**Row 3 (two columns):** Template runs (vertical list of buttons) | Story sessions (vertical list of buttons).

**Row 4 (two columns):** Run detail `pre` + [Terminate] (operate+) | Story state `pre` + diagnostics excerpt `pre` + turn form (author+) + create session form (author+).

### Detail flow (mental model)

1. Pick run → load `GET …/runs/{id}`; terminate posts to proxy.
2. Pick story session → parallel `state` + `diagnostics` (last 3 envelopes in UI for density).

## 4. Role variants (same layout, gated fields)

| Capability | Visible / enabled |
|------------|-------------------|
| observe | Lists, readiness, state, diagnostics, run detail read-only |
| operate | + Terminate run |
| author | + Create session, execute turn |

## 5. Future tabs (not in MVP shell)

Plan reference: Überblick → Live → Turn-Pipeline → Transcript → Rohdaten. Current MVP collapses “Überblick” into `state` JSON and pipeline peek into last diagnostics slice.
