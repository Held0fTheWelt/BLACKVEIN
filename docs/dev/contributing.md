# Contributing and repository layout

Orientation for **developers** working across World of Shadows services. For plain-language system context, read [Start here](../start-here/README.md) first.

## Repository language

**Canonical policy (single source of truth):** Change **only this section** when repository language rules change. Root **`AGENTS.md`**, **`CONTRIBUTING.md`**, `'fy'-suites/despaghettify/**`, and `'fy'-suites/despaghettify/state/**` must **not** duplicate this text — they **link here** so wording cannot drift or break across entry points.

**Policy:** **Strict English** for all **committed**, maintainer- and operator-facing text: `docs/`, package and root READMEs, code **comments** and **docstrings**, **commit messages**, logs and messages intended for developers or operators (unless a feature is explicitly internationalized with documented locale rules), and **human-readable** governance and evidence (including everything under `'fy'-suites/despaghettify/` and `'fy'-suites/despaghettify/state/artifacts/`). Fictional or in-world **player-facing narrative** under `content/modules/` may follow creative tone for that layer; **keys, inline hints to authors, schemas, and tooling** around that content stay English.

**Layering:** Procedure-specific docs (for example each Despaghettify task Markdown `**Language:**` line) add **scope for that procedure only** and link to this heading — they do **not** restate or narrow the policy above.

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

## Monorepo Python bootstrap (import hygiene)

- Run **pytest from each service root** (`backend/`, `world-engine/`) so the top-level `app` package resolves to that service only. Avoid a single shell `PYTHONPATH` that mixes `backend/` and `world-engine/` when importing `app`.
- CI workflows should keep **working-directory scoped** install and test steps per service; mirror that locally when debugging import collisions.

### Supported test invocation matrix (M2)

Use the same **working directory** as CI so `app` resolves to the intended package. **Do not** run the backend or world-engine pytest trees **from the repository root** with a bare `pytest` invocation that collects those packages without `cd` into the service directory first (both trees expose a top-level `app` package name; root-level collection risks the wrong `app`).

| Intent | Supported invocation | CI equivalent |
|--------|----------------------|---------------|
| Backend tests | `cd backend` then `python -m pytest tests/ …` | [`.github/workflows/backend-tests.yml`](../../.github/workflows/backend-tests.yml) `working-directory: backend` |
| World Engine tests | `cd world-engine` then `python -m pytest tests/ …` | [`.github/workflows/engine-tests.yml`](../../.github/workflows/engine-tests.yml) `working-directory: world-engine` |
| AI stack tests | Repo root: `PYTHONPATH=<repo>` `python -m pytest ai_stack/tests …` (see `ai_stack` README / workflow) | [`.github/workflows/ai-stack-tests.yml`](../../.github/workflows/ai-stack-tests.yml) |
| **Forbidden for backend / world-engine suites** | `pytest` from repo root collecting `backend/tests` or `world-engine/tests` without matching CI cwd / env | Same as above — wrong `app` |

**Convenience (optional):** from repo root, GNU Make: `make test-backend`, `make test-engine`, `make test-ai-stack`. On Windows, PowerShell: `.\scripts\run_backend_tests.ps1`, `.\scripts\run_world_engine_tests.ps1`, `.\scripts\run_ai_stack_tests.ps1`.

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

## Despaghettify and Cursor agent skills

**Repo standard:** Despaghettify **agent skills** under **`'fy'-suites/despaghettify/superpowers/`** are **thin routers** (they point at task Markdown only — **no** duplicated M7 thresholds or checklists). **Trigger values** and the full analysis procedure are **only** in `'fy'-suites/despaghettify/spaghetti-check-task.md`. Cursor loads **project** skills from **`.cursor/skills/`**; this repository **commits** mirrored copies so every clone gets the same skills.

After **any** edit to `'fy'-suites/despaghettify/superpowers/*/SKILL.md`, run from the repository root:

```bash
python "./'fy'-suites/despaghettify/tools/sync_despag_skills.py"
```

Optional drift check (e.g. in CI): `python "./'fy'-suites/despaghettify/tools/sync_despag_skills.py" --check` (exit **1** if `.cursor/skills` is out of date). Do not edit `.cursor/skills/` in isolation — sync will overwrite it.

**Skill markdown links:** run `python "./'fy'-suites/despaghettify/tools/validate_despag_skill_paths.py"` after changing paths under `'fy'-suites/despaghettify/superpowers/` (CI: `.github/workflows/despaghettify-skills-validate.yml`). See [`'fy'-suites/despaghettify/superpowers/references/VALIDATION.md`](../../'fy'-suites/despaghettify/superpowers/references/VALIDATION.md).

See also root **`AGENTS.md`**, [`'fy'-suites/despaghettify/superpowers/README.md`](../../'fy'-suites/despaghettify/superpowers/README.md), and [`'fy'-suites/despaghettify/README.md`](../../'fy'-suites/despaghettify/README.md).

## Contractify (repository contracts)

**Contract governance** (anchors vs projections, drift JSON, **CG-*** backlog) lives under [`'fy'-suites/contractify/`](../../'fy'-suites/contractify/README.md). Router skills mirror into **`.cursor/skills/`** via **`python "./'fy'-suites/contractify/tools/sync_contractify_skills.py"`** — same copy-only rule as other fy suites.

## Related

- [Architecture README](../architecture/README.md)
- [Documentation registry](../reference/documentation-registry.md)
