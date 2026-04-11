# Task 3 — Machine-Check Command Set

This command set is the executable acceptance surface for Task 3 outputs.

## 1) Historical naming residue in active affected test filenames

Primary ripgrep-style rule (execution target):

```bash
rg -n "(^|/)test_.*(area2|task(_|[0-9])|workstream|phase[0-9]*|final|closure)(_|\.|$)" backend/tests ai_stack/tests tests tools/mcp_server/tests
```

Wave-token extension rule:

```bash
rg -n "(^|/)test_w[0-9]+_.*\.py$" tests
```

Pass condition:
- No matches remain, except suites explicitly listed in `docs/audit/task3_retained_gate_suites.json` and justified there.

## 2) Sidecar disposition coverage

Required artifact:
- `docs/audit/task3_sidecar_disposition.json`

Checks:

```bash
rg -n "\"status\":\s*\"(merged|justified_standalone|removed)\"" docs/audit/task3_sidecar_disposition.json
rg -n "\"sidecar_path\"|\"owner_suite\"|\"status\"|\"justification\"" docs/audit/task3_sidecar_disposition.json
```

Pass condition:
- Every sidecar row includes required fields and an allowed `status`.

## 3) Retained gate-suite justification coverage

Required artifact:
- `docs/audit/task3_retained_gate_suites.json`

Check:

```bash
rg -n "\"suite_path\"|\"retention_reason\"|\"non_redundant_value\"|\"consumer\"" docs/audit/task3_retained_gate_suites.json
```

Pass condition:
- Every retained suite entry includes all required rationale fields.

## 4) Baseline re-validation presence

Required artifact:
- `docs/audit/TASK_3_BASELINE_REVALIDATION_NOTE.md`

Check:

```bash
rg -n "Task 1A|Task 1B|stale|revalid" docs/audit/TASK_3_BASELINE_REVALIDATION_NOTE.md
```

Pass condition:
- Baseline usage and staleness/re-validation policy are explicitly present.
