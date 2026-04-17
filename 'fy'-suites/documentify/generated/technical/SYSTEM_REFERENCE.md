# World of Shadows — technical reference

## Repository service map

- `frontend/`
- `administration-tool/`
- `backend/`
- `world-engine/`
- `ai_stack/`
- `story_runtime_core/`
- `writers-room/`

## Documentation domains

MVPs, admin, ai, api, architecture, archive, audit, audits, backend, database, dev, development, easy, features, forum, frontend, g9_evaluator_b_external_package, goc_evidence_templates, governance, implementation_reports, mcp, n8n, operations, plans, presentations, reference, reports, security, start-here, technical, testing, user, validation

## Automation and gates

admin-tests.yml, ai-stack-tests.yml, backend-tests.yml, compose-smoke.yml, despaghettify-skills-validate.yml, docify-skills-validate.yml, dockerify-skills-validate.yml, docs.yml, documentify-skills-validate.yml, engine-tests.yml, pre-deployment.yml, quality-gate.yml, testify-skills-validate.yml

## Canonical operational entrypoints

- `docker-up.py` — local Docker lifecycle
- `docker-compose.yml` — stack declaration
- `tests/run_tests.py` — multi-suite test runner
- `.github/workflows/` — GitHub Actions CI gates
