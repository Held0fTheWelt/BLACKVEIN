# DS-006 Pre Snapshot — Scan Scope Hygiene

## Wave Plan

| Sub-wave | Goal | Primary files / symbols | Gate |
|----------|------|-------------------------|------|
| 1 | Align despaghettify scan scope with the fixed product-code roots from `spaghetti-check-task.md`; prove vendored/generated environment trees no longer drive the latest metrics. | `fy-manifest.yaml`; latest despaghettify report and input list scan section | `wave-plan-validate`; `check --with-metrics`; `spaghetti_ast_scan.py` |

## Pre State

- Current `despaghettify.scan_roots` in `fy-manifest.yaml`: `backend`, `world-engine`, `ai_stack`, `story_runtime_core`, `frontend`, `writers-room`.
- Current AST telemetry from the latest report: `N=20859`, `L50=1365`, `L100=379`, `D6=58`.
- Current trigger-policy result: `M7_anteil=6.5004`, `M7_ref=4.24`, policy fires.
- Current top nesting includes vendored `world-engine/source/Lib/site-packages` entries, so DS-006 must settle the measurement boundary before product refactors chase C5/C6/C7 noise.
- Intended scope from `spaghetti-check-task.md`: `backend/app`, `world-engine/app`, `ai_stack`, `story_runtime_core`, `tools/mcp_server`, `administration-tool`.
