# World Engine console — accessibility specification

Targets WCAG 2.2 AA-oriented behavior for the implemented surfaces: `/manage/world-engine-console`, `/ops` on world-engine, and related manage navigation.

## Landmarks and structure

- **Admin console:** `{% extends manage/base.html %}` — uses existing `header`, `nav[aria-label="Management"]`, `main#main[role="main"]`. Page section is a single `section.manage-section` with a descriptive `h1`.
- **Ops page:** single `main#main[role="main"]`; one `h1`; sections use `aria-labelledby` pointing at `h2` ids.

## Live regions

- **Admin:** `#wec-banner` uses `role="status"` and `aria-live="polite"` for errors and capability denial (mirrors Play-Service control pattern).
- **Ops:** `#ops-banner` uses `role="status"`, `aria-live="polite"`, `aria-atomic="true"` so readiness changes announce as one unit.
- **Polling:** Optional 5s poll in admin console; operators should pause polling when using a screen reader for long JSON review (checkbox stops timer). Prefer polite live regions over `assertive` unless safety-critical.

## Status and color

- Ops page: status strip includes **text** (“Engine responded…”) in addition to background/border color classes (`.ok` / `.err`).
- Admin: banner text carries the error message; do not rely on color alone for run termination (confirm dialog + button label “Terminate run”).

## Focus and keyboard

- All primary actions are native `button` or `submit` controls (no div-buttons).
- Terminate uses `window.confirm` before POST — acceptable pattern; ensure focus returns to a sensible element after refresh (future: replace with modal + focus trap).
- Navigation: World Engine link participates in tab order like other manage nav links.

## JSON / pre blocks

- Large `pre` regions have `aria-label` where multiple blocks exist (readiness vs run detail vs story state) so screen reader users can distinguish them.

## Feature-gated UI

- Capability line (`#wec-caps`) exposes effective tier in plain language (“Effective: observe → operate → author”) so users understand why controls are missing without opening devtools.

## Copy and language

- Default manage `lang` is `de` from base template; ops template currently `lang="en"` to match existing play prototype — align with product decision if German copy is required on `/ops`.

## Testing checklist (manual)

1. Tab through `/manage/world-engine-console` with only `observe`: terminate and forms hidden, lists operable.
2. VoiceOver/NVDA: announce banner on forced error (e.g. stop backend).
3. Zoom 200%: two-column grid should stack (rely on existing `manage-grid` responsive rules).
