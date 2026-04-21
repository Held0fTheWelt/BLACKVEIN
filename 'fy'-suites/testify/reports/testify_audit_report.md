# Testify audit report

## Summary

- **workflow_count**: `13`
- **runner_suite_count**: `8`
- **hub_script_count**: `9`
- **finding_count**: `0`
- **warning_count**: `1`
- **analyze_mode_count**: `39`
- **canonical_schema_export_count**: `22`

## Runner coverage

- `tests/run_tests.py` suites: `['administration', 'ai_stack', 'backend', 'database', 'engine', 'frontend', 'improvement', 'writers_room']`
- `--suite all` order: `['backend', 'frontend', 'administration', 'engine', 'database', 'ai_stack']`

## Workflow coverage

- **admin-tests.yml** — jobs: `2`, path filters: `True`, workflow_dispatch: `False`
- **ai-stack-tests.yml** — jobs: `1`, path filters: `True`, workflow_dispatch: `False`
- **backend-tests.yml** — jobs: `6`, path filters: `True`, workflow_dispatch: `False`
- **compose-smoke.yml** — jobs: `1`, path filters: `False`, workflow_dispatch: `True`
- **despaghettify-skills-validate.yml** — jobs: `1`, path filters: `True`, workflow_dispatch: `False`
- **docify-skills-validate.yml** — jobs: `1`, path filters: `True`, workflow_dispatch: `False`
- **docs.yml** — jobs: `1`, path filters: `True`, workflow_dispatch: `False`
- **engine-tests.yml** — jobs: `2`, path filters: `True`, workflow_dispatch: `False`
- **fy-contractify-gate.yml** — jobs: `1`, path filters: `False`, workflow_dispatch: `False`
- **fy-despaghettify-gate.yml** — jobs: `1`, path filters: `False`, workflow_dispatch: `False`
- **fy-docify-gate.yml** — jobs: `1`, path filters: `False`, workflow_dispatch: `False`
- **pre-deployment.yml** — jobs: `2`, path filters: `False`, workflow_dispatch: `True`
- **quality-gate.yml** — jobs: `5`, path filters: `False`, workflow_dispatch: `False`

## Public modes

- mode keys: `['analyze.api', 'analyze.closure', 'analyze.code_docs', 'analyze.contract', 'analyze.docker', 'analyze.docs', 'analyze.observability', 'analyze.quality', 'analyze.readiness', 'analyze.security', 'analyze.structure', 'analyze.templates', 'analyze.usability', 'explain.code_docs', 'explain.contract', 'explain.docs', 'generate.closure_pack', 'generate.context_pack', 'generate.docs', 'generate.packaging_prep', 'generate.surface_aliases', 'govern.production', 'govern.release', 'import.mvp', 'inspect.api', 'inspect.closure', 'inspect.code_docs', 'inspect.contract', 'inspect.docker', 'inspect.docs', 'inspect.observability', 'inspect.quality', 'inspect.readiness', 'inspect.security', 'inspect.structure', 'inspect.templates', 'inspect.usability', 'metrics.governor_status', 'metrics.report']`
- missing analyze modes: `[]`

## Schema export

- canonical source complete: `True`
- canonical export complete: `True`
- export count: `22`

## Strengths

- Core GitHub Actions workflow set is present for backend, admin, engine, AI stack, quality gate, pre-deployment, and compose smoke.
- Root pyproject exports all fy-suite console scripts, including dockerify, testify, and documentify.
- tests/run_tests.py declares canonical --suite all order: backend, frontend, administration, engine, database, ai_stack.
- tests/run_tests.py declares explicit suite targets for: administration, ai_stack, backend, database, engine, frontend, improvement, writers_room.
- Mode registry exposes the required public analyze modes for contract, quality, code_docs, and docs.
- Canonical schema source files and exported schema bundle are both complete for the current evolution slice.

## Warnings

- No standalone frontend-tests.yml workflow detected; frontend quality currently relies on broader gates or local runner usage.

## Findings

- None.
