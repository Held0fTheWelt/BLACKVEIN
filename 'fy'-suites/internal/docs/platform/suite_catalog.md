# fy Suite Catalog

This is the product-facing catalog of all suites currently present in the autark fy workspace.

- suite_count: `15`
- core_count: `13`
- optional_count: `2`

## coda

- category: `core`
- quality_ok: `true`
- release_ready: `true`
- latest_run_id: `coda-9d3a3fcdc9ff`

Owns bounded closure-pack assembly, review-first completion packaging, and explicit residue reporting.

### Lifecycle commands

- `init`
- `inspect`
- `audit`
- `explain`
- `prepare-context-pack`
- `compare-runs`
- `clean`
- `reset`
- `triage`
- `prepare-fix`
- `self-audit`
- `release-readiness`
- `production-readiness`

### Native commands

- `assemble`
- `closure-pack`
- `residue-report`
- `bundle`

### Warnings

- `missing_optional:docs`
- `missing_optional:tests`

## contractify

- category: `core`
- quality_ok: `true`
- release_ready: `false`
- latest_run_id: `none`

Discovers, audits, explains, and consolidates contracts and projections.

### Lifecycle commands

- `init`
- `inspect`
- `audit`
- `explain`
- `prepare-context-pack`
- `compare-runs`
- `clean`
- `reset`
- `triage`
- `prepare-fix`
- `self-audit`
- `release-readiness`
- `production-readiness`

### Native commands

- `consolidate`
- `import`
- `legacy-import`

### Warnings

- `missing_optional:docs`

## despaghettify

- category: `core`
- quality_ok: `true`
- release_ready: `true`
- latest_run_id: `despaghettify-105bba0fb9e8`

Detects structural complexity and opens work for local spikes and broader cleanup.

### Lifecycle commands

- `init`
- `inspect`
- `audit`
- `explain`
- `prepare-context-pack`
- `compare-runs`
- `clean`
- `reset`
- `triage`
- `prepare-fix`
- `self-audit`
- `release-readiness`
- `production-readiness`

### Native commands

- `wave-plan`

### Warnings

- `missing_optional:docs`

## diagnosta

- category: `core`
- quality_ok: `true`
- release_ready: `true`
- latest_run_id: `diagnosta-a2d07a0ac407`

Owns bounded readiness diagnosis, blocker prioritization, and claim-honesty outputs across suites.

### Lifecycle commands

- `init`
- `inspect`
- `audit`
- `explain`
- `prepare-context-pack`
- `compare-runs`
- `clean`
- `reset`
- `triage`
- `prepare-fix`
- `self-audit`
- `release-readiness`
- `production-readiness`

### Native commands

- `diagnose`
- `readiness-case`
- `blocker-graph`

### Warnings

- `missing_optional:docs`
- `missing_optional:tests`

## docify

- category: `core`
- quality_ok: `true`
- release_ready: `false`
- latest_run_id: `none`

Improves code documentation, docstrings, and dense inline explanations for Python code.

### Lifecycle commands

- `init`
- `inspect`
- `audit`
- `explain`
- `prepare-context-pack`
- `compare-runs`
- `clean`
- `reset`
- `triage`
- `prepare-fix`
- `self-audit`
- `release-readiness`
- `production-readiness`

### Native commands

- `inline-explain`

### Warnings

- `missing_optional:docs`

## dockerify

- category: `optional`
- quality_ok: `true`
- release_ready: `false`
- latest_run_id: `none`

Provides repo-serving Docker and compose governance when the target repository needs it.

### Lifecycle commands

- `init`
- `inspect`
- `audit`
- `explain`
- `prepare-context-pack`
- `compare-runs`
- `clean`
- `reset`
- `triage`
- `prepare-fix`
- `self-audit`
- `release-readiness`
- `production-readiness`

### Native commands

- `stack-audit`

### Warnings

- `missing_optional:docs`

## documentify

- category: `core`
- quality_ok: `true`
- release_ready: `false`
- latest_run_id: `none`

Builds and grows documentation tracks, including status and AI-readable exports.

### Lifecycle commands

- `init`
- `inspect`
- `audit`
- `explain`
- `prepare-context-pack`
- `compare-runs`
- `clean`
- `reset`
- `triage`
- `prepare-fix`
- `self-audit`
- `release-readiness`
- `production-readiness`

### Native commands

- `generate-track`

### Warnings

- `missing_optional:docs`

## metrify

- category: `core`
- quality_ok: `true`
- release_ready: `false`
- latest_run_id: `none`

Measures AI usage, cost, model routing, and output volume across fy suites and summarizes the spending/utility picture.

### Lifecycle commands

- `init`
- `inspect`
- `audit`
- `explain`
- `prepare-context-pack`
- `compare-runs`
- `clean`
- `reset`
- `triage`
- `prepare-fix`
- `self-audit`
- `release-readiness`
- `production-readiness`

### Native commands

- `pricing`
- `record`
- `ingest`
- `report`
- `ai-pack`
- `full`

## mvpify

- category: `core`
- quality_ok: `true`
- release_ready: `false`
- latest_run_id: `none`

Imports prepared MVP bundles, mirrors their docs into the governed workspace, and orchestrates next-step implementation across suites.

### Lifecycle commands

- `init`
- `inspect`
- `audit`
- `explain`
- `prepare-context-pack`
- `compare-runs`
- `clean`
- `reset`
- `triage`
- `prepare-fix`
- `self-audit`
- `release-readiness`
- `production-readiness`

### Native commands

- `inspect`
- `plan`
- `ai-pack`
- `full`

## observifyfy

- category: `core`
- quality_ok: `true`
- release_ready: `true`
- latest_run_id: `observifyfy-8fbc874c8978`

Tracks internal fy-suite operations, internal docs roots, and non-contaminating cross-suite observability.

### Lifecycle commands

- `init`
- `inspect`
- `audit`
- `explain`
- `prepare-context-pack`
- `compare-runs`
- `clean`
- `reset`
- `triage`
- `prepare-fix`
- `self-audit`
- `release-readiness`
- `production-readiness`

### Native commands

- `inspect`
- `audit`
- `ai-pack`
- `full`

## postmanify

- category: `optional`
- quality_ok: `true`
- release_ready: `false`
- latest_run_id: `none`

Refreshes Postman surfaces from API evidence for repositories that use them.

### Lifecycle commands

- `init`
- `inspect`
- `audit`
- `explain`
- `prepare-context-pack`
- `compare-runs`
- `clean`
- `reset`
- `triage`
- `prepare-fix`
- `self-audit`
- `release-readiness`
- `production-readiness`

### Native commands

- `sync`

### Warnings

- `missing_optional:docs`

## securify

- category: `core`
- quality_ok: `true`
- release_ready: `false`
- latest_run_id: `none`

Provides the security lane for scans, secret-risk review, and security-oriented guidance.

### Lifecycle commands

- `init`
- `inspect`
- `audit`
- `explain`
- `prepare-context-pack`
- `compare-runs`
- `clean`
- `reset`
- `triage`
- `prepare-fix`
- `self-audit`
- `release-readiness`
- `production-readiness`

### Native commands

- `scan`
- `evaluate`
- `autofix`

## templatify

- category: `core`
- quality_ok: `true`
- release_ready: `false`
- latest_run_id: `none`

Owns and validates reusable templates for reports, docs, context packs, and suite outputs.

### Lifecycle commands

- `init`
- `inspect`
- `audit`
- `explain`
- `prepare-context-pack`
- `compare-runs`
- `clean`
- `reset`
- `triage`
- `prepare-fix`
- `self-audit`
- `release-readiness`
- `production-readiness`

### Native commands

- `list-templates`
- `validate`
- `render`
- `check-drift`

## testify

- category: `core`
- quality_ok: `true`
- release_ready: `false`
- latest_run_id: `none`

Audits test governance and verifies ADR-to-test reflection, not just passing behavior.

### Lifecycle commands

- `init`
- `inspect`
- `audit`
- `explain`
- `prepare-context-pack`
- `compare-runs`
- `clean`
- `reset`
- `triage`
- `prepare-fix`
- `self-audit`
- `release-readiness`
- `production-readiness`

### Warnings

- `missing_optional:docs`

## usabilify

- category: `core`
- quality_ok: `false`
- release_ready: `false`
- latest_run_id: `none`

Surfaces human-usable status, UX guidance, and understandable next-step outputs.

### Lifecycle commands

- `init`
- `inspect`
- `audit`
- `explain`
- `prepare-context-pack`
- `compare-runs`
- `clean`
- `reset`
- `triage`
- `prepare-fix`
- `self-audit`
- `release-readiness`
- `production-readiness`

### Native commands

- `inspect`
- `evaluate`
- `full`

### Missing required surfaces

- `README.md`
- `adapter/service.py`
- `adapter/cli.py`
- `tools`
- `reports`
- `state`
- `templates`

### Warnings

- `missing_optional:docs`
- `missing_optional:tests`
- `missing_optional:__init__.py`
