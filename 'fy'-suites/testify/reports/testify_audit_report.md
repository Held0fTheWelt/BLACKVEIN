# Testify audit report

## Summary

- **workflow_count**: `13`
- **runner_suite_count**: `8`
- **hub_script_count**: `9`
- **finding_count**: `0`
- **warning_count**: `1`

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

## Strengths

- Core GitHub Actions workflow set is present for backend, admin, engine, AI stack, quality gate, pre-deployment, and compose smoke.
- Root pyproject exports all fy-suite console scripts, including dockerify, testify, and documentify.
- tests/run_tests.py declares canonical --suite all order: backend, frontend, administration, engine, database, ai_stack.
- tests/run_tests.py declares explicit suite targets for: administration, ai_stack, backend, database, engine, frontend, improvement, writers_room.

## Warnings

- No standalone frontend-tests.yml workflow detected; frontend quality currently relies on broader gates or local runner usage.

## Findings

- None.
