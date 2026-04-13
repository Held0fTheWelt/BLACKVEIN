# Contributing

Full workflow, layout, and conventions: **[docs/dev/contributing.md](docs/dev/contributing.md)**.

## Language (repository)

Single source of truth: **[`docs/dev/contributing.md`](docs/dev/contributing.md#repository-language)** — heading **Repository language**. Do not maintain a parallel policy copy here or in **`AGENTS.md`**.

## Despaghettify · Cursor skills (repo standard)

- **Author** agent skills only under **`'fy'-suites/despaghettify/superpowers/<skill-name>/SKILL.md`**.
- **Mirror** them into **`.cursor/skills/`** for Cursor project discovery by running **`python "./'fy'-suites/despaghettify/tools/sync_despag_skills.py"`** from the repo root after any skill change (before commit/PR).
- **Validate** links in skill markdown: **`python "./'fy'-suites/despaghettify/tools/validate_despag_skill_paths.py"`** (see `'fy'-suites/despaghettify/superpowers/references/VALIDATION.md`; CI runs on hub edits).
- **Do not** rely on manual symlinks or one-off copies; the sync script is the supported path. Root **`AGENTS.md`** repeats this for AI agents.

## Postmanify · Cursor skills

- **Author** the router skill under **`'fy'-suites/postmanify/superpowers/postmanify-sync/SKILL.md`**.
- **Mirror** into **`.cursor/skills/`** with **`python "./'fy'-suites/postmanify/tools/sync_postmanify_skills.py"`** after edits (optional **`--check`**).

## Contractify · Cursor skills

- **Author** router skills under **`'fy'-suites/contractify/superpowers/<skill-name>/SKILL.md`**.
- **Mirror** into **`.cursor/skills/`** with **`python "./'fy'-suites/contractify/tools/sync_contractify_skills.py"`** after edits (optional **`--check`**).
- **Validate** skill markdown link targets: **`python "./'fy'-suites/contractify/tools/validate_contractify_skill_paths.py"`**.
