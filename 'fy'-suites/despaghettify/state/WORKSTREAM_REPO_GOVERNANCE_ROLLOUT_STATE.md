# Workstream: repo_governance_rollout

## Closed — DS-006 (session 20260520)

Scan-scope hygiene for despaghettify metrics. The wave aligns `fy-manifest.yaml` with the product-code roots required by `spaghetti-check-task.md`, then refreshes `latest_check_with_metrics.json` and the implementation input scan section.

**Wave plan:** `artifacts/workstreams/repo_governance_rollout/pre/session_20260520_DS-006_wave_plan.json`

**Pre artefacts:**

- `artifacts/workstreams/repo_governance_rollout/pre/session_20260520_DS-006_w01_scope_snapshot.md`
- `artifacts/workstreams/repo_governance_rollout/pre/session_20260520_DS-006_w01_scope_snapshot.json`

**Post artefacts:**

- `artifacts/workstreams/repo_governance_rollout/post/session_20260520_DS-006_w01_scope_comparison.md`
- `artifacts/workstreams/repo_governance_rollout/post/session_20260520_DS-006_w01_scope_comparison.json`

**Gates (final):**

- `PYTHONPATH="'fy'-suites" DESPAG_SKIP_ARCHIVE_SYNC=1 python -m despaghettify.tools.hub_cli check --with-metrics --out "'fy'-suites/despaghettify/reports/latest_check_with_metrics.json"` — pass
- `PYTHONPATH="'fy'-suites" python "'fy'-suites/despaghettify/tools/spaghetti_ast_scan.py"` — pass
