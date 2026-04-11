# Contributing and repository layout

Orientation for **developers** working across World of Shadows services. For plain-language system context, read [Start here](../start-here/README.md) first.

## Top-level layout

| Path | Responsibility |
|------|----------------|
| `frontend/` | Player/public Flask app |
| `administration-tool/` | Admin Flask app |
| `backend/` | API, auth, migrations, content compiler, integration |
| `world-engine/` | Play service (FastAPI): authoritative runtime |
| `ai_stack/` | LangGraph executor, RAG, GoC seams, LangChain bridges, capabilities |
| `story_runtime_core/` | Shared interpretation, model registry, adapters |
| `content/modules/` | Canonical YAML modules (`god_of_carnage/`, …) |
| `writers-room/` | Optional demo UI → backend Writers Room API |
| `tools/mcp_server/` | MCP server for operator/developer tooling |
| `schemas/` | JSON schemas shared across services |
| `tests/` | Repo-root smoke and gate helpers |
| `docs/` | Documentation (audience-first + architecture + audit) |

## Path hazards

- **Two “world-engine” paths:** canonical play service code lives in **root** `world-engine/`. A nested `backend/world-engine/` tree has been flagged as **confusing** in audit baselines—verify before editing or documenting paths.
- **Gitignored evidence:** `tests/reports/` is largely ignored; do not cite it as clone-guaranteed in user/admin docs.

## Package READMEs

Each major service maintains its own README with install and test hints:

- `backend/README.md`
- `world-engine/README.md`
- `frontend/README.md`
- `ai_stack/README.md` (if present) / `world-engine/requirements-dev.txt` for graph tests

## Development workflow

1. Follow [Local development and test workflow](local-development-and-test-workflow.md) for URLs and env vars.
2. Run the **smallest** relevant pytest package before wide suites (see [Test pyramid and suite map](testing/test-pyramid-and-suite-map.md)).
3. When touching GoC behavior, read the [normative contracts index](contracts/normative-contracts-index.md).

## AI and runtime changes

Cross-stack edits often touch `ai_stack/`, `world-engine/`, and `content/modules/` together. Review `docs/audit/TASK_1B_CROSS_STACK_COHESION_BASELINE.md` for seam vocabulary before large refactors.

## Related

- [Architecture README](../architecture/README.md)
- [Documentation registry](../reference/documentation-registry.md)
