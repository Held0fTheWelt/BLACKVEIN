# DS-006 Post Snapshot — Scan Scope Hygiene

## Result

`fy-manifest.yaml` now points Despaghettify at the fixed product-code roots from `spaghetti-check-task.md`:

- `backend/app`
- `world-engine/app`
- `ai_stack`
- `story_runtime_core`
- `tools/mcp_server`
- `administration-tool`

The scan no longer counts `world-engine/source/Lib/site-packages`, backend migrations, or broad tests from `backend` / `world-engine` roots.

## Before → After

| Metric | Before | After |
|--------|--------|-------|
| total functions | 20859 | 10676 |
| Python files | 1893 | 1148 |
| L50 | 1365 | 858 |
| L100 | 379 | 236 |
| D6 | 58 | 27 |
| M7 Anteil | 6.5004 | 5.7013 |

Remaining triggers are product/tooling findings, not vendored environment noise. `world-engine/source/Lib/site-packages` no longer appears in the top nesting leaders.

## Gates

- `wave-plan-validate --check-primary-paths` — pass
- `check --with-metrics` — pass, report refreshed at `despaghettify/reports/latest_check_with_metrics.json`
- `spaghetti_ast_scan.py` — pass, roots printed as `backend/app`, `world-engine/app`, `ai_stack`, `story_runtime_core`, `tools/mcp_server`, `administration-tool`
