# `'fy'-suites` — catalog

This directory groups **cross-cutting “fy” work**: tasks that **support how the monorepo is operated and evolved** (structure, API contracts in clients, agent workflows, hygiene) **without being part of the shipped product surface** (game, player apps, runtime story code). Think **meta-pipelines**: valuable for **project processing**, not the feature layer itself.

Use this file as the **catalog**: scan the table, jump to a suite’s `README.md`, then follow that suite’s CLI and Cursor skills.

---

## Suite catalog

| Suite | What it does | Python package / CLI | Cursor skills (source → sync) |
|-------|----------------|----------------------|--------------------------------|
| [**`despaghettify/`](despaghettify/README.md)** | Structure / “spaghetti” checks, DS-style workflow Markdown, metrics, autonomous loop helpers. | `python -m despaghettify.tools` · `despag-check` / `wos-despag` | [`superpowers/`](despaghettify/superpowers/README.md) → `python "./'fy'-suites/despaghettify/tools/sync_despag_skills.py"` |
| [**`postmanify/`](postmanify/README.md)** | Refresh Postman collections from OpenAPI; emit **master** + **per-tag sub-suites** under `postman/`. | `python -m postmanify.tools` · `postmanify` | [`postmanify-sync`](postmanify/superpowers/postmanify-sync/SKILL.md) → `python "./'fy'-suites/postmanify/tools/sync_postmanify_skills.py"` |
| [**`docify/`](docify/README.md)** | Python docstring backlog audit (AST), optional Google-layout checks, PEP 8 `#` comment / Google docstring assists for a single file. | `python "./'fy'-suites/docify/tools/python_documentation_audit.py"` · `python "./'fy'-suites/docify/tools/python_docstring_synthesize.py"` | [`superpowers/`](docify/superpowers/README.md) → `python "./'fy'-suites/docify/tools/sync_docify_skills.py"` |
| [**`contractify/`](contractify/README.md)** | Contract discovery, anchoring vs projections, relation edges, drift (incl. OpenAPI ↔ Postman manifest), governance backlog **CG-***. | `python -m contractify.tools` · `contractify` | [`superpowers/`](contractify/superpowers/README.md) → `python "./'fy'-suites/contractify/tools/sync_contractify_skills.py"` |

---

## Quick start (any suite)

1. **Repo root:** `pip install -e .` (see root [`pyproject.toml`](../pyproject.toml)) so importable packages under `'fy'-suites/` resolve.
2. **CLI:** prefer `python -m <package>.tools …` or the console scripts listed in the table.
3. **Cursor:** edit `superpowers/*/SKILL.md` in the suite, then run the suite’s **`sync_*_skills.py`** so **`.cursor/skills/`** stays the committed mirror.

---

## Conventions (all suites)

| Topic | Rule |
|-------|------|
| **Paths** | Invoke scripts with a repo-relative path, e.g. `python "./'fy'-suites/<suite>/tools/…"`. |
| **Package naming** | Directory name under `'fy'-suites/` matches the **importable** package (`despaghettify`, `postmanify`). Avoid a `tools/<suite>.py` file that shadows the package name. |
| **Skills** | Router-only `SKILL.md` files; **procedure** stays in task Markdown at suite root or in `references/`. |
| **Links** | Markdown under `superpowers/references/` needs **one extra `../`** segment to reach the repo root than when the hub lived at the repository root. |

---

## Adding a new suite (checklist)

1. Create **`'fy'-suites/<suite>/`** with `__init__.py`, `README.md`, and `tools/` (CLI + optional `tests/`).
2. Register the package in **[`pyproject.toml`](../pyproject.toml)** (editable install must discover it; avoid overlapping `include` filters that drop other suites).
3. Add a row to the **Suite catalog** table above and, if applicable, a **Superpower** under `superpowers/` plus a `sync_<suite>_skills.py` script pattern.
4. Point **`AGENTS.md`** and **`CONTRIBUTING.md`** at the new suite so agents and humans share one discovery path.

---

## Naming note

The folder name **`'fy'-suites`** is literal (quotes are part of the directory name on disk). In prose we refer to suites here as **“fy” suites** — **f**ramework for **y**ard-wide (repo-wide) **meta** work — not application features.
