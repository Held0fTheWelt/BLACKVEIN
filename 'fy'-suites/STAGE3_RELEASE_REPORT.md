# Fy Suite Stage 3 MVP Report

## Status

This package is the next complete MVP after the prior Stage-2 build.
It performs **hardening first** and then extends the architecture in line with the target constraints:

- autark `fy` workspace
- outward-only operation against target repositories
- internal governance, internal docs, internal state
- functioning tests as a gate
- complete suite adapters remain present
- Docker/Postman support stays optional and repo-serving, not platform-defining

## What was hardened

### Platform hardening
- hardened `workspace_root()` resolution so explicit suite-owned roots can be used in tests and controlled bootstrap cases
- richer registry contract in `fy_platform/ai/evidence_registry/registry.py`
  - evidence review-state transitions
  - run comparison deltas
  - evidence listing support
- hardened review policy in `fy_platform/ai/policy/review_policy.py`
- richer semantic index hit model in `fy_platform/ai/semantic_index/index_manager.py`
  - suite metadata in retrieval hits
  - artifact-path summary support
- richer context-pack output in `fy_platform/ai/context_packs/service.py`
- hardened CLI behavior in `fy_platform/tools/ai_suite_cli.py`
  - `--format json|markdown`
  - `--strict`
  - graph-recipe-backed inspect/audit/triage/context-pack flows

### Adapter hardening
- `contractify consolidate` improved
  - smart auto-resolution when one test candidate is clearly stronger than the rest
  - user-input stop remains when ambiguity stays unresolved
- `despaghettify` global category is now robust against isolated local spikes
  - local spikes still trigger wave plans
  - global category no longer gets over-penalized by a single outlier

## What was architecturally extended

### Graph recipes added
- `fy_platform/ai/graph_recipes/recipe_base.py`
- `inspect_graph.py`
- `audit_graph.py`
- `triage_graph.py`
- `context_pack_graph.py`

These are lightweight internal orchestration recipes for the MVP layer and prepare the platform for later deeper graph/runtime growth.

### Documentify expanded
`documentify` now generates a fuller internal documentation bundle through `documentify/tools/track_engine.py`:
- `easy`
- `technical`
- `role-admin`
- `role-developer`
- `role-operator`
- `role-writer`
- `role-player`
- `ai-read`
- manifest and index outputs

### Despaghettify expanded
`despaghettify` now produces a concrete remediation wave plan:
- local spike detection
- severity assignment
- action list for split/extract work
- robust low global category retention when only local outliers exist

## Validation

Executed successfully in this build:

- `pytest -q`
- **30 tests passed**

## Main files touched

- `fy_platform/ai/evidence_registry/registry.py`
- `fy_platform/ai/policy/review_policy.py`
- `fy_platform/ai/semantic_index/index_manager.py`
- `fy_platform/ai/context_packs/service.py`
- `fy_platform/ai/base_adapter.py`
- `fy_platform/ai/adapter_cli_helper.py`
- `fy_platform/ai/graph_recipes/*`
- `fy_platform/tools/ai_suite_cli.py`
- `documentify/tools/track_engine.py`
- `documentify/adapter/service.py`
- `despaghettify/adapter/service.py`
- `contractify/adapter/service.py`
- new/updated tests across `fy_platform`, `contractify`, `documentify`, `despaghettify`

## Resulting maturity

This is still an MVP, but it is materially stronger than the previous stage:
- harder platform core
- richer CLI contract
- richer documentation generation
- better local-spike handling
- smarter contract consolidation
- broader internal orchestration structure

It remains intentionally bounded and does not yet claim final production hardening.
