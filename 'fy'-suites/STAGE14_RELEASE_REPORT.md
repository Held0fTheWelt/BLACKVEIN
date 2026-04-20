# fy Suite Stage 14 Consistency and Import Release

## Summary

This release closes four targeted product gaps:

1. **Old consumer migration to the current form**
   - canonical internal documentation now lives under `docs/` at the workspace root
   - legacy nested `'fy'-suites/docs/...` is treated as a compatibility source, not the primary target
   - old path consumers were migrated to the current form

2. **Release hygiene**
   - the release package is cleaned of `__pycache__`, `.pytest_cache`, `*.pyc`, `egg-info`, and runtime backup/cache noise
   - `.fydata` runtime directories remain present but are cleaned to a releasable baseline

3. **Top-level structure alignment**
   - the packaged product now has top-level root `'fy'-suites`
   - inside that root live `fy_platform`, `contractify`, `testify`, `documentify`, `docify`, `despaghettify`, `templatify`, `usabilify`, `securify`, `observifyfy`, optional suites, and `docs`

4. **Maturity uplift for newer suites**
   - `securify`, `usabilify`, and `observifyfy` are now treated as mature core suites in the same quality model
   - suite quality checks now recognize nested adapter/tool test trees instead of warning just because a top-level `tests/` folder is absent

## Contractify import expansion

`contractify` now supports two explicit import paths:

- `import` for current contractify-aware fy-suite bundles
- `legacy-import` for older or nested bundle layouts

The importer is designed so that prepared MVP bundles that ship their own `contractify` can be imported and normalized without overwriting current workspace truth.
Imported material lands under:

- `contractify/imports/<import-id>/normalized/...`

This keeps imported data observable and non-contaminating.

## Canonical documentation routing

Canonical internal product docs now route to:

- `docs/`
- `docs/ADR/`
- `docs/platform/`

Legacy nested docs can still be migrated in, but new platform-facing outputs are written to the current form.

## Validation

- `compileall`: passed
- full test run: **72 passed**

## Result

For the current autark fy-suite product scope, this release is:

- structurally more consistent
- cleaner as a release artifact
- better prepared for importing both current and legacy contractify data
- better aligned with the desired top-level `'fy'-suites` product shape
