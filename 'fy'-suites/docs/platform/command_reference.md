# fy Command Reference

This page lists the stable shared lifecycle commands and the suite-specific native commands.

- command_envelope_current: `fy.command-envelope.v4`
- supported_read_versions: `fy.command-envelope.v3, fy.command-envelope.v4`
- supported_write_versions: `fy.command-envelope.v4`

- active_strategy_profile: `D`
- canonical_candidate_e_closure_report: `docs/platform/READINESS_CLOSURE_CANDIDATE_E_CLOSURE_REPORT.md`

## Platform-native commands

- `strategy show`
- `strategy set <A|B|C|D|E>`

## Generic lifecycle commands

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

## Suite-native commands

### coda

- `assemble`
- `closure-pack`
- `residue-report`
- `bundle`

### contractify

- `consolidate`
- `import`
- `legacy-import`

### despaghettify

- `wave-plan`

### diagnosta

- `diagnose`
- `readiness-case`
- `blocker-graph`

### docify

- `inline-explain`

### dockerify

- `stack-audit`

### documentify

- `generate-track`

### metrify

- `pricing`
- `record`
- `ingest`
- `report`
- `ai-pack`
- `full`

### mvpify

- `inspect`
- `plan`
- `ai-pack`
- `full`

### observifyfy

- `inspect`
- `audit`
- `ai-pack`
- `full`

### postmanify

- `sync`

### securify

- `scan`
- `evaluate`
- `autofix`

### templatify

- `list-templates`
- `validate`
- `render`
- `check-drift`

### testify

- no additional native commands

### usabilify

- `inspect`
- `evaluate`
- `full`
