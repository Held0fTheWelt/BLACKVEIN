# World of Shadows — simple overview

World of Shadows is a multi-service narrative platform.
The repository currently exposes these major service/package areas: **frontend, administration-tool, backend, world-engine, ai_stack, story_runtime_core, writers-room**.

## What starts the local stack

- `docker-up.py` is the operator-friendly entry path for Docker Compose.
- `docker-compose.yml` declares the main local stack services.
- `tests/run_tests.py` is the canonical multi-suite test runner.

## Where to begin reading

- `README.md`
- `docs/start-here/README.md`
- `docs/technical/README.md`
- `docs/testing/README.md`
- `docs/operations/RUNBOOK.md`
- `tests/TESTING.md`
- `docker-up.py`
- `tests/run_tests.py`
