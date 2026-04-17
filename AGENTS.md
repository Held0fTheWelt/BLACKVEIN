# Agent notes (World of Shadows)

## Repository language

**Canonical wording:** [`docs/dev/contributing.md`](docs/dev/contributing.md) — heading **Repository language** (anchor `#repository-language`). Follow that section; do not treat this file as a second copy of the policy.

## Despaghettify hub

The Despaghettify hub (Python package **`despaghettify`**, task Markdown, **state/**) lives under **`'fy'-suites/despaghettify/`** alongside other repo-wide tool suites. Use **`pip install -e .`** at the repo root so `python -m despaghettify.tools …` resolves the package (see root **`pyproject.toml`**).

The root **`world-of-shadows-hub`** package declares **`[project.dependencies]`** that include the full **backend Flask + pytest** pin set (aligned with **`backend/requirements.txt`**, **`backend/requirements-dev.txt`**, and **`backend/requirements-test.txt`**). After **`pip install -e .`** alone, **`python tests/run_tests.py --suite backend`** must run without an extra **`pip install -r backend/...`** step. **`--suite all`** and engine / ai_stack work still require **`setup-test-environment.*`** (or the per-component installs documented in **`tests/run_tests.py`** / **`tests/TESTING.md`**).

### Repo standard (Cursor)

1. **Router skills** live under `'fy'-suites/despaghettify/superpowers/<skill-name>/SKILL.md` (minimal; edit only to improve routing or descriptions). **Procedure** lives in the task Markdowns (`spaghetti-check-task.md`, `spaghetti-solve-task.md`, etc.); **numeric** trigger policy lives in `'fy'-suites/despaghettify/spaghetti-setup.md` — never duplicate those in a skill.
2. **Cursor discovery** uses **`.cursor/skills/<skill-name>/SKILL.md`** (committed). After changing any canonical skill file, run **`python "./'fy'-suites/despaghettify/tools/sync_despag_skills.py"`** from the repo root before commit/PR (same as human contributors; optional CI: `python "./'fy'-suites/despaghettify/tools/sync_despag_skills.py" --check`).
3. Do **not** hand-edit only `.cursor/skills/` — it will be overwritten on the next sync. **Windows / macOS / Linux:** use **`python "./'fy'-suites/despaghettify/tools/sync_despag_skills.py"`** (file copy) only — **no** symlinks, **no** `mklink`; committed `.cursor/skills/` is what Cursor auto-loads.
4. **Language:** Same canonical policy as [`docs/dev/contributing.md`](docs/dev/contributing.md#repository-language). Hub files add **procedure-only scope** in `'fy'-suites/despaghettify/README.md` (**Language** paragraph) and each task Markdown `**Language:**` line — **links upward**, no restated project policy.

### References

- **CLI:** `python -m despaghettify.tools check` (`--with-metrics` optional) | `open-ds` | `solve-preflight --ds DS-nnn` | `autonomous-init` / `autonomous-advance` / `autonomous-status` / `autonomous-verify` | `metrics-emit` | `trigger-eval` (optional `pip install -e .` → `despag-check` / `wos-despag`) — see `'fy'-suites/despaghettify/superpowers/references/CLI.md`.
- **Task docs:** `'fy'-suites/despaghettify/spaghetti-check-task.md`, `spaghetti-solve-task.md`, `spaghetti-add-task-to-meet-trigger.md`, `spaghetti-autonomous-agent-task.md`; numeric policy `'fy'-suites/despaghettify/spaghetti-setup.md`; input list `'fy'-suites/despaghettify/despaghettification_implementation_input.md`.

Human-oriented contributor wording also lives in **root `CONTRIBUTING.md`** and **`docs/dev/contributing.md`** (Despaghettify and Cursor agent skills).

**Skill path validation:** `python "./'fy'-suites/despaghettify/tools/validate_despag_skill_paths.py"` (see `'fy'-suites/despaghettify/superpowers/references/VALIDATION.md`; GitHub Actions runs on relevant diffs).

## Postmanify hub

1. **Router skill** lives under `'fy'-suites/postmanify/superpowers/postmanify-sync/SKILL.md`. **Procedure** lives in `'fy'-suites/postmanify/postmanify-sync-task.md`.
2. **Cursor discovery:** after editing that skill, run **`python "./'fy'-suites/postmanify/tools/sync_postmanify_skills.py"`** from the repo root (same copy-only rule as Despaghettify — no symlinks).
3. **CLI:** `python -m postmanify.tools plan` | `generate` (requires **`pip install -e .`**) — see `'fy'-suites/postmanify/superpowers/references/CLI.md`. Console script **`postmanify`** is equivalent.

## Docify hub

Docify lives under **`'fy'-suites/docify/`** with other **“fy”** meta-tool suites; see the suite catalog in **`'fy'-suites/Readme.md`**. Optional **`pip install -e .`** exposes the **`docify`** console script (same entry point as **`python -m docify.tools`**).

1. **Router skills** live under ``'fy'-suites/docify/superpowers/<skill-name>/SKILL.md`` (minimal). **Procedure** lives in task Markdowns (for example ``'fy'-suites/docify/documentation-check-task.md`` and ``'fy'-suites/docify/documentation-solve-task.md``); do not duplicate repository language policy in skills.
2. **Cursor discovery** uses **`.cursor/skills/<skill-name>/SKILL.md`** (committed). After changing any canonical Docify skill file, run **`python "./'fy'-suites/docify/tools/sync_docify_skills.py"`** from the repo root before commit/PR (optional CI: `python "./'fy'-suites/docify/tools/sync_docify_skills.py" --check`).
3. Do **not** hand-edit only `.cursor/skills/` for Docify copies — the next sync overwrites them. Use **`python "./'fy'-suites/docify/tools/sync_docify_skills.py"`** (file copy only — **no** symlinks, **no** `mklink`).
4. **Language:** Same canonical policy as [`docs/dev/contributing.md`](docs/dev/contributing.md#repository-language). Hub overview: **`'fy'-suites/docify/README.md`**.

**Docify default docstring scan** (`docify audit` / `python_documentation_audit.py` without `--root`): `backend`, `world-engine`, `ai_stack`, `frontend`, `administration-tool`, `story_runtime_core`, `'fy'-suites/despaghettify`, `'fy'-suites/postmanify`, **`'fy'-suites/docify`**, `tools/mcp_server` — see **`'fy'-suites/docify/README.md`**. **`python_docstring_synthesize.py`** does **not** scan the tree; it adds **PEP 8 inline `#` comments** or an optional Google docstring draft for a chosen `--file` (see **`'fy'-suites/docify/documentation-docstring-synthesize-task.md`**).

**Docify path validation:** `python "./'fy'-suites/docify/tools/validate_docify_skill_paths.py"` (GitHub Actions: `.github/workflows/docify-skills-validate.yml` on relevant diffs).

## Contractify hub

Contractify lives under **`'fy'-suites/contractify/`** with other **“fy”** meta-tool suites; see the suite catalog in **`'fy'-suites/Readme.md`**. Optional **`pip install -e .`** exposes the **`contractify`** console script (same entry point as **`python -m contractify.tools`**).

1. **Router skills** live under ``'fy'-suites/contractify/superpowers/<skill-name>/SKILL.md`` (minimal). **Procedure** lives in task Markdown at suite root (`contract-audit-task.md`, `contract-solve-task.md`, `contract-reset-task.md`); scope ceilings live in **`'fy'-suites/contractify/CONTRACT_GOVERNANCE_SCOPE.md`**.
2. **Cursor discovery** uses **`.cursor/skills/<skill-name>/SKILL.md`** (committed). After changing any canonical Contractify skill file, run **`python "./'fy'-suites/contractify/tools/sync_contractify_skills.py"`** from the repo root before commit/PR (optional CI: `python "./'fy'-suites/contractify/tools/sync_contractify_skills.py" --check`).
3. Do **not** hand-edit only `.cursor/skills/` for Contractify copies — the next sync overwrites them. Use **`python "./'fy'-suites/contractify/tools/sync_contractify_skills.py"`** (file copy only — **no** symlinks, **no** `mklink`).
4. **Language:** Same canonical policy as [`docs/dev/contributing.md`](docs/dev/contributing.md#repository-language). Hub overview: **`'fy'-suites/contractify/README.md`**.

**Contractify ↔ Docify / Postmanify / Despaghettify:** Contractify **models anchors and projections** and emits **drift JSON**; **docify** repairs Python/readable docs; **postmanify** regenerates API collections from OpenAPI; **despaghettify** handles structural execution cleanup when truth is tangled in code layout.

**Skill path validation:** `python "./'fy'-suites/contractify/tools/validate_contractify_skill_paths.py"` after changing links under `'fy'-suites/contractify/superpowers/`.

## Testify hub

Testify lives under **`'fy'-suites/testify/`** with other **"fy"** meta-tool suites; see the suite catalog in **`'fy'-suites/README.md`**. Optional **`pip install -e .`** exposes the **`testify`** console script (same entry point as **`python -m testify.tools`**).

1. **Router skills** live under ``'fy'-suites/testify/superpowers/<skill-name>/SKILL.md`` (minimal). **Procedure** lives in task Markdowns (`testify-check-task.md`, `testify-solve-task.md`, `testify-audit-task.md`, `testify-reset-task.md`); do not duplicate repository language policy in skills.
2. **Cursor discovery** uses **`.cursor/skills/<skill-name>/SKILL.md`** (committed). After changing any canonical Testify skill file, run **`python "./'fy'-suites/testify/tools/sync_testify_skills.py"`** from the repo root before commit/PR (optional CI: `python "./'fy'-suites/testify/tools/sync_testify_skills.py" --check`).
3. Do **not** hand-edit only `.cursor/skills/` for Testify copies — the next sync overwrites them. Use **`python "./'fy'-suites/testify/tools/sync_testify_skills.py"`** (file copy only — **no** symlinks, **no** `mklink`).
4. **Language:** Same canonical policy as [`docs/dev/contributing.md`](docs/dev/contributing.md#repository-language). Hub overview: **`'fy'-suites/testify/README.md`**.

**CLI:** `python -m testify.tools audit` | `testify self-check` — see `'fy'-suites/testify/README.md`.

## Documentify hub

Documentify lives under **`'fy'-suites/documentify/`** with other **"fy"** meta-tool suites; see the suite catalog in **`'fy'-suites/README.md`**. Optional **`pip install -e .`** exposes the **`documentify`** console script (same entry point as **`python -m documentify.tools`**).

1. **Router skills** live under ``'fy'-suites/documentify/superpowers/<skill-name>/SKILL.md`` (minimal). **Procedure** lives in task Markdowns (`documentify-check-task.md`, `documentify-solve-task.md`, `documentify-audit-task.md`, `documentify-reset-task.md`); do not duplicate repository language policy in skills.
2. **Cursor discovery** uses **`.cursor/skills/<skill-name>/SKILL.md`** (committed). After changing any canonical Documentify skill file, run **`python "./'fy'-suites/documentify/tools/sync_documentify_skills.py"`** from the repo root before commit/PR (optional CI: `python "./'fy'-suites/documentify/tools/sync_documentify_skills.py" --check`).
3. Do **not** hand-edit only `.cursor/skills/` for Documentify copies — the next sync overwrites them. Use **`python "./'fy'-suites/documentify/tools/sync_documentify_skills.py"`** (file copy only — **no** symlinks, **no** `mklink`).
4. **Language:** Same canonical policy as [`docs/dev/contributing.md`](docs/dev/contributing.md#repository-language). Hub overview: **`'fy'-suites/documentify/README.md`**.

**CLI:** `python -m documentify.tools audit` | `documentify self-check` — see `'fy'-suites/documentify/README.md`.

## Dockerify hub

Dockerify lives under **`'fy'-suites/dockerify/`** with other **"fy"** meta-tool suites; see the suite catalog in **`'fy'-suites/README.md`**. Optional **`pip install -e .`** exposes the **`dockerify`** console script (same entry point as **`python -m dockerify.tools`**).

1. **Router skills** live under ``'fy'-suites/dockerify/superpowers/<skill-name>/SKILL.md`` (minimal). **Procedure** lives in task Markdowns (`dockerify-check-task.md`, `dockerify-solve-task.md`, `dockerify-audit-task.md`, `dockerify-reset-task.md`); do not duplicate repository language policy in skills.
2. **Cursor discovery** uses **`.cursor/skills/<skill-name>/SKILL.md`** (committed). After changing any canonical Dockerify skill file, run **`python "./'fy'-suites/dockerify/tools/sync_dockerify_skills.py"`** from the repo root before commit/PR (optional CI: `python "./'fy'-suites/dockerify/tools/sync_dockerify_skills.py" --check`).
3. Do **not** hand-edit only `.cursor/skills/` for Dockerify copies — the next sync overwrites them. Use **`python "./'fy'-suites/dockerify/tools/sync_dockerify_skills.py"`** (file copy only — **no** symlinks, **no** `mklink`).
4. **Language:** Same canonical policy as [`docs/dev/contributing.md`](docs/dev/contributing.md#repository-language). Hub overview: **`'fy'-suites/dockerify/README.md`**.

**CLI:** `python -m dockerify.tools audit` | `dockerify self-check` — see `'fy'-suites/dockerify/README.md`.
