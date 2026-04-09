# Inspector Suite Canonical Workbench

## Canonical UI surface

The only real Inspector Suite product UI in the administration tool is this pair:

- Template: `administration-tool/templates/manage/inspector_workbench.html`
- Script: `administration-tool/static/manage_inspector_workbench.js`

Superseded standalone pages (`ai_stack_governance.html`, `inspector_suite.html` and their JS bundles) are **not** present as parallel surfaces; legacy URLs are redirect-only.

**Provenance / Raw UX:** Provenance canonical entries must render as the **primary** operator surface; raw evidence remains **explicitly secondary** diagnostic material and must never replace the canonical view.

## Canonical entrypoint

- Canonical administration route: `/manage/inspector-workbench`
- Canonical Flask endpoint: `manage_inspector_workbench`
- Legacy routes are permanently redirected (`308`) to the canonical workbench:
  - `/manage/ai-stack/governance`
  - `/manage/ai-stack-governance`
  - `/manage/inspector-suite`
  - `/manage/inspector-suite/turn`

## Read-only backend projections

Inspector Suite is backend-owned and read-only. The administration tool renders projection payloads and never computes canonical semantics in browser code.

Explicit read-only endpoints:

- `GET /api/v1/admin/ai-stack/inspector/turn/<session_id>?mode=canonical|raw`
- `GET /api/v1/admin/ai-stack/inspector/timeline/<session_id>`
- `GET /api/v1/admin/ai-stack/inspector/comparison/<session_id>`
- `GET /api/v1/admin/ai-stack/inspector/coverage-health/<session_id>`
- `GET /api/v1/admin/ai-stack/inspector/provenance-raw/<session_id>?mode=canonical|raw`

All endpoints are moderator/admin authenticated, feature-gated, rate-limited, and GET-only.

## Canonical sections and stance

- **Turn Inspector**: canonical single-turn projection (authority, validation, gate, fallback, rejection, trace).
- **Timeline**: multi-turn progression from emitted diagnostics.
- **Comparison**: mandatory bounded turn-to-turn within one session; unsupported dimensions remain explicit.
- **Coverage / Health**: distributions and frequencies from existing evidence.
- **Provenance / Raw**: provenance entries and optional raw drilldown.

Raw evidence is inspectable operator material only.
Raw evidence is never treated as canonical semantic truth in UI logic.
Canonical sections remain renderable without raw mode.

## Unsupported and unavailable semantics

Projection sections use explicit status envelopes:

- `supported`
- `unsupported`
- `unavailable`

Each section keeps explicit `unsupported_reason` / `unavailable_reason` instead of UI-side truth reconstruction.

## Non-goals

- No planner redesign
- No gate redesign
- No runtime behavior redesign
- No write/preview/counterfactual mutation tooling
- No fabricated analytics beyond emitted evidence
